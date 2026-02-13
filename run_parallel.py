#!/usr/bin/env python3
"""
Split vehicle combinations into N batch files and run them in parallel.

Each worker gets its own --output-dir to avoid file conflicts (the original
code's CsvExporter and reviews JSON both use read-modify-write patterns that
corrupt data under concurrent access).  After all workers finish, results are
merged into the standard data/ directory.

Usage:
    # Generate 4 batch files from the test dictionary:
    uv run python run_parallel.py --test --workers 4

    # Generate AND immediately launch all workers in parallel:
    uv run python run_parallel.py --test --workers 4 --run

    # With reviews and db export:
    uv run python run_parallel.py --test --workers 4 --run --with-reviews --export-db
"""
import argparse
import csv
import json
import shutil
import subprocess
import sys
import time
from math import ceil
from pathlib import Path

from kbb_scraper.config import get_scrape_combinations, get_stats


BATCH_DIR = Path("data/batches")
WORKERS_DIR = Path("data/workers")
FINAL_CSV = Path("data/csv/all_cars.csv")
FINAL_REVIEWS_CSV = Path("data/csv/all_reviews.csv")
FINAL_RAW = Path("data/raw")
FINAL_4TABLE = Path("data/processed/4table")


# ------------------------------------------------------------------ #
#  Split & write batch files
# ------------------------------------------------------------------ #

def split_combinations(combinations: list, num_workers: int) -> list[list]:
    """Split combinations into roughly equal chunks."""
    chunk_size = ceil(len(combinations) / num_workers)
    return [combinations[i : i + chunk_size] for i in range(0, len(combinations), chunk_size)]


def write_batch_files(chunks: list[list], test_mode: bool) -> list[Path]:
    """Write each chunk as a JSON batch file. Returns list of file paths."""
    BATCH_DIR.mkdir(parents=True, exist_ok=True)

    # Clean old batch files
    for old in BATCH_DIR.glob("batch_*.json"):
        old.unlink()

    prefix = "test" if test_mode else "full"
    paths = []
    for i, chunk in enumerate(chunks, 1):
        records = [{"make": m, "model": mo, "year": y} for m, mo, y in chunk]
        path = BATCH_DIR / f"batch_{prefix}_{i}.json"
        path.write_text(json.dumps(records, indent=2))
        paths.append(path)
    return paths


# ------------------------------------------------------------------ #
#  Launch workers (each in its own output dir)
# ------------------------------------------------------------------ #

def launch_workers(batch_paths: list[Path], extra_flags: list[str],
                    stagger_seconds: int = 5) -> int:
    """Launch one scraper process per batch file and wait for all to finish.

    Each worker writes to its own isolated directory under data/workers/
    to prevent any file-level conflicts.

    Workers are started with a stagger delay so the first worker caches the
    ChromeDriver binary before subsequent workers attempt to use it
    (avoids webdriver-manager race conditions on the shared ~/.wdm/ cache).
    """
    # Clean old worker dirs
    if WORKERS_DIR.exists():
        shutil.rmtree(WORKERS_DIR)
    WORKERS_DIR.mkdir(parents=True, exist_ok=True)

    procs = []

    for i, path in enumerate(batch_paths, 1):
        worker_dir = WORKERS_DIR / f"worker_{i}"
        worker_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "uv", "run", "python", "-m", "kbb_scraper",
            "--batch-file", str(path),
            "--output-dir", str(worker_dir),
        ] + extra_flags

        log_file = BATCH_DIR / f"worker_{i}.log"
        fh = open(log_file, "w")
        print(f"  Worker {i}/{len(batch_paths)}: {path.name}")
        print(f"    output → {worker_dir}")
        print(f"    log    → {log_file}")
        proc = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT)
        procs.append((i, proc, fh))

        # Stagger: let the first worker cache ChromeDriver before others start
        if i < len(batch_paths):
            print(f"    (waiting {stagger_seconds}s before next worker...)")
            time.sleep(stagger_seconds)

    print(f"\n{len(procs)} workers running. Waiting for all to finish...\n")

    failed = 0
    for i, proc, fh in procs:
        proc.wait()
        fh.close()
        status = "OK" if proc.returncode == 0 else f"FAILED (exit {proc.returncode})"
        print(f"  Worker {i} finished: {status}")
        if proc.returncode != 0:
            failed += 1

    return failed


# ------------------------------------------------------------------ #
#  Merge worker outputs into final data/ directory
# ------------------------------------------------------------------ #

