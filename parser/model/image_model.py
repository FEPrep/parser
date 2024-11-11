from typing import Optional, Literal

from pydantic import BaseModel


class Position(BaseModel):
    xref: int
    ref_name: str
    x0: int
    y0: int
    x1: int
    y1: int
    width: float
    height: float


class ImageModel(BaseModel):
    src: str
    position: Position
    image_type: Literal["thumbnail"]
    resolution: Optional[str] = None
    z_index: int
    reading_order: int
