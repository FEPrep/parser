import fitz
import json
import os
from parser.model.image_model import ImagePosition, ImageModel


def extract_metadata(input_file: str, output_dir: str, page_number: int) -> None:
    pdf_document = fitz.open(input_file)
    page = pdf_document[page_number]
    images = page.get_images(full=True)

    os.makedirs(output_dir, exist_ok=True)

    for img_index, img in enumerate(images):
        xref = img[0]
        ref_name = img[7]

        rects = page.get_image_rects(xref)
        for rect in rects:
            position = ImagePosition(
                xref=xref,
                ref_name=ref_name,
                x0=rect.x0,
                y0=rect.y0,
                x1=rect.x1,
                y1=rect.y1,
                width=rect.width,
                height=rect.height,
            )

            # instantiate the image model
            image_model = ImageModel(
                src=f"images/page{page_number + 1}_img{img_index + 1}.png",
                position=position,
            )

            metadata_filename = f"page_{page_number + 1}_img_{img_index + 1}.json"

            metadata_path = os.path.join(output_dir, metadata_filename)

            with open(metadata_path, "w") as file:
                json.dump(image_model.dict(), file, indent=4)

    pdf_document.close()
