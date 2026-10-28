"""Names for the controlled vocabularies in data/schemas/common.schema.json.

The generated contracts spell these out inline; hand-written code uses the aliases
below. A test checks that they match the schema exactly.
"""

from typing import Literal

CaseShape = Literal["round", "cushion", "tonneau", "square", "other"]
CaseMaterial = Literal["steel", "titanium", "gold", "ceramic", "resin", "bronze", "other"]
BezelType = Literal["none", "smooth", "fluted", "rotating_insert", "other"]
StrapType = Literal["bracelet", "leather", "rubber", "fabric", "other"]
ColourName = Literal[
    "black",
    "white",
    "silver",
    "grey",
    "blue",
    "green",
    "red",
    "brown",
    "gold",
    "champagne",
    "cream",
    "orange",
    "yellow",
    "pink",
    "purple",
    "other",
]
