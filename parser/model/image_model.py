from typing import Literal

from pydantic import BaseModel


class Position(BaseModel):
    xref: int
    ref_name: str
    x0: float
    y0: float
    x1: float
    y1: float
    width: float
    height: float


class ImageModel(BaseModel):
    element_type: Literal["image"] = "image"
    src: str
    position: Position
    # resolution: Optional[str] = None
    # z_index: int
    # reading_order: int
