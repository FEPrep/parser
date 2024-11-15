from typing import List
import json
from parser.model.table_model import TableModel, CellPosition, Row, Cell
import pdfplumber


def extract_tables(input_file: str, output_file: str):
    tables: List[TableModel] = []

    with pdfplumber.open(input_file) as pdf:
        for page_num, page in enumerate(pdf.pages):
            table_data = page.extract_table()

            if table_data is None:
                print(f"No table found on page {page_num + 1}")
                continue
            print(f"Table found on page {page_num + 1}")

            rows = []
            x_min, y_min, x_max, y_max = (
                float("inf"),
                float("inf"),
                float("-inf"),
                float("-inf"),
            )

            for row_data in table_data:
                row_cells = []
                for col_index, cell_text in enumerate(row_data):
                    words = page.extract_words()
                    cell_words = (
                        [word for word in words if word["text"] == cell_text]
                        if cell_text
                        else []
                    )

                    if cell_words:
                        cell_info = cell_words[0]
                        cell_position = CellPosition(
                            x=cell_info["x0"],
                            y=cell_info["top"],
                            width=cell_info["x1"] - cell_info["x0"],
                            height=cell_info["bottom"] - cell_info["top"],
                        )
                    else:
                        cell_position = CellPosition(
                            x=x_max if x_max != float("-inf") else 0,
                            y=y_max if y_max != float("-inf") else 0,
                            width=50,
                            height=20,
                        )

                    row_cells.append(
                        Cell(content=cell_text or "", position=cell_position)
                    )
                    x_min = min(x_min, cell_position.x)
                    y_min = min(y_min, cell_position.y)
                    x_max = max(x_max, cell_position.x + cell_position.width)
                    y_max = max(y_max, cell_position.y + cell_position.height)

                rows.append(Row(cells=row_cells))

            table_position = CellPosition(
                x=x_min, y=y_min, width=x_max - x_min, height=y_max - y_min
            )

            table = TableModel(position=table_position, z_index=1, rows=rows)
            tables.append(table)

    with open(output_file, "w") as json_file:
        json.dump([table.dict() for table in tables], json_file, indent=4)

    print(f"Table metadata extracted and saved to {output_file}")