def _merge_one_csv(pattern: str, dest: Path, label: str):
    """Merge per-worker CSV files matching *pattern* into *dest*."""
    worker_csvs = sorted(WORKERS_DIR.glob(pattern))
    if not worker_csvs:
        return

    dest.parent.mkdir(parents=True, exist_ok=True)

    all_headers: list[str] = []
    header_set: set[str] = set()
    all_rows: list[dict] = []

    for csv_path in worker_csvs:
        with open(csv_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames:
                for col in reader.fieldnames:
                    if col not in header_set:
                        all_headers.append(col)
                        header_set.add(col)
            for row in reader:
                all_rows.append(row)

    with open(dest, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"  {label}: {len(all_rows)} rows → {dest}")


def merge_csv_files():
    """Merge per-worker CSV files into final data/csv/ directory."""
    _merge_one_csv("worker_*/csv/all_cars.csv", FINAL_CSV, "Specs CSV")
    _merge_one_csv("worker_*/csv/all_reviews.csv", FINAL_REVIEWS_CSV, "Reviews CSV")


def merge_raw_json_files():
    """Merge per-worker raw JSON files into data/raw/.

    Reviews JSON files use a {make}_{model}_reviews.json format with a
    nested "years" dict, so we deep-merge by year key.
    """
    FINAL_RAW.mkdir(parents=True, exist_ok=True)
    worker_raw_dirs = sorted(WORKERS_DIR.glob("worker_*/raw"))

    review_files: dict[str, list[Path]] = {}  # filename → [paths]
    other_files: list[Path] = []

    for raw_dir in worker_raw_dirs:
        for f in raw_dir.iterdir():
            if f.is_dir():
                # Copy subdirectories (e.g. debug/) as-is
                dest = FINAL_RAW / f.name
                if not dest.exists():
                    shutil.copytree(f, dest)
            elif f.name.endswith("_reviews.json"):
                review_files.setdefault(f.name, []).append(f)
            else:
                other_files.append(f)

    # Deep-merge review JSON files
    merged_reviews = 0
    for filename, paths in review_files.items():
        combined = {}
        for p in paths:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not combined:
                combined = data
            else:
                # Merge years dict
                combined.setdefault("years", {}).update(data.get("years", {}))
        dest = FINAL_RAW / filename
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(combined, f, indent=2, ensure_ascii=False)
        merged_reviews += 1

    # Copy non-review files (no conflict — unique per make+model+year)
    for src in other_files:
        dest = FINAL_RAW / src.name
        shutil.copy2(src, dest)

    print(f"  Raw:     {merged_reviews} review files merged, "
          f"{len(other_files)} other files copied → {FINAL_RAW}")


def merge_4table_files():
    """Copy per-worker 4table exports into data/processed/4table/."""
    worker_4tables = sorted(WORKERS_DIR.glob("worker_*/processed/4table/*.json"))
    if not worker_4tables:
        return

    FINAL_4TABLE.mkdir(parents=True, exist_ok=True)
    for src in worker_4tables:
        dest = FINAL_4TABLE / src.name
        shutil.copy2(src, dest)

    print(f"  4-table: {len(worker_4tables)} files → {FINAL_4TABLE}")


def merge_all():
    """Merge all worker outputs into the final data/ directory."""
    print("\n=== Merging worker outputs ===")
    merge_csv_files()
    merge_raw_json_files()
    merge_4table_files()
    print("Done.")


# ------------------------------------------------------------------ #
#  Main
# ------------------------------------------------------------------ #

def main():
    parser = argparse.ArgumentParser(
        description="Split & run KBB scraper in parallel (conflict-safe)"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--test", action="store_true",
                      help="Use test dictionary (5 brands, 15 models, 3 years)")
    mode.add_argument("--batch", action="store_true",
                      help="Use full dictionary (38 brands, 412 models, 25 years)")
    mode.add_argument("--merge-only", action="store_true",
                      help="Skip scraping — only merge existing worker outputs")

    parser.add_argument("--workers", type=int, default=4,
                        help="Number of parallel workers (default: 4)")
    parser.add_argument("--run", action="store_true",
                        help="Launch workers immediately after generating batch files")
    parser.add_argument("--with-reviews", action="store_true",
                        help="Pass --with-reviews to each worker")
    parser.add_argument("--export-db", action="store_true",
                        help="Pass --export-db to each worker")
    parser.add_argument("--no-headless", action="store_true",
                        help="Pass --no-headless to each worker")

    args = parser.parse_args()

    # --merge-only: just merge existing worker dirs and exit
    if args.merge_only:
        merge_all()
        return

    test_mode = args.test

    # Show stats
    stats = get_stats(test_mode)
    mode_name = "TEST" if test_mode else "FULL"
    print(f"=== {mode_name} mode ===")
    print(f"  Brands: {stats['brands']}")
    print(f"  Models: {stats['total_models']}")
    print(f"  Years:  {stats['year_range']}")
    print(f"  Total combinations: {stats['total_combinations']}")
    print(f"  Workers: {args.workers}")
    print()

    # Generate combinations and split
    combinations = get_scrape_combinations(test_mode)
    chunks = split_combinations(combinations, args.workers)

    print(f"Splitting {len(combinations)} combinations into {len(chunks)} batch files:")
    for i, chunk in enumerate(chunks, 1):
        print(f"  Batch {i}: {len(chunk)} combinations")

    # Write batch files
    batch_paths = write_batch_files(chunks, test_mode)
    print(f"\nBatch files written to {BATCH_DIR}/\n")

    # Optionally launch
    if args.run:
        print(f"=== Launching {len(batch_paths)} workers (isolated output dirs) ===")
        extra_flags = []
        if args.with_reviews:
            extra_flags.append("--with-reviews")
        if args.export_db:
            extra_flags.append("--export-db")
        if args.no_headless:
            extra_flags.append("--no-headless")

        failed = launch_workers(batch_paths, extra_flags)

        if failed:
            print(f"\n{failed} worker(s) failed. Check logs in {BATCH_DIR}/")
            print("Merging successful worker outputs anyway...")

        merge_all()

        if failed:
            sys.exit(1)
    else:
        print("To run manually (each worker gets its own output dir):")
        for i, p in enumerate(batch_paths, 1):
            worker_dir = WORKERS_DIR / f"worker_{i}"
            print(f"  uv run python -m kbb_scraper --batch-file {p} --output-dir {worker_dir}")
        print(f"\nThen merge results:")
        print(f"  uv run python run_parallel.py --merge-only")
        print(f"\nOr re-run with --run to do everything automatically.")


if __name__ == "__main__":
    main()
