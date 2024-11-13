import re
import sys
from datetime import datetime
from typing import List, NamedTuple, Tuple

import pymupdf as fitz  # pymupdf
from pydantic import BaseModel

from parser.elements.rectangle import (
    Rectangle,
    build_connectivity_graph,
    find_connected_components,
)
from parser.model.page_model import (
    Page,
    PageType,
    Section,
    SectionType,
    Semester,
    pages_as_string,
    sections_as_string,
)
from parser.page_processing import (
    extract_date_from_page,
    get_page_type,
    get_section_type,
)
from parser.question_extraction import get_questions, write_to_file
from parser.section_processing import get_sections


class BlockText(NamedTuple):
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    # block sequence number
    block_no: int
    # 1 for image block, 0 for text block
    block_type: int


class Exam(BaseModel, strict=True):
    loaded: bool
    exam_path: str

    solutions_path: str | None
    sections: List[Section] | None
    semester: str | None
    year: int | None

    def __init__(self, exam_path: str, solutions_path: str | None = None):
        super().__init__(
            exam_path=exam_path,
            solutions_path=solutions_path,
            loaded=False,
            sections=None,
            semester=None,
            year=None,
        )

    def remove_page_mentions(self, text: str) -> str:
        # Use regular expression to find and remove "Page x of y" patterns
        return re.sub(r"Page \d+ of \d+", "", text)

    def load_data(self, verbose: bool = False):
        assert not self.loaded
        try:
            # Open and read the PDF file using pymupdf
            document = fitz.open(self.exam_path)

            # Process the PDF content here
            # For example, you could extract text from each page:
            pages: List[Page] = []
            previous_section_type: SectionType | None = None
            for page_number in range(len(document)):
                page: fitz.Page = document.load_page(page_number)
                text = page.get_text(sort=True)
                # block_text: List[BlockText] = page.get_text("blocks", sort=True)
                # print(block_text)

                text = self.remove_page_mentions(text)

                if previous_section_type is None:
                    assert page_number == 0
                    date = extract_date_from_page(text)
                    assert date is not None
                    semester, year = get_semester_and_year(date)
                    self.semester = semester
                    self.year = year

                page_type = get_page_type(text)
                if page_type is None:
                    print(
                        f"Breaking on page {page_number} because it is not a valid PageType"
                    )
                    break

                section_type: SectionType | None = None
                if page_type == PageType.SECTION:
                    section_type = get_section_type(text)
                    if section_type is None:
                        print(
                            f"Breaking on page {page_number} because it is not a valid SectionType"
                        )
                        print(text)
                        break
                else:
                    section_type = previous_section_type

                if section_type is None:
                    raise ValueError("section_type is None")

                new_page = Page(
                    page_type=page_type,
                    section_type=section_type,
                    page_number=page_number,
                    text=text,
                    fitz_page=page,
                )

                pages.append(new_page)

                previous_section_type = section_type

                if verbose:
                    write_to_file(
                        "raw.txt",
                        "\n".join(pages_as_string(pages, include_metadata=False)),
                    )
                    write_to_file(
                        "raw_with_meta.txt",
                        "\n".join(pages_as_string(pages, include_metadata=True)),
                    )

                sections: List[Section] = get_sections(pages)

                if verbose:
                    write_to_file(
                        "sections.txt",
                        "\n".join(sections_as_string(sections, include_metadata=True)),
                    )

                for section in sections:
                    questions = get_questions(section)
                    for question in questions:
                        valid_pages: List[Page] = []
                        for page in section.pages:
                            if page.page_number in question.pages:
                                valid_pages.append(page)

                        if len(question.sub_questions) > 0:
                            for sub in question.sub_questions:
                                bbox: Rectangle | None = run_bbox_search(
                                    sub.original_text.text,
                                    [x.fitz_page for x in valid_pages],
                                )
                                print("bbox=", bbox)

                                for sub_sub in sub.sub_questions:
                                    bbox: Rectangle | None = run_bbox_search(
                                        sub_sub.original_text.text,
                                        [x.fitz_page for x in valid_pages],
                                    )
                                    print("bbox=", bbox)

                        else:
                            bbox: Rectangle | None = run_bbox_search(
                                question.original_text,
                                [x.fitz_page for x in valid_pages],
                            )

                            print("bbox=", bbox)

                    section.questions = questions

                self.sections = sections

                self.loaded = True

                document.save("joemama.pdf")
        except Exception as e:
            print(f"An error occurred: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()
            sys.exit(1)

    def write(self, output_file: str):
        assert self.loaded
        print(f"Writing to {output_file}")
        with open(output_file, "w") as json_file:
            json_file.write(self.model_dump_json())


def run_bbox_search(original_text: str, fitz_page: List[fitz.Page]) -> Rectangle | None:
    if len(fitz_page) > 1:
        # multi-line question
        # ignore for now
        return None

    bboxes: List[Tuple[float, float, float, float]] = fitz_page[0].search_for(
        original_text
    )

    if len(bboxes) == 0:
        print(f"No bboxes found for {original_text}")
        # raise ValueError(f"No bboxes found for {original_text}")
        return None

    rectangles: List[Rectangle] = [Rectangle(*bbox) for bbox in bboxes]

    MAX_DISTANCE = 800  # Maximum allowed distance to consider rectangles as neighbors

    # Assign an index to each rectangle for easy reference
    rect_indices = {i: rect for i, rect in enumerate(rectangles)}

    # Step 1: Build the connectivity graph using the function
    graph = build_connectivity_graph(rect_indices, MAX_DISTANCE)

    # Step 2: Find connected components using the function
    components = find_connected_components(graph, rect_indices)

    # Step 3: Merge rectangles in each connected component
    merged_rectangles: List[Rectangle] = []

    for component in components:
        merged_rect = rect_indices[component[0]]
        for idx in component[1:]:
            merged_rect = merged_rect.merge_with(rect_indices[idx])
        merged_rectangles.append(merged_rect)

    # Step 4: Select the largest rectangle
    largest_rectangle: Rectangle = max(merged_rectangles, key=lambda r: r.area())

    annot = fitz_page[0].add_rect_annot(
        (
            largest_rectangle.x0,
            largest_rectangle.y0,
            largest_rectangle.x1,
            largest_rectangle.y1,
        )
    )
    blue = (0, 0, 1)
    gold = (1, 1, 0)
    annot.set_border(width=1, dashes=[1, 2])
    annot.set_colors(stroke=blue, fill=gold)
    annot.update(opacity=0.5)

    return largest_rectangle


def get_semester_and_year(date: datetime) -> Tuple[Semester, int]:
    month: int = date.month
    year: int = date.year

    if month in [1, 2]:
        semester = Semester.SPRING
    elif month in [5, 6]:
        semester = Semester.SUMMER
    elif month in [8, 9, 12]:
        semester = Semester.FALL
    else:
        raise ValueError(f"Invalid month: {month}")

    return semester, year
