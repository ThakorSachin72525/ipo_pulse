"""Sample model for IPO data."""


class IPOMetric:
    """Simple model representing a single IPO metric."""

    def __init__(self, company_name: str, price: float):
        self.company_name = company_name
        self.price = price

    def __repr__(self) -> str:
        return f"IPOMetric(company_name={self.company_name!r}, price={self.price})"
