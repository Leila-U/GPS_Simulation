import arcpy
import random
import os
import datetime

import globalvariables as gvar
from RouteTree import RouteTreeNode


class SyntheticGPS:
    def __init__(self):
        """
         activity_space: (Points) HOME, WORK, and ACTIVITY
         route: (Vectors) the route connecting all points in the activity_space
         synthetic_points: (Points) synthetic GPS data created from the route
         """
        self.activity_space, self.route_tree = self.__create_activity_space__()
        self.route = self.find_optimal_route()
        self.synthetic_points = None
        print(self.route_tree)

    def __create_activity_space__(self):
        """
        Creates points that include home, work, and specified amount of activity locations and RouteTreeNode for
        calculating the route
        :return: directory containing the activity space points and a RouteTreeNode containing all possible paths from
        home -> work -> activities ... -> home
        """
        spatial_reference = arcpy.SpatialReference(gvar.COORD_SYSTEM)
        output_dir = os.path.join(gvar.HABITAT_DIR, gvar.HABITAT_NAME)
        fields = ["NAME", "SHAPE@XY"]

        arcpy.management.CreateFeatureclass(gvar.HABITAT_DIR, gvar.HABITAT_NAME, "POINT")
        arcpy.management.AddField(output_dir, "NAME", "TEXT")
        arcpy.management.DefineProjection(output_dir, spatial_reference)

        home = self.create_rand_point("home", gvar.HOME_ZONE_DIR)
        arcpy.da.InsertCursor(output_dir, fields).insertRow(home)
        home_rt = RouteTreeNode(home[0], home[1],
                                datetime.datetime(23, 6, 20, 0, 0, 0), datetime.datetime(23, 6, 20, 8, 0, 0))

        work = self.create_rand_point("work", gvar.WORK_ZONE_DIR)
        arcpy.da.InsertCursor(output_dir, fields).insertRow(work)
        work_rt = RouteTreeNode(work[0], work[1])

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

        return output_dir, home_rt

    def find_optimal_route(self):
        """
        Requires there to be at least home and work nodes
        Finds the route with the optimal time to travel through all home, work, and activities
        :return: route that returns back home at the earliest time
        """
        leaf_nodes = []
        self.route_tree.calculate_all_routes(leaf_nodes)

        shortest_route = leaf_nodes[0]
        for leaf in leaf_nodes[1:]:
            if leaf.end_time < shortest_route.end_time:
                shortest_route = leaf
        shortest_route.route.saveACopy(os.path.join(gvar.ROUTES_DIR, gvar.SHORTEST_ROUTE_NAME))
        return shortest_route.route


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


if __name__ == "__main__":
    test = SyntheticGPS()
