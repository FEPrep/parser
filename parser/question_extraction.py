import re
import sys
from copy import copy
from typing import Dict, List

import regex

from parser.model.page_model import (
    ExtractionType,
    Metadata,
    Page,
    PageType,
    Question,
    Section,
    SectionType,
    SubQuestion,
    Text,
)

QUESTION_PATTERN = re.compile(
    r"(?s)\s*([1-5])\)\s*\((\d+)\s*pts\)\s*(\w+)\s*\(\s*([^)]+?)\s*\)\s*(.*?)(?=\s*[1-5]\)\s*\(\d+\s*pts\)\s*\w+\s*\([^)]+\)|\s*\Z)",
    re.DOTALL,
)
"""
A regex pattern to extract questions from text.

This pattern is designed to match questions that follow a specific format:
- A number (1-5) followed by a closing parenthesis.
- A point value enclosed in parentheses, e.g., "(10 pts)".
- A category represented by a word.
- A sub-category enclosed in parentheses.
- The question text itself, which can span multiple lines.

The pattern uses lookahead to ensure it captures the question text up to the
next question or the end of the text.

Flags:
- `(?s)`: Enables DOTALL mode, allowing the dot (.) to match newline characters.
"""


SUB_QUESTION_PATTERN = re.compile(
    r"(?m)^\s*(?:\(\s*([a-z])\s*\)|([a-z])[.)])\s*(?:\(\s*(\d+)\s*pts?\s*\))?\s*([\s\S]*?)(?=^(?:\(\s*[a-z]\s*\)|[a-z][.)])|\Z)",
    re.DOTALL,
)
"""
A regex pattern to extract sub-questions from text.

This pattern is designed to match sub-questions that follow a specific format:
- An optional identifier (a-z) enclosed in parentheses, followed by a period, or followed by a closing parenthesis.
- An optional point value enclosed in parentheses, e.g., "(5 pts)".
- The sub-question text itself, which can span multiple lines.

The pattern uses lookahead to ensure it captures the sub-question text up to
the next sub-question or the end of the text.

Flags:
- `(?m)`: Enables MULTILINE mode, allowing the start (^) and end ($) anchors to match the start and end of each line.
- `re.DOTALL`: Allows the dot (.) to match newline characters, enabling the capture of multi-line sub-question text.
"""


def get_questions(section: Section) -> List[Question]:
    """
    Extracts and organizes questions from a given section.

    This function processes each page in the provided section to extract
    questions using regex patterns. It handles questions that may span
    multiple pages by combining the text of the current and next page.
    The function ensures that each question is associated with the correct
    page numbers and updates the question text if it spans multiple pages.

    Args:
        section (Section): The section containing pages from which to extract questions.

    Returns:
        List[Question]: A sorted list of Question objects, each representing
        a parsed question with its associated metadata and page numbers.
    """
    questions: Dict[int, Question] = {}

    for i, page in enumerate(section.pages):
        # Ensure the page is of the correct type
        assert page.page_type == PageType.QUESTION

        # Get the next page if it exists
        next: Page | None = section.pages[i + 1] if i + 1 < len(section.pages) else None

        # Combine the text of the current and next page after filtering headers
        next_plus_current = apply_header_filter(page.text) + (
            "\n" + apply_header_filter(next.text) if next is not None else ""
        )

        # Extract questions from the current page
        current_questions: List[Question] = extract_questions(
            apply_header_filter(page.text), section.type
        )
        # Extract questions from the combined text of current and next page
        next_plus_current_questions: List[Question] = extract_questions(
            next_plus_current, section.type
        )

        # Process questions found in the current page
        for question in current_questions:
            # Add the current page number to the question's page list
            question.pages.append(i + section.start_page)
            questions[question.question_number] = question

        # Process questions found in the combined text
        for question in next_plus_current_questions:
            # If the question spans multiple pages, update its text and pages
            if (
                question.question_number in questions
                and questions[question.question_number].filtered_text
                != question.filtered_text
            ):
                # Update the question's text
                questions[
                    question.question_number
                ].filtered_text = question.filtered_text
                # Ensure the next page exists before appending its number
                assert next is not None
                # Add the next page number to the question's page list
                questions[question.question_number].pages.append(
                    i + section.start_page + 1
                )

    # Return the questions sorted by their question number
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
    """
    Removes header and footer metadata from the provided text.

    This function processes the input text line by line, filtering out lines
    that start with specific keywords typically used in headers or footers,
    such as "Page", "Summer", "Spring", and "Fall". The remaining lines are
    joined back into a single string.

    Args:
        text (str): The text from which to remove header and footer metadata.

    Returns:
        str: The filtered text with header and footer lines removed.
    """
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
    """
    Extracts questions from a given text based on a predefined regex pattern.

    This function uses a regex pattern to identify and extract questions from
    the provided text. Each question is parsed into its components, including
    the question number, maximum points, category, sub-category, and the
    question text itself. Sub-questions are also extracted and processed to
    remove their text from the main question text.

    Args:
        text (str): The text from which to extract questions.
        section_type (SectionType): The type of section the questions belong to.

    Returns:
        List[Question]: A list of Question objects, each representing a parsed
        question with its associated metadata and sub-questions.
    """
    questions: List[Question] = []
    matches = QUESTION_PATTERN.findall(text)

    for match in matches:
        question_number, max_points, category, sub_category, question_text = match

        original_text = copy(question_text)
        sub_questions = extract_sub_questions(question_text)
        for sub_question in sub_questions:
            question_text = question_text.replace(sub_question.original_text.text, "")

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
            metadata=Metadata(extraction_type=ExtractionType.DEFAULT),
        )

        questions.append(question)

    return questions


