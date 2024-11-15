from typing import Literal

from pydantic import BaseModel


class CellPosition(BaseModel):
    x: float
    y: float
    width: float
    height: float


class Cell(BaseModel):
    content: str
    position: CellPosition
    colspan: int = 1
    rowspan: int = 1


class Row(BaseModel):
    cells: list[Cell]


class TableModel(BaseModel):
    element_type: Literal["table"] = "table"
    type: str = "table"
    position: CellPosition
    z_index: int
    reading_order: int
    rows: list[Row]
