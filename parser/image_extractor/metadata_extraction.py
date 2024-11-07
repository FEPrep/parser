from models import Image, Position


def extract_metadata(img_index, xref, page, image_ext, image_path) -> Image:
    bbox = page.get_image_bbox(xref)
    position = Position(
        x=int(bbox.x0),
        y=int(bbox.y0),
        width=int(bbox.width),
        height=int(bbox.height),
    )

    metadata = Image(
        src=image_path,
        position=position,
        resolution=f"{bbox.width}x{bbox.height}",
        z_index=1,
        reading_order=img_index + 1,
    )
    return metadata