def extract_fill_in_the_blank_sub_questions(text: str) -> List[SubQuestion]:
    """
    Extracts fill-in-the-blank sub-questions from a given text, handling each
    independently, including multi-line underscores, based on the specified formats.
    """
    text_lines = text.splitlines(
        keepends=True
    )  # Keep line endings for accurate indexing
    sub_questions: List[SubQuestion] = []

    # Initialize variables
    is_collecting = False
    start_index = None
    found_underscore = (
        False  # Ensure underscores are found before creating a sub-question
    )

    # Compute cumulative lengths of lines for accurate indexing
    line_lengths = [len(line) for line in text_lines]
    cumulative_lengths = [0]
    for length in line_lengths:
        cumulative_lengths.append(cumulative_lengths[-1] + length)

    for i, line in enumerate(text_lines):
        stripped_line = line.strip()
        line_without_whitespace = line.replace(" ", "").lstrip(
            "-"
        )  # Ignore leading hyphens
        contains_underscore = "_____" in line_without_whitespace

        # Determine if the line contains ':', '=', or ';'
        line_contains_colon = any(
            char in line_without_whitespace for char in [":", "=", ";"]
        )

        # Check if the line starts a sub-question
        starts_fill_in = line_contains_colon

        if starts_fill_in:
            # If we're already collecting, finalize the previous sub-question
            if is_collecting and found_underscore:
                end_index = cumulative_lengths[i]
                question_text = text[start_index:end_index]
                question_text_obj = Text.from_string(question_text, text, start_index)
                sub_question = SubQuestion(
                    identifier="",
                    points=None,
                    original_text=question_text_obj,
                    filtered_text=question_text_obj,
                    sub_questions=[],
                    metadata=Metadata(
                        extraction_type=ExtractionType.FILL_IN_THE_BLANKS
                    ),
                )
                sub_questions.append(sub_question)
            # Start collecting the new sub-question
            is_collecting = True
            start_index = cumulative_lengths[i]
            found_underscore = contains_underscore
        elif is_collecting:
            # Continue collecting lines
            if stripped_line == "" or contains_underscore:
                if contains_underscore:
                    found_underscore = True
                # Keep collecting
            else:
                # End of the current sub-question
                if found_underscore:
                    end_index = cumulative_lengths[i]
                    question_text = text[start_index:end_index]
                    question_text_obj = Text.from_string(
                        question_text, text, start_index
                    )
                    sub_question = SubQuestion(
                        identifier="",
                        points=None,
                        original_text=question_text_obj,
                        filtered_text=question_text_obj,
                        sub_questions=[],
                        metadata=Metadata(
                            extraction_type=ExtractionType.FILL_IN_THE_BLANKS
                        ),
                    )
                    sub_questions.append(sub_question)
                # Reset flags
                is_collecting = False
                start_index = None
                found_underscore = False

    # Handle any remaining collected lines at the end of the text
    if is_collecting and found_underscore:
        end_index = cumulative_lengths[-1]
        question_text = text[start_index:end_index]
        question_text_obj = Text.from_string(question_text, text, start_index)
        sub_question = SubQuestion(
            identifier="",
            points=None,
            original_text=question_text_obj,
            filtered_text=question_text_obj,
            sub_questions=[],
            metadata=Metadata(extraction_type=ExtractionType.FILL_IN_THE_BLANKS),
        )
        sub_questions.append(sub_question)

    return sub_questions


