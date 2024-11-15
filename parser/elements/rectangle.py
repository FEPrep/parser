import math
from collections import defaultdict
from itertools import combinations

import pymupdf
from pydantic import BaseModel


# Define a Rectangle class for clarity
class Rectangle(BaseModel, strict=True):
    x0: float
    y0: float
    x1: float
    y1: float

    @classmethod
    def from_points(cls, x0, y0, x1, y1):
        return cls(x0=x0, y0=y0, x1=x1, y1=y1)

    @classmethod
    def from_pymupdf(cls, rect: pymupdf.Rect):
        return cls(x0=rect.x0, y0=rect.y0, x1=rect.x1, y1=rect.y1)

    def __repr__(self):
        return f"Rectangle(({self.x0}, {self.y0}), ({self.x1}, {self.y1}))"

    def area(self):
        return abs((self.x1 - self.x0) * (self.y1 - self.y0))

    def min_distance_to(self, other):
        """
        Calculate the minimum distance between self and other rectangle.
        If they overlap, the distance is zero.
        """
        dx = max(max(self.x0, other.x0) - min(self.x1, other.x1), 0)
        dy = max(max(self.y0, other.y0) - min(self.y1, other.y1), 0)
        return math.hypot(dx, dy)

    def merge_with(self, other):
        """
        Merge self with another rectangle, returning a new Rectangle.
        """
        new_x0 = min(self.x0, other.x0)
        new_y0 = min(self.y0, other.y0)
        new_x1 = max(self.x1, other.x1)
        new_y1 = max(self.y1, other.y1)
        return Rectangle(x0=new_x0, y0=new_y0, x1=new_x1, y1=new_y1)

    def is_within(self, other):
        """
        Check if the current rectangle is completely within another rectangle.
        """
        return (
            self.x0 >= other.x0
            and self.y0 >= other.y0
            and self.x1 <= other.x1
            and self.y1 <= other.y1
        )

    def as_tuple(self):
        return (self.x0, self.y0, self.x1, self.y1)


def build_connectivity_graph(rect_indices, max_distance):
    """
    Build a graph where each node is a rectangle, and an edge exists between
    two rectangles if their minimum distance is less than or equal to max_distance.
    """
    graph = defaultdict(list)
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


def find_connected_components(graph, rect_indices):
    """
    Find connected components in the graph using DFS.
    Returns a list of components, where each component is a list of rectangle indices.
    """

    def dfs(node, visited, component):
        visited.add(node)
        component.append(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                dfs(neighbor, visited, component)

    visited = set()
    components = []

    for node in rect_indices:
        if node not in visited:
            component = []
            dfs(node, visited, component)
            components.append(component)
    return components
