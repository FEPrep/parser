import os
import fitz


def extract_math_text(pdf_path, output_dir):
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = os.path.join(output_dir, pdf_name)
    os.makedirs(output_dir, exist_ok=True)

    pdf_document = fitz.open(pdf_path)
    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        text_blocks = page.get_text("dict")["blocks"]

        for block in text_blocks:
            # Only process text blocks (type 0)
            if block["type"] == 0:
                for line in block["lines"]:
                    for span in line["spans"]:
                        if span["font"] == "CambriaMath":
                            print(
                                f"{span["text"]}\non page {page_num} with bbox {span["bbox"]}"
                            )
