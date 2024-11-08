import re
from datetime import datetime
from typing import Tuple

from parser.model.page_model import PageType, SectionType


def extract_date_from_page(text: str) -> datetime | None:
    # print("text: ", text)
    """
    Extracts a date in the format "May 22, 2021" from a string.

    Args:
    text (str): The input string containing the date.

    Returns:
    datetime | None: The extracted date as a datetime object or None if no date is found.
    """
    match = re.search(r"\b([A-Za-z]+\d{1,2},\d{4})\b", text.replace(" ", ""))
    if match:
        return datetime.strptime(match.group(0), "%B%d,%Y")
    return None


def extract_section_info(text: str) -> Tuple[str, str] | None:
    """
    Extracts section letter and name from a string containing "Section A: XYZ" format.

    Args:
    text (str): The input string containing section information.

    Returns:
    Tuple[str, str]: A tuple containing the section letter and section name.
    """

    # Looking for the following 2 lines:
    # Section A
    # BASIC DATA STRUCTURES
    # post 2022 exam regex
    match = re.search(r"Section\s+([A-D])(?:\s+|\n)(.*?)(?:\n|$)", text, re.DOTALL)
    if match is None:
        # print("unable to get section letter using Regex, must be pre 2022 Exam")
        # Looking for the following 2 lines:
        # Section I  A
        # DATA STRUCTURES
        # pre 2022 exam regex
        match = re.search(
            r"Section\s+([I|I I]+)\s+([A-Z])\s*\n(.*?)(?:\n|$)", text, re.DOTALL
        )
        # print("1", match)
        # print("initial match: ", match)
        if match:
            # print("FOUND MATCH")
            section_number, section_letter, section_name = match.groups()
            section_number = section_number.strip()
            section_letter = section_letter.strip()
            section_name = section_name.strip()

            if section_number == "I":
                if section_letter == "A":
                    return ("A", "Data Structures")
                elif section_letter == "B":
                    return ("B", "Advanced Data Structures")
                else:
                    return None
            elif section_number == "II" or section_number == "I I":
                if section_letter == "A":
                    return ("A", "Algorithm Analysis")
                elif section_letter == "B":
                    return ("B", "Algorithms")
                else:
                    return None

            return (section_letter, section_name.strip())

        return None

    return (match.group(1), match.group(2).strip())


def get_page_type(text: str) -> PageType | None:
    if "Computer Science Foundation Exam" in text:
        return PageType.SECTION
    return PageType.QUESTION


def get_section_type(text: str) -> SectionType | None:
    section_info = extract_section_info(text)

    if section_info is None:
        print("unable to get section info")
        return None

    section_letter, section_name = section_info

    section_name = " ".join(
        [x.strip() for x in section_name.split(" ") if x.strip() != ""]
    )

    if "Advanced Data Structures".lower() in section_name.lower():
        return SectionType.ADVANCED_DATA_STRUCTURES
    elif "Data Structures".lower() in section_name.lower():
        return SectionType.BASIC_DATA_STRUCTURES
    elif "Algorithm Analysis".lower() in section_name.lower():
        return SectionType.ALGORITHM_ANALYSIS
    elif "Algorithms".lower() in section_name.lower():
        return SectionType.ALGORITHMS
    return None
