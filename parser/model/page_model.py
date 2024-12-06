# Warren, if you could please add your code from the
# parser/model.py here, that would be great.
# Divide the base Foundation Exam Page model content
# and any QuestionFeaturization content into
# separate files as you see fit.

# TODO: Will separate better in the future - Warren

from enum import Enum, StrEnum
from typing import List, Tuple

import pymupdf as fitz  # pymupdf
from nltk import download as nltk_download
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from pydantic import BaseModel, Field

from parser.elements.rectangle import (
    Rectangle,
    build_connectivity_graph,
    find_connected_components,
)

NLTK_INITIALIZED: bool = False
PORTER_STEMMER: PorterStemmer | None = None
STOP_WORDS: set[str] | None = None


class TextLocation(BaseModel, strict=True):
    start_index: int
    end_index: int


def initialize_nltk():
    nltk_download("stopwords")
    nltk_download("punkt_tab")
    global STOP_WORDS
    STOP_WORDS = set(stopwords.words("english"))
    global PORTER_STEMMER
    PORTER_STEMMER = PorterStemmer()
    global NLTK_INITIALIZED
    NLTK_INITIALIZED = True


class Semester(StrEnum):
    SPRING = "Spring"
    SUMMER = "Summer"
    FALL = "Fall"


class PageType(StrEnum):
    SECTION = "Section"
    QUESTION = "Question"


class SectionType(StrEnum):
    BASIC_DATA_STRUCTURES = "Basic Data Structures"
    ADVANCED_DATA_STRUCTURES = "Advanced Data Structures"
    ALGORITHM_ANALYSIS = "Algorithm Analysis"
    ALGORITHMS = "Algorithms"


class Page(BaseModel, strict=True, arbitrary_types_allowed=True):
    page_type: PageType
    section_type: SectionType

    fitz_page: fitz.Page = Field(exclude=True)  # Prevent serialization

    # 0-indexed page numbers, not including the section page
    page_number: int

    text: str


class QuestionInputType(str, Enum):
    CODE_FREE_RESPONSE = "CODE_FREE_RESPONSE"
    CODE_FILL_BLANKS = "CODE_FILL_BLANKS"

    BOOLEAN = "BOOLEAN"

    #   MULTIPLE_CHOICE = "MULTIPLE_CHOICE"

    SHORT_ANSWER = "SHORT_ANSWER"
    LONG_ANSWER = "LONG_ANSWER"

    MATH_FREE_RESPONSE = "MATH_FREE_RESPONSE"
    MATH_SINGLE_ANSWER = "MATH_SINGLE_ANSWER"
    TIME_MILLISECONDS = "TIME"

    TABLE = "TABLE"
    LINKED_LIST_MODIFICATION = "LINKED_LIST_MODIFICATION"

    CONVERT_INFIX_TO_POSTFIX_WITH_STACK = "CONVERT_INFIX_TO_POSTFIX_WITH_STACK"
    CONVERT_INFIX_TO_POSTFIX_WITHOUT_STACK = "CONVERT_INFIX_TO_POSTFIX_WITHOUT_STACK"

    BASE_CONVERSION = "BASE_CONVERSION"

    TIME_COMPLEXITY = "TIME_COMPLEXITY"
    SPACE_COMPLEXITY = "SPACE_COMPLEXITY"

    TIME_COMPLEXITY_WITH_PROOF = "TIME_COMPLEXITY_WITH_PROOF"
    SPACE_COMPLEXITY_WITH_PROOF = "SPACE_COMPLEXITY_WITH_PROOF"

    INTEGER_ANSWER = "INTEGER_ANSWER"


# Define the structure for query responses
class QuestionClassification(BaseModel, strict=True):
    chain_of_thought: str = Field(
        ...,
        description="The chain of thought that led to the prediction.",
    )
    question_input_type: QuestionInputType = Field(
        ...,
        description="The type of input expectedfor the question.",
    )


# Define the structure for query responses
class QuestionDescription(BaseModel, strict=True):
    chain_of_thought: str = Field(
        ...,
        description="The chain of thought that led to the prediction.",
    )
    description: str = Field(
        ...,
        description="What the exam question is asking for.",
    )


class Text(BaseModel, strict=True):
    text: str
    location: TextLocation

    @staticmethod
    def from_string(text: str, parent_text: str, start_index: int) -> "Text":
        assert start_index != -1
        begin_index = parent_text.find(text, start_index)
        if begin_index == -1:
            print(f"Could not find '{text}' in '{parent_text}'")
            print(f"Start index: {start_index}")
            print(f"Parent text: {parent_text}")
            raise Exception("Could not find text")

        return Text(
            text=text,
            location=TextLocation(
                start_index=begin_index,
                end_index=begin_index + len(text),
            ),
        )


class ExtractionType(StrEnum):
    DEFAULT = "DEFAULT"

    CODE_FREE_RESPONSE = "CODE_FREE_RESPONSE"
    FILL_IN_THE_BLANKS = "FILL_IN_THE_BLANKS"
    LLM_BASED = "LLM_BASED"
    LINKED_LIST_MODIFICATION = "LINKED_LIST_MODIFICATION"


