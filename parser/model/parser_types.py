from typing import List
from pydantic import BaseModel

from parser.model.image_model import ImageModel


class ElementTypes(BaseModel):
    pdf_path: str
    # warren add instance of text model here
    # text:
    images: List[ImageModel] = []
    # tables: List[Table] = []

    class Config:
        # enable to allow fitz.Document and other non-standard types
        arbitrary_types_allowed = True

    # set up pdf init method in here as well
