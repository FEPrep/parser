import os
import fitz

# Allow some wiggle room when testing the difference between potential numerators and denominators
FRACTION_MIDPOINT_DIFF_THRESHOLD = 0.5


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

        # Iterate through the math spans
        i = 0
        while i < len(math_spans):
            print("===========================")
            span = math_spans[i]

            num_sigmas = span["text"].count("\u2211")
            if num_sigmas > 0:
                process_summation(math_spans, i, num_sigmas)
                i += 2 * num_sigmas  # Already processed the bounds with the summation
            elif is_numerator(math_spans, i):
                process_fraction(span, math_spans[i + 1])
                i += (
                    1  # Already processed the next span (denominator) with the fraction
                )
            else:
                print(f"value: {span["text"]}, flags: {span["flags"]}")

            print({span["bbox"]})

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


# Compares the current span to the next span to determine whether
# the current span is the next span's numerator
def is_numerator(span_list, idx):
    # Ensure the next span exists
    if idx + 1 < len(span_list):
        cur_bbox = span_list[idx]["bbox"]
        next_bbox = span_list[idx + 1]["bbox"]
        x_midpoint_diffs = abs(
            ((cur_bbox[0] - cur_bbox[2]) / 2) - ((next_bbox[0] - next_bbox[2]) / 2)
        )
        # todo: resolve: might not be enough to catch all numerators
        return x_midpoint_diffs < FRACTION_MIDPOINT_DIFF_THRESHOLD

    return False


def process_fraction(numerator, denominator):
    assert denominator
    print(f"fraction: {numerator["text"]} / {denominator["text"]}")
