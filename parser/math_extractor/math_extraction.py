import os
import fitz


# Extract all math text into json containing necessary metadata / context
def extract_math_text(pdf_path, output_dir):
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = os.path.join(output_dir, pdf_name)
    os.makedirs(output_dir, exist_ok=True)

    pdf_document = fitz.open(pdf_path)
    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        text_blocks = page.get_text("dict")["blocks"]

        math_spans = get_math_span_list(text_blocks)

        bounds_to_process = 0
        for span in math_spans:
            print("===========================")
            if bounds_to_process > 0:
                if bounds_to_process % 2 == 0:
                    print("type: upper bound")
                else:
                    print("type: lower bound")

                bounds_to_process -= 1
            else:
                bounds_to_process = 2 * amt_summations_in_span(span)
                if bounds_to_process > 0:
                    print("type: summation")
                else:
                    print("type: not summation")

            print(f"value: {span["text"]}")
            print("===========================")


# Returns a list of spans containing math text
def get_math_span_list(text_blocks):
    result = []
    for block in text_blocks:
        # Only process text blocks
        if block["type"] == 0:
            for line in block["lines"]:
                for span in line["spans"]:
                    if span["font"] == "CambriaMath":
                        result.append(span)

    return result


def amt_summations_in_span(span):
    return span["text"].count("\u2211")
