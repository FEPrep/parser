from collections import defaultdict
from itertools import combinations
from typing import Dict, List

import pymupdf
from pydantic import BaseModel

from parser.elements.rectangle import Rectangle


class Drawing(BaseModel, strict=True):
    """
    Represents a drawing object with a rectangle and associated indices.

    Attributes:
        rect (Rectangle): The rectangle representing the drawing.
        indices (List[int]): List of indices associated with the drawing.
    """

    rect: Rectangle
    indices: List[int]


def get_merged_drawings_from_page(page: pymupdf.Page) -> List[Drawing]:
    """
    Extracts and merges drawing objects from a given page.

    Args:
        page (pymupdf.Page): The page from which to extract drawings.

    Returns:
        List[Drawing]: A list of merged drawing objects.
    """
    drawings = page.get_drawings()
    page_width = page.rect.width
    page_height = page.rect.height

    drawing_objects = []
    for drawing_index, drawing_dict in enumerate(drawings):
        # Convert pymupdf.Rect to Rectangle
        drawing_dict["rect"] = Rectangle.from_pymupdf(drawing_dict["rect"])
        # Convert items' rectangles to Rectangle
        drawing_dict["items"] = [
            (item[0], Rectangle.from_pymupdf(item[1]), item[2])
            for item in drawing_dict.get("items", [])
        ]
        # Store the index of the drawing
        drawing_dict["indices"] = [drawing_index]

        drawing = Drawing(**drawing_dict)
        # Skip drawings that are page boundaries
        if is_page_boundary(drawing.rect, page_width, page_height):
            print(f"Skipping page boundary drawing: {drawing.rect}")
            continue

        drawing_objects.append(drawing)

    # Merge the drawing objects
    merged_drawings: List[Drawing] = merge_drawings(drawing_objects)

    return merged_drawings


def is_page_boundary(
    rect: Rectangle, page_width: float, page_height: float, tolerance: float = 1.0
) -> bool:
    """
    Determines if a rectangle is the page boundary based on its dimensions.

    Args:
        rect (Rectangle): The rectangle to check.
        page_width (float): The width of the page.
        page_height (float): The height of the page.
        tolerance (float): Allowable deviation in dimensions.

    Returns:
        bool: True if the rectangle is the page boundary, False otherwise.
    """
    width_match = abs(rect.x1 - rect.x0 - page_width) <= tolerance
    height_match = abs(rect.y1 - rect.y0 - page_height) <= tolerance
    return width_match and height_match


def build_connectivity_graph(
    rect_indices: Dict[int, Rectangle], max_distance: float
) -> Dict[int, List[int]]:
    """
    Builds a connectivity graph based on the proximity of rectangles.

    Args:
        rect_indices (Dict[int, Rectangle]): A dictionary mapping indices to rectangles.
        max_distance (float): The maximum distance to consider two rectangles connected.

    Returns:
        Dict[int, List[int]]: A graph represented as an adjacency list.
    """
    graph = defaultdict(list)
    for (i1, rect1), (i2, rect2) in combinations(rect_indices.items(), 2):
        # Calculate the minimum distance between two rectangles
        distance = rect1.min_distance_to(rect2)
        # If the distance is within the max_distance, connect the nodes
        if distance <= max_distance:
            graph[i1].append(i2)
            graph[i2].append(i1)
    return graph


def find_connected_components(
    graph: Dict[int, List[int]], rect_indices: Dict[int, Rectangle]
) -> List[List[int]]:
    """
    Finds connected components in a graph using depth-first search.

    Args:
        graph (Dict[int, List[int]]): The graph represented as an adjacency list.
        rect_indices (Dict[int, Rectangle]): A dictionary mapping indices to rectangles.

    Returns:
        List[List[int]]: A list of connected components, each represented as a list of indices.
    """

    def dfs(node: int, visited: set, component: List[int]):
        stack = [node]
        while stack:
            current = stack.pop()
            if current not in visited:
                visited.add(current)
                component.append(current)
                stack.extend(graph[current])

    visited: set[int] = set()
    components: List[List[int]] = []

    for node in rect_indices:
        if node not in visited:
            component: List[int] = []
            dfs(node, visited, component)
            components.append(component)
    return components


def merge_drawings(
    drawings: List[Drawing], max_distance: float = 10.0
) -> List[Drawing]:
    """
    Merges drawings that are close to each other into single drawings.

    Args:
        drawings (List[Drawing]): A list of drawing objects to merge.
        max_distance (float): The maximum distance to consider two drawings for merging.

    Returns:
        List[Drawing]: A list of merged drawing objects.
    """
    # Create a dictionary of rectangle indices
    rect_indices = {i: drawing.rect for i, drawing in enumerate(drawings)}
    # Build a connectivity graph based on the max_distance
    graph = build_connectivity_graph(rect_indices, max_distance)
    # Find connected components in the graph
    components = find_connected_components(graph, rect_indices)

    merged_drawings: List[Drawing] = []

    for component in components:
        # Start with the first rectangle in the component
        merged_rect = rect_indices[component[0]]
        # Merge all rectangles in the component
        for idx in component[1:]:
            merged_rect = merged_rect.merge_with(rect_indices[idx])

        # Create a new Drawing with the merged rectangle and component indices
        merged_drawings.append(Drawing(rect=merged_rect, indices=component))

    return merged_drawings