# Regular expression as defined above
FUNCTION_EXTRACTION_PATTERN = regex.compile(
    r"""
    (?P<return_type>
        (?:
            [\w\*\&\[\]]+          # Match return type characters
            (?:\s+|/[*].*?[*]/)+    # Match whitespace or comments
        )+
    )
    (?P<function_name>\w+)\s*
    \(
        (?P<arguments>
            (?:[^()]*|\((?:[^()]|\([^()]*\))*\))*
        )
    \)\s*
    (?P<body>
        \{
            (?:
                [^{}]+
                |
                (?&body)
            )*
        \}
    )
    """,
    regex.MULTILINE | regex.DOTALL | regex.VERBOSE,
)
"""
Examples Code:
int add(int a, int b) {
    return a + b;
}

void swap(int *a, int *b) {
    int temp = *a;
    *a = *b;
    *b = temp;
}

static inline int max(int a, int b) {
    return a > b ? a : b;
}

struct node* create_node(int data) {
    struct node* new_node = (struct node*)malloc(sizeof(struct node));
    new_node->data = data;
    new_node->next = NULL;
    return new_node;
}

void (*signal(int sig, void (*func)(int)))(int) {
    // function body
}

void complex_function(
    int a,
    char *b,
    double (*c)(int)
) {
    // code
}

void process_array(int arr[], size_t size) {
    for (size_t i = 0; i < size; ++i) {
        // process arr[i]
    }
}

void no_arguments(void) {
    // code
}

const char* const* get_strings(void) {
    static const char* strs[] = {"hello", "world", NULL};
    return strs;
}

int compute(int **matrix, int rows, int cols) {
    int sum = 0;
    for(int i = 0; i < rows; ++i) {
        for(int j = 0; j < cols; ++j) {
            sum += matrix[i][j];
        }
    }
    return sum;
}
"""


def extract_code_free_response_sub_questions(text: str) -> List[SubQuestion]:
    """
    Extracts code-free-response sub-questions from a given text.

    This function scans through each line of the provided text to identify
    sub-questions that are formatted as code-free-response. A line is considered
    a code-free-response sub-question if it contains more than 10 repeated new line characters
    beginning with an opening bracket and ending with a closing bracket and

    Args:
        text (str): The text from which to extract fill-in-the-blank sub-questions.

    Returns:
        List[SubQuestion]: A list of SubQuestion objects representing each
        identified fill-in-the-blank sub-question. Each SubQuestion includes
        the original text, filtered text, and metadata indicating it was
        extracted using underscores.
    """

    # Find all matches
    matches = FUNCTION_EXTRACTION_PATTERN.finditer(text)

    sub_questions: List[SubQuestion] = []

    for match in matches:
        raw = match.group(0)
        function_name = match.group("function_name")
        # arguments = match.group("arguments")
        body = match.group("body")

        # print(f"Function name: {function_name}")
        # print(f"Arguments: {arguments.strip()}")
        # print(f"Body:\n{body.strip()}")
        # print("-" * 50)

        if largest_subsequence_of_empty_strings(body.split("\n")) < 5:
            print(f"Skipping code-free-response sub-question: {raw}")
            continue

        question_text: Text = Text.from_string(raw, text, 0)

        sub_question = SubQuestion(
            identifier=function_name,
            points=None,
            original_text=question_text,
            filtered_text=question_text,
            sub_questions=[],
            metadata=Metadata(extraction_type=ExtractionType.CODE_FREE_RESPONSE),
        )
        sub_questions.append(sub_question)

    return sub_questions


