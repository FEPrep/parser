import io
import os

import fitz

# from PIL import Image
from Typing import List
from metadata_extraction import extract_metadata
from models import Image


def extract_images(pdf_path, output_dir) -> List[Image]:
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = os.path.join(output_dir, pdf_name)
    os.makedirs(output_dir, exist_ok=True)
    pdf_document = fitz.open(pdf_path)
    metadata_list = []

    for page_number in range(len(pdf_document)):
        page = pdf_document[page_number]
        images = page.get_images(full=True)

        for img_index, img in enumerate(images):
            xref = img[0]
            base_image = pdf_document.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            image = Image.open(io.BytesIO(image_bytes))

            # add conversion to see if this fixes the black image issue
            image = image.convert("RGB")
            # fun fact: this did not fix the black image issue

            image_path = os.path.join(
                output_dir,
                f"page_{page_number + 1}_img_{img_index + 1}.{image_ext}",
            )
            image.save(image_path)

            metadata = extract_metadata(img_index, xref, page, image_ext, image_path)
            metadata_list.append(metadata)

    pdf_document.close()
    print(f"Images successfully extracted and saved to {output_dir}.")
    return metadata_list
