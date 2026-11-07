"""Data connectors. Each turns one public source into canonical observations."""
from .base import ComparabilityError, Connector, LoadResult, ManifestError, QualityReport, SystemBreak
from .brazil_sipni import BrazilSIPNIConnector

__all__ = [
    "BrazilSIPNIConnector",
    "ComparabilityError",
    "Connector",
    "LoadResult",
    "ManifestError",
    "QualityReport",
    "SystemBreak",
]
