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

        i = 0
        while i < len(math_spans):
            print("===========================")
            print(f"i = {i}")
            span = math_spans[i]

            num_sigmas = span["text"].count("\u2211")
            if num_sigmas > 0:
                process_summation(math_spans, i, num_sigmas)
                i += 2 * num_sigmas
            else:
                print(f"value: {span["text"]}")

            i += 1
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


# Saves a span containing one or more summations in the correct output format
def process_summation(span_list, idx, num_sigmas):
    sum_span = span_list[idx]
    print(f"summation: {sum_span["text"]}")

    for i in range((2 * num_sigmas), 0, -1):
        bound_type = "upper" if i % 2 == 1 else "lower"
        print(f"{bound_type} bound: {span_list[idx+i]["text"]}")
