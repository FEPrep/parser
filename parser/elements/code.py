from typing import List, Literal

import regex
from pydantic import BaseModel

from parser.elements.pymupdf_integ import PyMuPDFRect
from parser.elements.rectangle import Rectangle

EMPTY_BRANCH_PATTERN = regex.compile(
    r"""
        \{                          # Opening brace
        (?:
            \s*                     # Optional leading whitespace
            (?:
                //.*(?:\n|$)        | # Single-line comment
                for\s*\([^)]*\)\s*\{\s*\}\s*(?:\n|$)  | # Empty for loop
                while\s*\([^)]*\)\s*\{\s*\}\s*(?:\n|$) | # Empty while loop
            )
        )*                           # Repeat for multiple lines
        \}                          # Closing brace
        """,
    regex.VERBOSE | regex.MULTILINE,
)


class CodeInputSubArea(BaseModel):
    kind: Literal[
        "fill_in_the_blank", "free_response", "partially_filled_free_response"
    ]
    code_textarea: Rectangle | None
    text: str


class CodeArea(BaseModel):
    rect: Rectangle
    sub_areas: List[CodeInputSubArea]
    text: str


def filter_empty_lines(text: str) -> str:
    return text.replace(" ", "").replace("\n", "")


def detect_empty_branches(code: str) -> List[str]:
    print(f"code={code}")
    matches = EMPTY_BRANCH_PATTERN.findall(code)
    print(f"matches={matches}")
    for match in matches:
        print(f"match={match}")

    return matches


def find_lowest_bbox(bboxes: List[PyMuPDFRect]) -> PyMuPDFRect:
    return max(bboxes, key=lambda x: x[1])
