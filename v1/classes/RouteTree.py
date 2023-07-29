import arcpy
import random

import globalvariables as gvar


class RouteTreeNode:
    """
    name: Str = the activity location description (e.g., home, work)
    xy_coord: Point = the activity location coordinates
    children: RouteTreeNode = the next points to visit
    ---
    route: Vector = the route sublayer from NA that contains the connection between the previous node to self
    start_time: Datetime = the time when the person arrives at the location
    end_time: Datetime = the time when the person leaves the location
    """

    def __init__(self, name, xy_coord):
        self.name = name
        self.xy_coord = xy_coord
        self.children = []

        # time values
        self.start_time = None
        self.end_time = None

        # route values
        self.route = None

    def __str__(self, depth=0):
        tree_str = "{0}{1} ({2}) \n".format("\t" * depth, self.name, self.xy_coord)
        for child in self.children:
            tree_str += child.__str__(depth + 1)
        return tree_str

    """GET methods"""
    def get_name(self):
        return self.name

    def get_xy(self):
        return self.xy_coord

    def get_children(self):
        return self.children

    def get_route(self):
        return self.route

    """SET methods"""
    def add_child(self, child_node):
        self.children.append(child_node)

    """ROUTING SETUP methods"""
    def add_all_routes(self, home_node):
        if not self.children:
            self.add_child(RouteTreeNode(home_node.get_name(), home_node.get_xy()))
        else:
            for child in self.children:
                for sibling in self.children:
                    if child != sibling:
                        child.add_child(RouteTreeNode(sibling.get_name(), sibling.get_xy()))
                child.add_all_routes(home_node)
