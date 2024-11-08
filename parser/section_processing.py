from typing import List

from parser.model.page_model import Page, PageType, Section, SectionType


def get_sections(pages: List[Page]) -> List[Section]:
    sections: List[Section] = []
    last_section_type: SectionType | None = None
    pages_in_section: List[Page] = []
    for page in pages:
        if page.page_type == PageType.SECTION:
            if last_section_type is not None:
                sections.append(
                    Section(
                        type=last_section_type,
                        start_page=pages_in_section[0].page_number,
                        end_page=pages_in_section[-1].page_number,
                        pages=pages_in_section,
                    )
                )
                pages_in_section = []
            last_section_type = page.section_type
        else:
            assert last_section_type is not None
            pages_in_section.append(page)

    if last_section_type is None:
        raise ValueError("No sections found")

    sections.append(
        Section(
            type=last_section_type,
            start_page=pages_in_section[0].page_number,
            end_page=pages_in_section[-1].page_number,
            pages=pages_in_section,
        )
    )
    return sections
