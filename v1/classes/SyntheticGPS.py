import arcpy
import random
import os

import globalvariables as gvar
from RouteTree import RouteTreeNode


class SyntheticGPS:
    def __init__(self):
        """
         activity_space = a directory to points that contain HOME, WORK, and ACTIVITY
         route = a directory to a vector containing the route connecting all points in the activity_space
         synthetic_points = a directory to the synthetic GPS data created from the route
         """
        self.activity_space = self.__create_activity_space__()
        self.route_tree = None
        self.synthetic_points = None

    def __create_activity_space__(self):
        spatial_reference = arcpy.SpatialReference(gvar.COORD_SYSTEM)
        output_dir = os.path.join(gvar.HABITAT_DIR, gvar.HABITAT_NAME)
        fields = ["NAME", "SHAPE@XY"]

        arcpy.CreateFeatureclass_management(gvar.HABITAT_DIR, gvar.HABITAT_NAME, "POINT")
        arcpy.AddField_management(output_dir, "NAME", "TEXT")
        arcpy.DefineProjection_management(output_dir, spatial_reference)

        home = self.create_rand_point("home", gvar.HOME_ZONE_DIR)
        arcpy.da.InsertCursor(output_dir, fields).insertRow(home)
        home_rt = RouteTreeNode(home[0], home[1])

        work = self.create_rand_point("work", gvar.WORK_ZONE_DIR)
        arcpy.da.InsertCursor(output_dir, fields).insertRow(work)
        work_rt = RouteTreeNode(work[0], work[1])

        line_dir = gvar.SCRATCH_DIR + r"\Habitat_Line"
        buffer_dir = gvar.SCRATCH_DIR + r"\Habitat_Buffer"
        arcpy.PointsToLine_management(output_dir + ".shp", line_dir)
        arcpy.Buffer_analysis(line_dir, buffer_dir, str(gvar.DATA_EXTENT) + " Meters")

        activities = self.create_rand_point("activity", buffer_dir)

        for activity in activities:
            arcpy.da.InsertCursor(output_dir, fields).insertRow(activity)
            activity_rt = RouteTreeNode(activity[0], activity[1])
            work_rt.add_child(activity_rt)

        work_rt.add_all_routes(home_rt)
        home_rt.add_child(work_rt)
        print(home_rt)

        arcpy.Delete_management(line_dir)
        arcpy.Delete_management(buffer_dir)

        return output_dir

    @staticmethod
    def create_rand_point(point_type: str, zone) -> tuple:
        points_dir = os.path.join(gvar.SCRATCH_DIR, point_type)

        if point_type == "home" or point_type == "work":
            arcpy.FeatureToPoint_management(zone, points_dir, "CENTROID")
            random_index = random.randrange(0, int(arcpy.GetCount_management(points_dir)[0]))
            row_num = 0
            with arcpy.da.UpdateCursor(points_dir, ["SHAPE@XY"]) as cursor:
                for row in cursor:
                    if row_num == random_index:
                        x, y = float(row[0][0]), float(row[0][1])
                        arcpy.Delete_management(points_dir)
                        random_points = (point_type, arcpy.Point(x, y))
                    row_num += 1
        else:
            arcpy.CreateRandomPoints_management(gvar.SCRATCH_DIR, point_type, zone, "", gvar.NUM_ACTIVITIES, "",
                                                "POINT")
            with arcpy.da.UpdateCursor(points_dir, ["SHAPE@XY"]) as cursor:
                random_points = []
                for row in cursor:
                    x, y = float(row[0][0]), float(row[0][1])
                    random_points.append(("activity", arcpy.Point(x, y)))

        arcpy.Delete_management(points_dir)
        return random_points

if __name__ == "__main__":
    test = SyntheticGPS()
