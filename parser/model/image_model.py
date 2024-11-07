from typing import Field, Optional

from pydantic import BaseModel


class Position(BaseModel):
    x: int
    y: int
    width: int
    height: int


class Image(BaseModel):
    src: str
    position: Position
    color_profile: str = Field(default="RGB", const=True)
    resolution: Optional[str] = None
    z_index: int
    reading_order: int
