from typing import Optional, Literal

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
    src: str
    position: Position
    image_type: Literal["thumbnail"]
    resolution: Optional[str] = None
    z_index: int
    reading_order: int
