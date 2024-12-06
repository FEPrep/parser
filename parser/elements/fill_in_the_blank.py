import pymupdf  # type: ignore
from pydantic import BaseModel

from parser.elements.pymupdf_integ import PyMuPDFRect
from parser.elements.rectangle import Rectangle


class SeparatedRects(BaseModel):
    underscores: PyMuPDFRect | None
    remaining: PyMuPDFRect | None


def separate_underscores_from_text(
    page: pymupdf.Page, rect: Rectangle, text: str
) -> SeparatedRects:
    underscores = None
    remaining = None

    # Find the longest continuous sequence of underscores
    longest_underscore_seq = ""
    current_seq = ""

    for char in text:
        if char == "_":
            current_seq += char
        else:
            if len(current_seq) > len(longest_underscore_seq):
                longest_underscore_seq = current_seq
            current_seq = ""

    # Check the last sequence
    if len(current_seq) > len(longest_underscore_seq):
        longest_underscore_seq = current_seq

    if len(longest_underscore_seq) >= 3:
        # Use page.search_for to find the remaining text
        non_underscores = text.replace(longest_underscore_seq, "")
        remaining_bbox = page.search_for(
            text.replace(longest_underscore_seq, ""), clip=rect.as_tuple()
        )
        if remaining_bbox:
            remaining = (
                remaining_bbox[0][0],
                remaining_bbox[0][1],
                remaining_bbox[0][2],
                remaining_bbox[0][3],
                non_underscores,
                0,
                0,
                0,
            )

        underscores_bbox = page.search_for(longest_underscore_seq, clip=rect.as_tuple())
        if underscores_bbox:
            underscores = (
                underscores_bbox[0][0],
                underscores_bbox[0][1],
                underscores_bbox[0][2],
                underscores_bbox[0][3],
                longest_underscore_seq,
                0,
                0,
                0,
            )
    else:
        remaining = None

    return SeparatedRects(underscores=underscores, remaining=remaining)
