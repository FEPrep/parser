from typing import List, Tuple

import pymupdf
from pydantic import BaseModel

from parser.elements.code import (
    CodeArea,
    CodeInputSubArea,
    detect_empty_branches,
    find_lowest_bbox,
)
from parser.elements.pymupdf_integ import PyMuPDFRect
from parser.elements.rectangle import Rectangle, merge_rectangles
from parser.question_extraction import FUNCTION_EXTRACTION_PATTERN


class PageBlocks(BaseModel):
    page_number: int
    blocks: List[PyMuPDFRect]
    merged: Rectangle
    merged_text: str

    @classmethod
    def from_page_bboxes(
        cls, page_bboxes: List[PyMuPDFRect], pymypdfPage: pymupdf.Page
    ):
        rectangles: List[Rectangle] = [
            Rectangle.from_points(*bbox[0:4]) for bbox in page_bboxes
        ]

        largest_rectangle: Rectangle = merge_rectangles(rectangles)

        return cls(
            blocks=page_bboxes,
            merged=largest_rectangle,
            merged_text=pymypdfPage.get_text(clip=largest_rectangle.as_tuple()),
            page_number=pymypdfPage.number,
        )


class PageResult(BaseModel, extra="forbid", strict=True):
    page_number: int
    code_areas: List[CodeArea]
    fill_in_the_blank_areas: List[Rectangle]


class ExamResult(BaseModel, extra="forbid", strict=True):
    page_results: List[PageResult]


def extract_code_inputs(page: pymupdf.Page, page_blocks: PageBlocks) -> List[CodeArea]:
    # Find all matches

    print(f"page_blocks.merged_text={page_blocks.merged_text}")

    matches = FUNCTION_EXTRACTION_PATTERN.finditer(page_blocks.merged_text)

    print(f"matches={matches}")
    code_areas: List[CodeArea] = []

    print(f"page_number={page_blocks.page_number}")
    for match in matches:
        code_sub_areas: List[CodeInputSubArea] = []

        raw = match.group(0)
        raw = raw.strip()
        if raw.startswith("\n"):
            raw = raw[1:]

        print(f"raw={raw}")
        print(f"match={match}")
        function_name = match.group("function_name")
        print(f"parsing function_name='{function_name}'")
        # arguments = match.group("arguments")
        body = match.group("body")

        empty_branches: List[str] = detect_empty_branches(body)

        # define parent bbox
        parent_bbox = page.search_for(raw, clip=page_blocks.merged.as_tuple())

        parent_rect = merge_rectangles(
            [Rectangle.from_points(*x[0:4]) for x in parent_bbox]
        )

        if len(empty_branches) > 0:
            print(f"empty_branches={empty_branches}")
            for branch in empty_branches:
                code_bboxes = page.search_for(branch, clip=parent_rect.as_tuple())
                if code_bboxes is None or len(code_bboxes) == 0:
                    raise ValueError(
                        f"No code bbox found for body='{body}', branch={branch}"
                    )

                code_textarea_rect = merge_rectangles(
                    [Rectangle.from_points(*x[0:4]) for x in code_bboxes]
                )

                code_sub_areas.append(
                    CodeInputSubArea(
                        kind="free_response",
                        code_textarea=code_textarea_rect,
                        text=branch,
                    )
                )

        if len(code_sub_areas) == 0:
            # Fallback to use distance-based approach... very ugly
            print(
                f"No code areas found for page {page_blocks.page_number}. Reverting to distance-based approach."
            )

            # Find second to last line and last line of input code
            code_lines = raw.split("\n")

            print(f"code_lines={code_lines}")
            if len(code_lines) < 2:
                print(
                    f"Aborting distance-based approach, only found {len(code_lines)} lines of code. Need 2."
                )
                continue
            second_to_last_line = code_lines[-2]
            # if "return" in second_to_last_line:
            #    second_to_last_line = code_lines[-3]
            for line in reversed(code_lines[:-1]):
                if len(line.strip()) > 0 and "return" not in line.strip():
                    second_to_last_line = line
                    break

            last_line = code_lines[-1]

            # Find locations of second to last line and last line
            second_to_last_line_bbox = page.search_for(
                second_to_last_line, clip=parent_rect.as_tuple()
            )
            last_line_bbox = page.search_for(last_line, clip=parent_rect.as_tuple())

            if second_to_last_line_bbox is None:
                print(
                    f"Aborting distance-based approach, could not find locations of second to last line='{second_to_last_line}'."
                )
                continue

            if last_line_bbox is None:
                print(
                    f"Aborting distance-based approach, could not find locations of last line='{last_line}'."
                )
                continue

            if len(second_to_last_line_bbox) > 1 or len(last_line_bbox) > 1:
                print(
                    "There are multiple locations for second to last line or last line."
                )
                print(f"second_to_last_line_bbox={second_to_last_line_bbox}")
                print(f"second_to_last_line={second_to_last_line}")
                print(f"last_line_bbox={last_line_bbox}")
                print(f"last_line={last_line}")
                # Choose the lower of the two
                # Loop over
                last_line_bbox = [find_lowest_bbox(last_line_bbox)]
                print(f"last_line_bbox={last_line_bbox}")

                second_to_last_line_bbox = [find_lowest_bbox(second_to_last_line_bbox)]
                print(f"second_to_last_line_bbox={second_to_last_line_bbox}")

                # continue

            second_to_last_line_rect = Rectangle.from_pymupdf(
                second_to_last_line_bbox[0]
            )
            last_line_rect = Rectangle.from_pymupdf(last_line_bbox[0])

            # Find vertical distance between second to last line and last line
            print(f"last_line_rect={last_line_rect}")
            print(f"second_to_last_line_rect={second_to_last_line_rect}")
            vertical_distance = last_line_rect.y0 - second_to_last_line_rect.y0

            print(f"vertical_distance={vertical_distance}")
            if vertical_distance > 200:
                print(
                    "Found candidate for partially filled in code area question. Creating Question now."
                )

                merged_code_area = merge_rectangles(
                    [
                        Rectangle.from_points(*x[0:4])
                        for x in page.search_for(
                            raw, clip=page_blocks.merged.as_tuple()
                        )
                    ]
                )

                # Create bbox for code area
                code_area_bbox = Rectangle.from_points(
                    merged_code_area.x0,
                    second_to_last_line_rect.y1,
                    merged_code_area.x1,
                    last_line_rect.y0,
                )

                # Find text
                code_area_text = page.get_text(clip=code_area_bbox.as_tuple())

                code_sub_areas.append(
                    CodeInputSubArea(
                        kind="partially_filled_free_response",
                        code_textarea=code_area_bbox,
                        text=code_area_text,
                    )
                )

            # return []

        if len(code_sub_areas) > 0:
            merged_code_area = merge_rectangles(
                [
                    Rectangle.from_points(*x[0:4])
                    for x in page.search_for(raw, clip=page_blocks.merged.as_tuple())
                ]
            )
            # merged_code_area = merge_rectangles(
            #    [x.code_textarea for x in code_sub_areas if x.code_textarea is not None]
            # )

            code_area = CodeArea(
                rect=merged_code_area, text=raw, sub_areas=code_sub_areas
            )
            code_areas.append(code_area)

    return code_areas


def is_code_page(
    page: pymupdf.Page, page_blocks: PageBlocks
) -> Tuple[bool, List[CodeArea]]:
    code: List[CodeArea] = extract_code_inputs(page, page_blocks)
    if len(code) > 0:
        return True, code
    return False, None
