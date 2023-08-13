import arcpy
import random
import os
import datetime

import globalvariables as gvar
from RouteTree import RouteTreeNode
from Person import Person


class SyntheticGPS:
    def __init__(self):
        """
         activity_space: (Points) HOME, WORK, and ACTIVITY
         route: (Vectors) the route connecting all points in the activity_space
         synthetic_points: (Points) synthetic GPS data created from the route
         """
        self.person = Person()

    def route_to_points(self):
        with arcpy.da.UpdateCursor(self.person.route, ["SHAPE@XY", "StartTime", "EndTime", "Total_Length"]) as cursor:
            # TODO
            pass



if __name__ == "__main__":
    test = SyntheticGPS()
