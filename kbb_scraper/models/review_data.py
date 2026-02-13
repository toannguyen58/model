"""
Data models for KBB consumer reviews and expert review data.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any


@dataclass
class ConsumerReview:
    """Aggregated consumer review data from KBB consumer reviews page."""
    overall_rating: Optional[float] = None       # e.g. 3.9 out of 5
    review_count: Optional[int] = None            # e.g. 343
    recommend_percentage: Optional[int] = None    # e.g. 68
    star_distribution: Dict[int, int] = field(default_factory=dict)
    # e.g. {5: 53, 4: 15, 3: 14, 2: 8, 1: 10}  (percentages)
    category_ratings: Dict[str, float] = field(default_factory=dict)
    # e.g. {"value": 4.0, "performance": 4.0, "quality": 3.9, ...}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_rating": self.overall_rating,
            "review_count": self.review_count,
            "recommend_percentage": self.recommend_percentage,
            "star_distribution": {str(k): v for k, v in self.star_distribution.items()},
            "category_ratings": self.category_ratings,
        }


@dataclass
class ExpertReview:
    """Expert review / recommendations data from KBB model page."""
    expert_rating: Optional[float] = None   # e.g. 4.6 out of 5
    ranking: Optional[str] = None           # e.g. "#2 in Best Midsize Cars of 2020"
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expert_rating": self.expert_rating,
            "ranking": self.ranking,
            "pros": self.pros,
            "cons": self.cons,
        }


@dataclass
class ReviewData:
    """Combined review data for a vehicle model + year."""
    make: str
    model: str
    year: str
    consumer_review: Optional[ConsumerReview] = None
    expert_review: Optional[ExpertReview] = None
    scrape_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "make": self.make,
            "model": self.model,
            "year": self.year,
            "scrape_timestamp": self.scrape_timestamp,
        }
        if self.consumer_review:
            result["consumer_review"] = self.consumer_review.to_dict()
        if self.expert_review:
            result["expert_review"] = self.expert_review.to_dict()
        return result
