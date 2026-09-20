"""Sample view for rendering data."""


class HomeView:
    """Renders the home screen output."""

    @staticmethod
    def render(message: str) -> str:
        return f"View: {message}"
