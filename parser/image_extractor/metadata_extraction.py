import fitz
import json
import os
from typing import List
from parser.model.image_model import Position


def extract_metadata(input_file: str, output_file: str, page_number: int) -> None:
    pdf_document = fitz.open(input_file)
    page = pdf_document[page_number]
    images = page.get_images(full=True)

    image_positions = []

    for img_index, img in enumerate(images):
        xref = img[0]
        ref_name = img[7]
        # base_image = pdf_document.extract_image(xref)
        # image_ext = base_image["ext"]

        rects = page.get_image_rects(xref)
        for rect in rects:
            position = Position(
                xref=xref,
                ref_name=ref_name,
                x0=rect.x0,
                y0=rect.y0,
                x1=rect.x1,
                y1=rect.y1,
                width=rect.width,
                height=rect.height,
            )

            # metadata_output = os.path.join(
            #     output_file,
            #     f"page_{page_number + 1}_img_{img_index + 1}.{image_ext}",
            # )
            print(f"Extracted metadata for image: {position}")
            image_positions.append(position)

    pdf_document.close()
    write_metadata_to_json(
        image_positions,
        os.path.basename(output_file),
        output_directory="./parser/image_extractor/extracted-metadata",
    )


def write_metadata_to_json(
    image_positions: List[Position], output_file: str, output_directory: str
) -> None:
    updated_path = os.path.join(output_directory, output_file)

    os.makedirs(os.path.dirname(updated_path), exist_ok=True)

    with open(updated_path, "w") as file:
        json.dump([position.dict() for position in image_positions], file, indent=4)

    print(f"Metadata successfully written to {updated_path}")
    print("JSON file successfully written to: ", updated_path)