class ExtractionMetadata(BaseModel, strict=True):
    extraction_type: ExtractionType


ExtractionMetadatas = List[ExtractionMetadata]


class Metadata(BaseModel, strict=True):
    # original_text: str = Field(..., exclude=True)

    extraction_type: ExtractionType

    generated_name: str | None = None
    removed_stop_words: str | None = None
    lemmatized_text: str | None = None

    classification: QuestionClassification | None = None
    description: QuestionDescription | None = None
    classification_on_description: QuestionClassification | None = None

    bbox: Rectangle | None = None

    def run_bbox_search(
        self, original_text: str, fitz_page: List[fitz.Page], draw: bool = False
    ):
        if len(fitz_page) > 1:
            # multi-line question
            # ignore for now
            # TODO: Come back to
            return None

        bboxes: List[Tuple[float, float, float, float]] = fitz_page[0].search_for(
            original_text
        )

        if len(bboxes) == 0:
            print(f"No bboxes found for {original_text}")
            # raise ValueError(f"No bboxes found for {original_text}")
            return None

        rectangles: List[Rectangle] = [Rectangle.from_points(*bbox) for bbox in bboxes]

        MAX_DISTANCE = (
            800  # Maximum allowed distance to consider rectangles as neighbors
        )

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

        if draw:
            annot = fitz_page[0].add_rect_annot(
                (
                    largest_rectangle.x0,
                    largest_rectangle.y0,
                    largest_rectangle.x1,
                    largest_rectangle.y1,
                )
            )
            blue = (0, 0, 1)
            gold = (153 / 255, 240 / 255, 234 / 255)
            annot.set_border(width=1, dashes=[1, 2])
            annot.set_colors(stroke=blue, fill=gold)
            annot.update(opacity=0.5)

        self.bbox = largest_rectangle

    def run_nlp_preprocessing(self):
        self.removed_stop_words = self.remove_stop_words(self.original_text)
        self.lemmatized_text = self.lemmatize_text(self.removed_stop_words)

    def lemmatize_text(self, text: str) -> str:
        if not NLTK_INITIALIZED:
            initialize_nltk()
        assert PORTER_STEMMER is not None

        word_tokens = word_tokenize(text)
        lemmatized_sentence = [PORTER_STEMMER.stem(word) for word in word_tokens]
        return " ".join(lemmatized_sentence)

    def remove_stop_words(self, text: str) -> str:
        if not NLTK_INITIALIZED:
            initialize_nltk()
        assert STOP_WORDS is not None

        word_tokens = word_tokenize(text)
        # converts the words in word_tokens to lower case and then checks whether
        # they are present in stop_words or not
        filtered_sentence = [w for w in word_tokens if w.lower() not in STOP_WORDS]
        # with no lower case conversion
        filtered_sentence = []

        for w in word_tokens:
            if w not in STOP_WORDS:
                filtered_sentence.append(w)

        return " ".join(filtered_sentence)


class SubQuestion(BaseModel, strict=True):
    # text excluding the sub-question number and the "a) " prefix
    original_text: Text
    filtered_text: Text

    # eg. "a", "b", "c"
    identifier: str
    sub_questions: List["SubQuestion"]
    points: int | None = None
    metadata: Metadata


class Question(BaseModel, strict=True):
    pages: List[int]
    section_type: SectionType
    question_number: int
    max_points: int
    category: str
    sub_category: str

    # text excluding the question number, category, max points,
    original_text: str

    # original_text without the sub-questions
    filtered_text: str

    sub_questions: List[SubQuestion]
    metadata: Metadata


class Section(BaseModel, strict=True):
    # 0-indexed page numbers, not including the section page
    start_page: int
    end_page: int

    type: SectionType
    pages: List[Page]
    questions: List[Question] | None = None


def pages_as_string(pages: List[Page], include_metadata: bool = False) -> List[str]:
    result = []
    for page in pages:
        if include_metadata:
            result.append(
                f"Page {page.page_number}, SectionType: {page.section_type}, PageType: {page.page_type}"
            )
        result.append(page.text)
    return result


def sections_as_string(
    sections: List[Section], include_metadata: bool = False
) -> List[str]:
    result = []
    for section in sections:
        if include_metadata:
            result.append(
                f"Section {section.type}, StartPage: {section.start_page}, EndPage: {section.end_page}"
            )
        result.append(
            "\n".join(pages_as_string(section.pages, include_metadata=include_metadata))
        )
    return result


def questions_as_string(
    questions: List[Question], include_metadata: bool = False
) -> List[str]:
    result = []
    for question in questions:
        if include_metadata:
            result.append(
                f"Question {question.question_number}, SectionType: {question.section_type}, Category: {question.category}, SubCategory: {question.sub_category}"
            )
        result.append(question.filtered_text)
    return result
