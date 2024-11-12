# Scrapes and stores all PDFs from the previous FE webpage

import json
import os
import re

import requests
from bs4 import BeautifulSoup


# Is the tag a PDF link for an exam that has no discrete section?
def pdf_after_discrete(tag):
    is_anchor = tag.has_attr("href")
    contains_pdf = is_anchor and re.search(".pdf", tag["href"])
    pdf_not_labeled_with_CS_or_DS = contains_pdf and not re.search("CS|DS", tag["href"])

    if pdf_not_labeled_with_CS_or_DS:
        # All exams after August 2016 contain no discrete section
        year_match = re.search(r"[0-9]{4}", tag["href"])
        if year_match:
            year = int(year_match.group())
            # Return true if the exam was after August 2016
            return (year > 2016) or (
                year == 2016 and not re.search("aug|may", tag["href"], re.IGNORECASE)
            )

    return False


# Return a string describing the type of exam document
def get_document_type(file_name):
    if re.search(r"sol", file_name, re.IGNORECASE):
        return "solutions"
    elif re.search(r"info", file_name, re.IGNORECASE):
        return "info"
    else:
        return "exam"


JsonOutputType = dict[str, dict[str, dict[str, str]]]
json_output: JsonOutputType = {"documents": {}}

url = "https://www.cs.ucf.edu/registration/exm/"
read = requests.get(url)  # Get request for HTML
html = read.content
soup = BeautifulSoup(html, "html.parser")

pdf_anchors = soup.find_all(pdf_after_discrete)

pdfs_dir = "pdfs"
if not os.path.exists(pdfs_dir):
    os.makedirs(pdfs_dir)

for pdf_anchor in pdf_anchors:
    # Make the directory for the current exam
    dir_name = re.findall(r"^[^\/]+", pdf_anchor.get("href"))[0]
    if not os.path.exists(pdfs_dir + "/" + dir_name):
        os.makedirs(pdfs_dir + "/" + dir_name)

    # Initialize empty dict entry for dir_name if one doesn't already exist
    if dir_name not in json_output["documents"]:
        json_output["documents"][dir_name] = {}

    cur_link = pdf_anchor.get("href")
    response = requests.get(url + cur_link)

    # Create path string for the current PDF
    file_name = cur_link.rsplit("/", 1)[-1]
    doc_type = get_document_type(file_name)
    path = pdfs_dir + "/" + dir_name + "/" + file_name

    # Configure json output
    json_output["documents"][dir_name][doc_type] = path

    # Store the PDF
    pdf = open(path, "wb")
    pdf.write(response.content)
    pdf.close()

with open("exam_paths.json", "w") as file:
    json.dump(json_output, file, indent=4)
