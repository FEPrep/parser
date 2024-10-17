import os
from typing import List

from parser.dataset.exam import Exam
from parser.model import Semester


class DataLoader:
    exams: List[Exam]
    loaded: bool

    def __init__(self, data_dir: str, solutions_dir: str):
        self.exam_dir = data_dir
        self.solutions_dir = solutions_dir
        self.loaded = False

    def load_data(self):
        self.exams = []
        for filename in os.listdir(self.exam_dir):
            if filename.endswith(".pdf"):
                exam_path = os.path.join(self.exam_dir, filename)
                # solutions_path = os.path.join(
                #    self.solutions_dir, filename.replace(".pdf", "_solutions.pdf")
                # )
                exam = Exam(exam_path, None)
                exam.load_data()
                output_file = (
                    os.path.dirname(exam_path)
                    + "/"
                    + os.path.basename(exam_path).removesuffix(".pdf")
                    + "_extracted.json"
                )
                exam.write(output_file)
                self.exams.append(exam)
        self.loaded = True
        pass

    def get_exam(self, semester: Semester, year: int) -> Exam | None:
        for exam in self.exams:
            if exam.semester == semester and exam.year == year:
                return exam
        return None
