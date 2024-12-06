from typing import Dict, List, Literal, Tuple

import pymupdf  # type: ignore
import regex
from pydantic import BaseModel

from parser.elements.code import (
    CodeArea,
    CodeInputSubArea,
    detect_empty_branches,
    find_lowest_bbox,
)
from parser.elements.pymupdf_integ import PyMuPDFRect
from parser.elements.rectangle import Rectangle, merge_rectangles
from parser.model.page_model import PageType, SectionType, Semester
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


class StructDefinition(BaseModel, extra="forbid", strict=True):
    name: str
    rect: Rectangle
    raw: str


class MacroDefinition(BaseModel, extra="forbid", strict=True):
    kind: Literal["define", "include"]
    name: str
    rect: Rectangle
    raw: str


class Paragraph(BaseModel, extra="forbid", strict=True):
    rect: Rectangle
    raw: str


class PageResult(BaseModel, extra="forbid", strict=True):
    page_number: int
    section_type: SectionType
    page_type: PageType
    raw_text: str
    filtered_text: str

    code_areas: List[CodeArea]
    fill_in_the_blank_areas: List[Rectangle]
    struct_definitions: List[StructDefinition]
    macro_definitions: List[MacroDefinition]
    # paragraphs: List[Paragraph] | None


class SubQuestion(BaseModel, extra="forbid", strict=True):
    rects: List[Rectangle]
    raw: str
    identifier: str
    points: int | None = None


MultiPageRectangles = Dict[int, Rectangle]


class Question(BaseModel, extra="forbid", strict=True):
    rects: MultiPageRectangles
    raw: str
    sub_questions: List[SubQuestion]
    question_number: int
    max_points: int
    category: str
    sub_category: str


class ExamResult(BaseModel, extra="forbid", strict=True):
    semester: Semester
    year: int
    page_results: List[PageResult]
    questions: Dict[SectionType, Dict[int, Question]]


def extract_paragraphs(
    page: pymupdf.Page, page_blocks: PageBlocks, blocked_areas: List[Rectangle]
) -> List[Paragraph]:
    paragraphs: List[Paragraph] = []

    split = page_blocks.merged_text.split("\n")
    previous_blank = False
    running_text = ""
    for line in split:
        if len(line.strip()) == 0:
            previous_blank = True
            continue
        else:
            if previous_blank:
                rect = merge_rectangles(
                    [
                        Rectangle.from_points(*x[0:4])
                        for x in page.search_for(
                            running_text, clip=page_blocks.merged.as_tuple()
                        )
                    ]
                )
                paragraphs.append(Paragraph(rect=rect, raw=running_text))
                running_text = ""
            running_text += line
            previous_blank = False

    return paragraphs


MACRO_DEFINITION_PATTERN = regex.compile(
    r"""
    ^\s*(
        \#include\s+(?P<include>[<"][^>"]+[>"])
        |
        \#define\s+(?P<defname>\w+(?:\s*\([^)]*\))?)\s*(?P<defvalue>.*)
    )\s*$
""",
    regex.MULTILINE | regex.VERBOSE,
)


def extract_macro_definitions(
    page: pymupdf.Page, page_blocks: PageBlocks
) -> List[MacroDefinition]:
    macro_definitions: List[MacroDefinition] = []
    for match in MACRO_DEFINITION_PATTERN.finditer(page_blocks.merged_text):
        groups = match.groupdict()
        raw = match.group(0)
        rect = merge_rectangles(
            [
                Rectangle.from_points(*x[0:4])
                for x in page.search_for(raw, clip=page_blocks.merged.as_tuple())
            ]
        )
        if groups.get("include"):
            macro_definitions.append(
                MacroDefinition(
                    kind="include",
                    name=groups["include"],
                    rect=rect,
                    raw=raw,
                )
            )
        elif groups.get("defname"):
            macro_definitions.append(
                MacroDefinition(
                    kind="define",
                    name=groups["defname"],
                    rect=rect,
                    raw=raw,
                )
            )

    return macro_definitions


def extract_struct_definitions(
    page: pymupdf.Page, page_blocks: PageBlocks
) -> List[StructDefinition]:
    # Regular expression pattern to match C-like struct definitions
    pattern = r"""
    (?P<typedef>typedef\s+)?          # Optional 'typedef' keyword
    struct\s+                         # 'struct' keyword
    (?P<name_before>\w+)?             # Optional struct name before '{'
    \s*                               # Optional whitespace
    (?P<struct_body>                  # Start of 'struct_body' group
    \{
        (?:
            [^{}]                     # Any character except braces
            |                         # OR
            (?P>struct_body)          # Recursively match nested braces
        )*
    \}
    )
    (?:\s*(?P<name_after>\w+)\s*;)?   # Optional 'name_after' followed by semicolon
    """
    # Compile the regex with VERBOSE and DOTALL flags
    compiled_re = regex.compile(pattern, regex.VERBOSE | regex.DOTALL)

    struct_definitions: List[StructDefinition] = []

    # Find all struct definitions in the text
    for match in compiled_re.finditer(page_blocks.merged_text):
        # print("Match found:")
        # print(match.group())

        raw = match.group()

        name_before = match.group("name_before")
        name_after = match.group("name_after")
        if name_before is None:
            struct_name = name_after
        else:
            assert name_before is not None
            struct_name = name_before

        rect = merge_rectangles(
            [
                Rectangle.from_points(*x[0:4])
                for x in page.search_for(raw, clip=page_blocks.merged.as_tuple())
            ]
        )
        struct_definition = StructDefinition(
            name=struct_name,
            rect=rect,
            raw=raw,
        )

        struct_definitions.append(struct_definition)

    return struct_definitions


def extract_functions(page: pymupdf.Page, page_blocks: PageBlocks) -> List[CodeArea]:
    matches = FUNCTION_EXTRACTION_PATTERN.finditer(page_blocks.merged_text)

    code_areas: List[CodeArea] = []

    for match in matches:
        code_sub_areas: List[CodeInputSubArea] = []

        raw = match.group(0)
        raw = raw.strip()
        if raw.startswith("\n"):
            raw = raw[1:]
        # function_name = match.group("function_name")
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
                # Choose the lower of the two
                # Loop over
                last_line_bbox = [find_lowest_bbox(last_line_bbox)]

                second_to_last_line_bbox = [find_lowest_bbox(second_to_last_line_bbox)]

                # continue

            second_to_last_line_rect = Rectangle.from_pymupdf(
                second_to_last_line_bbox[0]
            )
            last_line_rect = Rectangle.from_pymupdf(last_line_bbox[0])

            # Find vertical distance between second to last line and last line
            vertical_distance = last_line_rect.y0 - second_to_last_line_rect.y0

            print(f"vertical_distance={vertical_distance}")
            if vertical_distance > 200:
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

        merged_code_area = merge_rectangles(
            [
                Rectangle.from_points(*x[0:4])
                for x in page.search_for(raw, clip=page_blocks.merged.as_tuple())
            ]
        )

        code_area = CodeArea(rect=merged_code_area, text=raw, sub_areas=code_sub_areas)
        code_areas.append(code_area)

    return code_areas


def is_code_page(
    page: pymupdf.Page, page_blocks: PageBlocks
) -> Tuple[bool, List[CodeArea]]:
    code: List[CodeArea] = extract_functions(page, page_blocks)
    if len(code) > 0:
        return True, code
    return False, None
