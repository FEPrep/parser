from typing import Literal, List

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
    cells: List[Cell]


class TableModel(BaseModel):
    element_type: Literal["table"] = "table"
    position: CellPosition
    z_index: int
    rows: List[Row]
