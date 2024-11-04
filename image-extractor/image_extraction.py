import fitz
import io
import os
from PIL import Image
import sys

if len(sys.argv) != 2:
    print("Usage: python image_extractor/image_extraction.py path/to/directory")
    sys.exit(1)

directory_path = sys.argv[1]
if not os.path.isdir(directory_path):
    print("The provided path is not a directory.")
    sys.exit(1)

for filename in os.listdir(directory_path):
    if filename.endswith(".pdf"):
        pdf_path = os.path.join(directory_path, filename)
        pdf_name = os.path.splitext(filename)[0]
        output_dir = f"./extracted-images/{pdf_name}"
        os.makedirs(output_dir, exist_ok=True)
        pdf_document = fitz.open(pdf_path)

        for page_number in range(len(pdf_document)):
            page = pdf_document[page_number]
            images = page.get_images(full=True)

            for img_index, img in enumerate(images):
                xref = img[0]
                base_image = pdf_document.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                image = Image.open(io.BytesIO(image_bytes))
                image_path = os.path.join(
                    output_dir,
                    f"page_{page_number + 1}_img_{img_index + 1}.{image_ext}",
                )
                image.save(image_path)

        pdf_document.close()
        print(f"Image successfully extracted and saved to {output_dir}.")

print(
    "\nAll images successfully extracted from PDF files and saved to the extracted-images directory."
)
