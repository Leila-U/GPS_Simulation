import arcpy
import random
import os
import datetime

import globalvariables as gvar
from RouteTree import RouteTreeNode


class Person:
    def __init__(self):
        # Create activity space
        self.home = None
        self.work = None
        self.activity_space = None
        self.route_tree = None
        self.__create_activity_space__()

        # Choose route
        self.route = None

        # taken from census data
        self.tract_name = None
        self.probability = None
        self.__find_route__()

    def __create_activity_space__(self):
        """
        Creates points that include home, work, and specified amount of activity locations and RouteTreeNode for
        calculating the route
        :return: directory containing the activity space points and a RouteTreeNode containing all possible paths from
        home -> work -> activities ... -> home
        """
        spatial_reference = gvar.COORD_SYSTEM
        output_dir = os.path.join(gvar.HABITAT_DIR, gvar.HABITAT_NAME)
        fields = ["NAME", "SHAPE@XY"]

        arcpy.management.CreateFeatureclass(gvar.HABITAT_DIR, gvar.HABITAT_NAME, "POINT")
        arcpy.management.AddField(output_dir, "NAME", "TEXT")
        arcpy.management.DefineProjection(output_dir, spatial_reference)

        self.home = self.create_rand_point("home", gvar.HOME_ZONE_DIR)
        arcpy.da.InsertCursor(output_dir, fields).insertRow(self.home)
        home_rt = RouteTreeNode(self.home[0], self.home[1],
                                datetime.datetime(2023, 6, 20, 0, 0, 0), datetime.datetime(2023, 6, 20, 8, 0, 0))

        self.work = self.create_rand_point("work", gvar.WORK_ZONE_DIR)
        arcpy.da.InsertCursor(output_dir, fields).insertRow(self.work)
        work_rt = RouteTreeNode(self.work[0], self.work[1])

        line_dir = gvar.SCRATCH_DIR + r"\Habitat_Line"
        buffer_dir = gvar.SCRATCH_DIR + r"\Habitat_Buffer"
        arcpy.management.PointsToLine(output_dir + ".shp", line_dir)
        arcpy.analysis.Buffer(line_dir, buffer_dir, str(gvar.DATA_EXTENT) + " Meters")

        activities = self.create_rand_point("activity", buffer_dir)

        for activity in activities:
            arcpy.da.InsertCursor(output_dir, fields).insertRow(activity)
            activity_rt = RouteTreeNode(activity[0], activity[1])
            work_rt.add_child(activity_rt)

        work_rt.add_all_routes(home_rt)
        home_rt.add_child(work_rt)

        arcpy.management.Delete(line_dir)
        arcpy.management.Delete(buffer_dir)

        self.activity_space = output_dir
        self.route_tree = home_rt


    def __find_route__(self):
        """
        Requires there to be at least home and work nodes
        Assigns high probability to routes with a more optimal time
        :return: route that returns back home
        """
        leaf_nodes = []
        self.route_tree.calculate_all_routes(leaf_nodes)

        leaf_nodes.sort(key=lambda x: x.start_time)

        final_route = leaf_nodes[0]
        for i in range(len(leaf_nodes)):
            if i == len(leaf_nodes) - 1 or i == random.randint(0, i + 1):
                final_route = leaf_nodes[i]
                print(i)
                break

        final_route.route.saveACopy(os.path.join(gvar.ROUTES_DIR, gvar.FINAL_ROUTE_NAME))
        return final_route.route


    @staticmethod
    def create_rand_point(point_type: str, zone):
        """
        Creates random points in a certain zone for home, work, and activities
        :param point_type: (String) contains a short description of the type of location (e.g., HOME, WORK, ACTIVITY)
        :param zone: (Vector) the boundary the points will be contained in
        :return: point_type, a single point or a list of points with random x, y coordinates
        """
        points_dir = os.path.join(gvar.SCRATCH_DIR, point_type)

        if point_type == "home" or point_type == "work":
            arcpy.management.FeatureToPoint(zone, points_dir, "CENTROID")
            random_index = random.randrange(0, int(arcpy.management.GetCount(points_dir)[0]))
            row_num = 0
            with arcpy.da.UpdateCursor(points_dir, ["SHAPE@XY"]) as cursor:
                for row in cursor:
                    if row_num == random_index:
                        x, y = float(row[0][0]), float(row[0][1])
                        arcpy.management.Delete(points_dir)
                        random_points = (point_type, arcpy.Point(x, y))
                    row_num += 1
        else:
            arcpy.management.CreateRandomPoints(gvar.SCRATCH_DIR, point_type, zone, "", gvar.NUM_ACTIVITIES, "",
                                                "POINT")
            with arcpy.da.UpdateCursor(points_dir, ["SHAPE@XY"]) as cursor:
                random_points = []
                for row in cursor:
                    x, y = float(row[0][0]), float(row[0][1])
                    random_points.append(("activity", arcpy.Point(x, y)))

        arcpy.management.Delete(points_dir)
        return random_points

