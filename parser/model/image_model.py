from typing import Optional, Literal

from pydantic import BaseModel


class Position(BaseModel):
    x: int
    y: int
    width: int
    height: int


class ImageModel(BaseModel):
    src: str
    position: Position
    image_type: Literal["thumbnail"]
    resolution: Optional[str] = None
    z_index: int
    reading_order: int
