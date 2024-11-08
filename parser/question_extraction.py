import re
import sys
from copy import copy
from typing import Dict, List

from parser.model.page_model import (
    Metadata,
    Page,
    PageType,
    Question,
    Section,
    SectionType,
    SubQuestion,
    Text,
)

# Define the regex pattern to extract questions
question_pattern = re.compile(
    r"(?s)\s*([1-5])\)\s*\((\d+)\s*pts\)\s*(\w+)\s*\(\s*([^)]+?)\s*\)\s*(.*?)(?=\s*[1-5]\)\s*\(\d+\s*pts\)\s*\w+\s*\([^)]+\)|\s*\Z)",
    re.DOTALL,
)

sub_question_pattern = re.compile(
    r"(?m)^\s*(?:\(\s*([a-z])\s*\)|([a-z])\.|([a-z])\))\s*(?:\(\s*(\d+)\s*pts?\s*\))?\s*([\s\S]*?)(?=^\s*(?:\(\s*[a-z]\s*\)|[a-z]\.|[a-z]\))|\Z)",
    re.DOTALL,
)


def get_questions(section: Section) -> List[Question]:
    questions: Dict[int, Question] = {}

    for i, page in enumerate(section.pages):
        assert page.page_type == PageType.QUESTION

        next: Page | None = section.pages[i + 1] if i + 1 < len(section.pages) else None

        next_plus_current = apply_header_filter(page.text) + (
            "\n" + apply_header_filter(next.text) if next is not None else ""
        )

        # Find all matches in the combined text of the current and next page

        current_questions: List[Question] = extract_questions(
            apply_header_filter(page.text), section.type
        )
        next_plus_current_questions: List[Question] = extract_questions(
            next_plus_current, section.type
        )

        for question in current_questions:
            question.pages.append(i + section.start_page)
            questions[question.question_number] = question

        for question in next_plus_current_questions:
            if question.question_number in questions:
                # this means that the question spanned multiple pages and the text spanning both pages should be updated

                if (
                    questions[question.question_number].filtered_text
                    != question.filtered_text
                ):
                    questions[
                        question.question_number
                    ].filtered_text = question.filtered_text
                    assert next is not None
                    questions[question.question_number].pages.append(
                        i + section.start_page + 1
                    )

    return sorted(questions.values(), key=lambda q: q.question_number)


def write_to_file(filename: str, content: str):
    try:
        with open(filename, "w") as file:
            file.write(content)
        print(f"Successfully wrote content to {filename}")
    except IOError as e:
        print(
            f"An error occurred while writing to {
              filename}: {e}",
            file=sys.stderr,
        )


def apply_header_filter(text: str) -> str:
    # remove the header and footer metadata

    new_text: List[str] = []
    split_text: List[str] = text.split("\n")

    for line in split_text:
        if line.startswith("Page"):
            continue
        if line.startswith("Summer"):
            continue
        if line.startswith("Spring"):
            continue
        if line.startswith("Fall"):
            continue
        new_text.append(line)

    return "\n".join(new_text)


def extract_questions(text: str, section_type: SectionType) -> List[Question]:
    questions: List[Question] = []
    matches = question_pattern.findall(text)

    for match in matches:
        question_number, max_points, category, sub_category, question_text = match

        original_text = question_text
        sub_questions = extract_sub_questions(question_text)
        for sub_question in sub_questions:
            question_text = question_text.replace(
                sub_question.original_text.text, ""
            ).strip()

        question = Question(
            pages=[],
            section_type=section_type,
            question_number=int(question_number),
            max_points=int(max_points),
            category=category,
            sub_category=sub_category,
            filtered_text=question_text,
            original_text=original_text,
            sub_questions=sub_questions,
            metadata=Metadata(),
        )

        questions.append(question)

    return questions


def extract_fill_in_the_blank_sub_questions(text: str) -> List[SubQuestion]:
    text_lines = text.split("\n")
    sub_questions: List[SubQuestion] = []

    current_index_in_master_text = 0
    for line in text_lines:
        # max_index_in_master_text = current_index_in_master_text + len(line)

        line_without_whitespace = line.replace(" ", "")
        if "_____" in line_without_whitespace and (
            "=" in line_without_whitespace
            or ":" in line_without_whitespace
            or ";" in line_without_whitespace
        ):
            sub_question = SubQuestion(
                identifier="",
                points=None,
                original_text=Text.from_string(
                    line, line, current_index_in_master_text
                ),
                filtered_text=Text.from_string(
                    line, line, current_index_in_master_text
                ),
                sub_questions=[],
                extracted_using_underscores=True,
            )
            sub_questions.append(sub_question)

        current_index_in_master_text += len(line) + 1  # +1 for the newline character

    return sub_questions


def is_outlier_sub_question(msg: str) -> bool:
    # Aug 17, Fall 2017 FE Page 16
    if " \n(a) int lowestOneBit(int n)" in msg:
        return True
    # Aug 17, Fall 2017 FE Page 16
    if " \n(b) int highestOneBit(int n)  - returns" in msg:
        return True

    return False


def extract_sub_questions(text: str) -> List[SubQuestion]:
    matches = sub_question_pattern.finditer(text)  # Use finditer to get match objects

    sub_questions: List[SubQuestion] = []

    for match in matches:
        # Extract the entire matched string
        original_text = match.group(0)

        if is_outlier_sub_question(original_text):
            print(f"Skipping outlier sub-question: {original_text}")
            continue

        question_text: str
        letter: str
        letter_alt: str
        letter_alt2: str
        points: str

        letter, letter_alt, letter_alt2, points, question_text = match.groups()
        assert (
            sum(x is not None and x != "" for x in [letter, letter_alt, letter_alt2])
            == 1
        ), f"Only one of letter, letter_alt, and letter_alt2 should be not None. letter='{letter}', letter_alt='{letter_alt}', letter_alt2='{letter_alt2}'"

        letter = letter if letter else letter_alt
        letter = letter if letter else letter_alt2

        question_text = question_text.strip()

        # Beginning of manual edge-case handling
        # Page 8
        if question_text.startswith("(b) "):
            question_text = question_text[3:]

        # End of manual edge-case handling

        sub_questions_in_sub_question = extract_sub_questions(question_text)

        if len(sub_questions_in_sub_question) == 0:
            sub_questions_in_sub_question = extract_fill_in_the_blank_sub_questions(
                question_text
            )

        filtered_text = copy(question_text)
        for sub_question in sub_questions_in_sub_question:
            filtered_text = question_text.replace(
                sub_question.original_text.text, ""
            ).strip()

        sub_question = SubQuestion(
            identifier=letter,
            points=int(points) if points else None,
            filtered_text=Text.from_string(
                filtered_text, original_text, text.find(original_text)
            ),
            original_text=Text.from_string(
                original_text, original_text, text.find(original_text)
            ),
            sub_questions=sub_questions_in_sub_question,
            extracted_using_underscores=False,
        )
        sub_questions.append(sub_question)

    if len(sub_questions) == 0:
        sub_questions = extract_fill_in_the_blank_sub_questions(text)

    return sub_questions
