import json
import os
from typing import List, Literal, Tuple

import pymupdf  # type: ignore

from parser.elements.rectangle import Rectangle

PyMuPDFRect = Tuple[float, float, float, float, str, float, float, float]

InputAreaKind = Literal[
    "underscores",
    "code_underscores",
    "textarea",
    "code_textarea",
    "entire_function_area",
    "generic_block",
]


def rect_to_bbox(rect: PyMuPDFRect) -> Tuple[float, float, float, float]:
    return (rect[0], rect[1], rect[2], rect[3])


def mark_rect(page: pymupdf.Page, rect: PyMuPDFRect | Rectangle, kind: InputAreaKind):
    """Underline each word that contains 'text'."""
    if isinstance(rect, Rectangle):
        bbox = rect.as_tuple()
    else:
        bbox = rect_to_bbox(rect)

    annot = page.add_rect_annot(bbox)  # underline
    blue = (0, 0, 1)
    if kind == "underscores":
        fill = (153 / 255, 240 / 255, 234 / 255)
    elif kind == "textarea":
        fill = (234 / 255, 240 / 255, 153 / 255)
    elif kind == "code_textarea":
        fill = (234 / 255, 153 / 255, 240 / 255)
    elif kind == "code_underscores":
        fill = (153 / 255, 240 / 255, 234 / 255)
    elif kind == "entire_function_area":
        fill = (234 / 255, 153 / 255, 240 / 255)
    elif kind == "generic_block":
        fill = (234 / 255, 153 / 255, 240 / 255)
    else:
        raise ValueError(f"Invalid kind: {kind}")

    annot.set_border(width=1, dashes=[1, 2])
    annot.set_colors(stroke=blue, fill=fill)
    annot.update(opacity=0.5)


def serialize_blocks_to_json(
    blocks: List[PyMuPDFRect],
) -> str:
    blocks_list = [
        {
            "x0": block[0],
            "y0": block[1],
            "x1": block[2],
            "y1": block[3],
            "text": block[4],
            "width": block[5],
            "height": block[6],
        }
        for block in blocks
    ]
    return json.dumps(blocks_list, indent=4)


def load_exam_and_extract_text_words(filepath: str):
    doc = pymupdf.open(filepath)

    for i, page in enumerate(doc):  # scan through the pages
        blocks: List[Tuple[float, float, float, float, str, float, float]] = (
            page.get_text("blocks")
        )

        for block in blocks:
            mark_rect(page, block, "generic_block")  # mark the page's words

        json_data = serialize_blocks_to_json(blocks)
        with open(f"page-{i}-blocks.json", "w") as json_file:
            json_file.write(json_data)

    doc.save("marked-" + os.path.basename(filepath))
