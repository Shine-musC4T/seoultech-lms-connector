"""Read-only connector for the authenticated user's SeoulTech e-Class data."""

from .client import SeoultechLMSClient

__version__ = "0.3.2"

__all__ = ["SeoultechLMSClient", "__version__"]
