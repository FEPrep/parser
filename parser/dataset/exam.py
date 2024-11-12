import re
import sys
from datetime import datetime
from typing import List, Tuple

import pymupdf  # pymupdf
from pydantic import BaseModel

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
            document = pymupdf.open(self.exam_path)

            # Process the PDF content here
            # For example, you could extract text from each page:
            pages: List[Page] = []
            previous_section_type: SectionType | None = None
            for page_number in range(len(document)):
                page = document.load_page(page_number)
                text = page.get_text(sort=True)
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
                )
                pages.append(new_page)

                previous_section_type = section_type

            if verbose:
                write_to_file(
                    "raw.txt", "\n".join(pages_as_string(pages, include_metadata=False))
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
                section.questions = questions

            self.sections = sections

            self.loaded = True
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
