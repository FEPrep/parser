# Handles making and storing pdfs for each FE question in MinIO file storage bucket

import pymupdf
import io
import os
import sys
from dotenv import load_dotenv
from minio import Minio
from parser.dataset.exam import Exam


class Bucket:
    client: Minio
    bucket_name: str = "fe-pdfs"

    def __init__(self):
        # Configure connection to MinIO client
        load_dotenv()
        self.client = Minio(
            os.getenv("MINIO_ENDPOINT"),
            access_key=os.getenv("MINIO_ACCESS_KEY"),
            secret_key=os.getenv("MINIO_SECRET_KEY"),
        )

        if not self.client.bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)

    # Creates and stores Minio objects containing exam questions
    def create_exam_objs(self, exam: Exam):
        document = pymupdf.open(exam.exam_path)

        assert exam.sections
        for section in exam.sections:
            assert section.questions
            for question in section.questions:
                # Create a new empty PDF named with a unique ID
                pdf_dir = f"{exam.semester}-{exam.year}"
                question_pdf_name = f"{pdf_dir}/{question.id}.pdf"
                question_pdf = pymupdf.open()

                for page in question.pages:
                    # Add question content from document page to the new document
                    rect = document[page].rect
                    question_pdf_page = question_pdf.new_page(
                        width=rect.width, height=rect.height
                    )
                    question_pdf_page.show_pdf_page(rect, document, page)

                pdf_bytes = question_pdf.write()
                pdf_stream = io.BytesIO(pdf_bytes)

                try:
                    # Add the file to the bucket
                    self.client.put_object(
                        bucket_name=self.bucket_name,
                        object_name=question_pdf_name,
                        data=pdf_stream,
                        length=len(pdf_bytes),
                        content_type="application/pdf",
                    )
                except Exception as e:
                    print(f"An error occurred: {e}", file=sys.stderr)
                    import traceback

                    traceback.print_exc()
                    sys.exit(1)
