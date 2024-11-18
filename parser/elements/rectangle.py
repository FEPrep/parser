import math
from collections import defaultdict
from itertools import combinations

# Define a Rectangle class for clarity
from typing import Dict, List, Set, Tuple

import pymupdf
from pydantic import BaseModel


class Rectangle(BaseModel, strict=True):
    x0: float
    y0: float
    x1: float
    y1: float

    @classmethod
    def from_points(cls, x0: float, y0: float, x1: float, y1: float) -> "Rectangle":
        """
        Create a Rectangle instance from given corner points.

        Args:
            x0 (float): The x-coordinate of the first corner.
            y0 (float): The y-coordinate of the first corner.
            x1 (float): The x-coordinate of the opposite corner.
            y1 (float): The y-coordinate of the opposite corner.

        Returns:
            Rectangle: A new Rectangle instance.
        """
        return cls(x0=x0, y0=y0, x1=x1, y1=y1)

    @classmethod
    def from_pymupdf(cls, rect: pymupdf.Rect) -> "Rectangle":
        """
        Create a Rectangle instance from a pymupdf.Rect object.

        Args:
            rect (pymupdf.Rect): A rectangle object from pymupdf.

        Returns:
            Rectangle: A new Rectangle instance.
        """
        return cls(x0=rect.x0, y0=rect.y0, x1=rect.x1, y1=rect.y1)

    def __repr__(self) -> str:
        """
        Return a string representation of the Rectangle.

        Returns:
            str: A string representation of the Rectangle.
        """
        return f"Rectangle(({self.x0}, {self.y0}), ({self.x1}, {self.y1}))"

    def area(self) -> float:
        """
        Calculate the area of the Rectangle.

        Returns:
            float: The area of the Rectangle.
        """
        return abs((self.x1 - self.x0) * (self.y1 - self.y0))

    def min_distance_to(self, other: "Rectangle") -> float:
        """
        Calculate the minimum distance between self and another rectangle.
        If they overlap, the distance is zero.

        Args:
            other (Rectangle): Another rectangle to calculate the distance to.

        Returns:
            float: The minimum distance between the two rectangles.
        """
        dx = max(max(self.x0, other.x0) - min(self.x1, other.x1), 0)
        dy = max(max(self.y0, other.y0) - min(self.y1, other.y1), 0)
        return math.hypot(dx, dy)

    def merge_with(self, other: "Rectangle") -> "Rectangle":
        """
        Merge self with another rectangle, returning a new Rectangle.

        Args:
            other (Rectangle): Another rectangle to merge with.

        Returns:
            Rectangle: A new Rectangle that is the union of the two rectangles.
        """
        new_x0 = min(self.x0, other.x0)
        new_y0 = min(self.y0, other.y0)
        new_x1 = max(self.x1, other.x1)
        new_y1 = max(self.y1, other.y1)
        return Rectangle(x0=new_x0, y0=new_y0, x1=new_x1, y1=new_y1)

    def is_within(self, other: "Rectangle") -> bool:
        """
        Check if the current rectangle is completely within another rectangle.

        Args:
            other (Rectangle): Another rectangle to check against.

        Returns:
            bool: True if the current rectangle is within the other rectangle, False otherwise.
        """
        return (
            self.x0 >= other.x0
            and self.y0 >= other.y0
            and self.x1 <= other.x1
            and self.y1 <= other.y1
        )

    def as_tuple(self) -> Tuple[float, float, float, float]:
        """
        Return the rectangle as a tuple of its corner points.

        Returns:
            tuple: A tuple containing the coordinates of the rectangle's corners.
        """
        return (self.x0, self.y0, self.x1, self.y1)


def build_connectivity_graph(
    rect_indices: Dict[int, Rectangle], max_distance: float
) -> Dict[int, List[int]]:
    """
    Build a graph where each node is a rectangle, and an edge exists between
    two rectangles if their minimum distance is less than or equal to max_distance.

    Args:
        rect_indices (Dict[int, Rectangle]): A dictionary mapping indices to Rectangle objects.
        max_distance (float): The maximum distance to consider two rectangles connected.

    Returns:
        Dict[int, List[int]]: A graph represented as an adjacency list.
    """
    graph: Dict[int, List[int]] = defaultdict(list)
    for (i1, rect1), (i2, rect2) in combinations(rect_indices.items(), 2):
        distance = rect1.min_distance_to(rect2)
        if distance > max_distance:
            raise RuntimeError(
                f"Distance between rectangles {i1} and {i2} exceeds max_distance: {distance}"
            )
        if distance <= max_distance:
            graph[i1].append(i2)
            graph[i2].append(i1)
    return graph


def find_connected_components(
    graph: Dict[int, List[int]], rect_indices: Dict[int, Rectangle]
) -> List[List[int]]:
    """
    Find connected components in the graph using DFS.
    Returns a list of components, where each component is a list of rectangle indices.

    Args:
        graph (Dict[int, List[int]]): A graph represented as an adjacency list.
        rect_indices (Dict[int, Rectangle]): A dictionary mapping indices to Rectangle objects.

    Returns:
        List[List[int]]: A list of connected components, each being a list of rectangle indices.
    """

    def dfs(node: int, visited: Set[int], component: List[int]):
        """
        Depth-first search to explore the graph and find connected components.

        Args:
            node (int): The current node being visited.
            visited (Set[int]): A set of visited nodes.
            component (List[int]): The current component being built.
        """
        visited.add(node)
        component.append(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                dfs(neighbor, visited, component)

    visited: Set[int] = set()
    components: List[List[int]] = []

    for node in rect_indices:
        if node not in visited:
            component: List[int] = []
            dfs(node, visited, component)
            components.append(component)
    return components


def merge_rectangles(
    rectangles: List[Rectangle], max_distance: float = 2000000
) -> Rectangle:
    # Assign an index to each rectangle for easy reference
    rect_indices = {i: rect for i, rect in enumerate(rectangles)}

    # Step 1: Build the connectivity graph using the function
    graph = build_connectivity_graph(rect_indices, max_distance)

    # Step 2: Find connected components using the function
    components = find_connected_components(graph, rect_indices)

    # Step 3: Merge rectangles in each connected component
    merged_rectangles: List[Rectangle] = []

    for component in components:
        merged_rect = rect_indices[component[0]]

        for idx in component[1:]:
            merged_rect = merged_rect.merge_with(rect_indices[idx])

        merged_rectangles.append(merged_rect)

    # Step 4: Select the largest rectangle
    largest_rectangle: Rectangle = max(merged_rectangles, key=lambda r: r.area())

    return largest_rectangle