def largest_subsequence_of_empty_strings(text: List[str]) -> int:
    """
    Finds the length of the largest subsequence of empty strings in the given list.

    This function iterates through the list of strings, counting consecutive empty strings
    and returns the length of the longest such subsequence.

    Args:
        text (List[str]): A list of strings to analyze.
    """
    max_length = 0
    current_length = 0

    for string in text:
        if string.strip() == "":
            current_length += 1
            max_length = max(max_length, current_length)
        else:
            current_length = 0

    return max_length


def is_ignorable_outlier_sub_question(msg: str) -> bool:
    """
    Determines if a given sub-question message is considered an outlier.

    This function checks if the provided message contains specific patterns
    that are known to be outliers in the context of sub-questions. These
    patterns are hardcoded and are used to identify sub-questions that
    should be skipped during processing.

    Args:
        msg (str): The message string of the sub-question to be checked.

    Returns:
        bool: True if the message is an outlier, False otherwise.
    """
    # Aug 17, Fall 2017 FE Page 16
    if "int lowestOneBit(int n) - returns" in msg:
        return True
    # Aug 17, Fall 2017 FE Page 16
    if "int highestOneBit(int n) - returns" in msg:
        return True

    return False


def handle_question_edge_cases(question_text: str) -> str:
    """
    Handles edge cases in the question text.

    This function processes the input question text to correct common formatting
    issues that often accompany sub-questions. For example, it removes leading "(b) " from the
    text and ensures the text is properly capitalized.

    Args:
        question_text (str): The question text to be processed.

    Returns:
        str: The processed question text with common formatting issues corrected.
    """
    # Remove leading "(b) " from the text
    if question_text.startswith("(b) "):
        question_text = question_text[3:]
    # Ensure the text is properly capitalized
    return question_text


def extract_sub_questions(text: str) -> List[SubQuestion]:
    """
    Extracts sub-questions from a given text using a regex pattern.

    This function identifies sub-questions within the provided text by using
    a predefined regex pattern. It processes each match to extract relevant
    details such as the sub-question identifier, points, and text. The function
    also handles nested sub-questions and fill-in-the-blank sub-questions.

    Args:
        text (str): The text from which to extract sub-questions.

    Returns:
        List[SubQuestion]: A list of SubQuestion objects, each representing a
        parsed sub-question with its associated metadata and any nested
        sub-questions.
    """
    matches = SUB_QUESTION_PATTERN.finditer(text)  # Use finditer to get match objects

    sub_questions: List[SubQuestion] = []

    for match in matches:
        # Extract the entire matched string
        original_text = match.group(0)

        if is_ignorable_outlier_sub_question(original_text):
            print(f"Skipping outlier sub-question: {original_text}")
            continue

        question_text: str
        letter: str
        letter_alt: str
        points: str

        letter, letter_alt, points, question_text = match.groups()
        assert (
            sum(x is not None and x != "" for x in [letter, letter_alt]) == 1
        ), f"Only one of letter, letter_alt, and letter_alt2 should be not None. letter='{letter}', letter_alt='{letter_alt}'"

        letter = letter if letter else letter_alt
        # letter = letter if letter else letter_alt2

        question_text = question_text.strip()

        question_text = handle_question_edge_cases(question_text)

        sub_questions_in_sub_question = extract_sub_questions(question_text)

        if len(sub_questions_in_sub_question) == 0:
            sub_questions_in_sub_question = extract_fill_in_the_blank_sub_questions(
                question_text
            )

        if len(sub_questions_in_sub_question) == 0:
            sub_questions_in_sub_question = extract_code_free_response_sub_questions(
                question_text
            )

        filtered_text = copy(question_text)
        for sub_question in sub_questions_in_sub_question:
            print(f"sub_question.original_text={sub_question.original_text}")
            filtered_text = filtered_text.replace(
                sub_question.original_text.text, ""
            ).strip()

        print(f"filtered_text={filtered_text}")

        sub_question = SubQuestion(
            identifier=letter,
            points=int(points) if points else None,
            filtered_text=Text.from_string(filtered_text, text, 0),
            original_text=Text.from_string(original_text, text, 0),
            sub_questions=sub_questions_in_sub_question,
            metadata=Metadata(extraction_type=ExtractionType.DEFAULT),
        )
        sub_questions.append(sub_question)

    if len(sub_questions) == 0:
        sub_questions = extract_fill_in_the_blank_sub_questions(text)

    if len(sub_questions) == 0:
        sub_questions = extract_code_free_response_sub_questions(text)

    return sub_questions
