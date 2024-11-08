import re
from typing import List

from parser.model.page_model import Question, QuestionInputType


class InputTypeExtraction:
    def __init__(self, question: Question):
        self.question = question

    def extract_possible_input_types(self) -> List[QuestionInputType]:
        if self.is_code_free_response():
            return [QuestionInputType.CODE_FREE_RESPONSE]

        if self.has_fill_in_the_blank_input_type():
            return [
                QuestionInputType.CODE_FILL_BLANKS,
                QuestionInputType.MULTIPLE_CHOICE,
            ]

        return []

    def is_code_free_response(self) -> bool:
        # This is a very confident/foolproof check to determine if the question text
        # contains a code free response pattern, which is identified by having '{'
        # followed by at least 8 newlines and then '}'.
        return contains_braces_with_newlines(self.question.filtered_text, 8)

    def has_fill_in_the_blank_input_type(self) -> bool:
        # This is a very confident/foolproof check to determine if the question text
        # contains a fill in the blank input type pattern, which is identified by having
        # '__' followed by at least 8 newlines.
        return contains_multiple_underscore_delimiters(self.question.filtered_text)


def contains_multiple_underscore_delimiters(text: str) -> bool:
    # This is a very confident/foolproof check to determine if the question text
    # contains a multiple underscore delimiters pattern, which is identified by having
    # '__' followed by at least 8 newlines and then ']'.
    substring = "_" * 8
    return substring in text


def contains_braces_with_newlines(text: str, n: int) -> bool:
    """
    Checks if the text contains a substring with '{' followed by at least n newlines and then '}'.

    Args:
    text (str): The input string to check.
    n (int): The minimum number of newlines to look for between '{' and '}'.

    Returns:
    bool: True if the pattern is found, False otherwise.
    """
    pattern = r"\{" + r"(?:\n){" + str(n) + r",}\}"
    return re.search(pattern, text) is not None
