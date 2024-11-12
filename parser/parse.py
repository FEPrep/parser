import os
import sys
from typing import List

from image_extractor.image_extraction import extract_images
from math_extractor.math_extraction import extract_math_text
from pydantic import BaseModel

from parser.dataset.exam import Exam
from parser.model.page_model import Section


class PreProcessedExam(BaseModel):
    sections: List[Section]


def main(input_file: str, output_file: str, verbose: bool = False):
    extract_images(input_file, output_dir="./parser/image_extractor/extracted-images")
    extract_math_text(input_file, output_dir="./parser/math_extractor/extracted-math")

    exam: Exam = Exam(input_file, None)
    exam.load_data(verbose)
    exam.write(output_file)


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


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python parse.py <input_file>", file=sys.stderr)
        sys.exit(1)

    input_file = sys.argv[1]

    output_file = (
        os.path.dirname(input_file)
        + "/"
        + os.path.basename(input_file).removesuffix(".pdf")
        + "_extracted.json"
    )

    main(input_file, output_file)
