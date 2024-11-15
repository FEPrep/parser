# Handles making and storing pdfs for each FE question in MinIO file storage bucket

import pymupdf
import uuid
import io
import os
from dotenv import load_dotenv
from minio import Minio
from parser.dataset.exam import Exam


class Bucket:
    client: Minio | None = None
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

        for section in exam.sections:
            for question in section.questions:
                # Create a new empty PDF named with a unique ID
                unique_id = str(uuid.uuid4())
                question_pdf_name = f"{exam.semester}-{exam.year}/{unique_id}.pdf"
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
                    self.client.put_object(
                        bucket_name=self.bucket_name,
                        object_name=question_pdf_name,
                        data=pdf_stream,
                        length=len(pdf_bytes),
                        content_type="application/pdf",
                    )
                except Exception as e:
                    print(f"uh oh!\n{e}")
