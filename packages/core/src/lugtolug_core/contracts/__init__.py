"""Data contracts, generated from the JSON Schemas in data/schemas (ADR-0004).

The modules in this package are generated: change a schema, then run
`uv run poe contracts`. CI fails when they fall out of date.
"""

from lugtolug_core.contracts.annotation import ImageAnnotation
from lugtolug_core.contracts.catalogue import CatalogueEntry
from lugtolug_core.contracts.stand_in import StandInSpec

__all__ = ["CatalogueEntry", "ImageAnnotation", "StandInSpec"]
