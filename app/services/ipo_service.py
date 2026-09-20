"""Sample service for business logic."""

from app.models.ipo_model import IPOMetric


class IPOService:
    """Provides IPO-related operations."""

    @staticmethod
    def get_sample_metric() -> IPOMetric:
        return IPOMetric("Sample IPO", 100.0)
