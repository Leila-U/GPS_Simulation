import datetime
import arcpy
import random


class SyntheticGPS:
    def __init__(self):
        """
        activity_space = a directory to points that contain HOME, WORK, and ACTIVITY
        route = a directory to a vector containing the route connecting all points in the activity_space
        synthetic_points = a directory to the synthetic GPS data created from the route
        """
        self.activity_space = self.create_activity_space()
        self.route = self.create_route()
        self.synthetic_points = ""

    def create_activity_space(self):
        # directory where habitat points will be saved
        habitat_dir = arcpy.env.workspace + r"\habitatPoints"

        # create empty feature class to store home, work, and activity space points
        arcpy.CreateFeatureclass_management(arcpy.env.workspace, "habitatPoints", "POINT")
        arcpy.AddField_management(habitat_dir, "NAME", "TEXT")
        arcpy.AddField_management(habitat_dir, "NEAR_DIST", "LONG")

        # create a random HOME point using residential zones provided by user
        residential_zones = arcpy.GetParameter(0)
        home = self.create_rand_point(residential_zones, "HOME")
        arcpy.da.InsertCursor(habitat_dir, ["NAME", "NEAR_DIST", "SHAPE@XY"]).insertRow(home)

        # create a random WORK point using residential zones provided by user
        work_zones = arcpy.GetParameter(1)
        work = self.create_rand_point(work_zones, "WORK")
        arcpy.da.InsertCursor(habitat_dir, ["NAME", "NEAR_DIST", "SHAPE@XY"]).insertRow(work)

        # get parameters for ACTIVITY SPACE points
        activity_point_num = arcpy.GetParameter(2)
        buffer_size = arcpy.GetParameterAsText(3)

        # directory where buffer will be saved
        line_dir = arcpy.env.scratchGDB + r"\habitatLine"
        buffer_dir = arcpy.env.scratchGDB + r"\habitatBuffer"

        # create buffer using a line between all habitat points
        arcpy.PointsToLine_management(habitat_dir, line_dir)
        arcpy.Buffer_analysis(line_dir, buffer_dir, buffer_size + " Meters")

        # create a random ACTIVITY point using buffer
        for i in range(activity_point_num):
            activity = self.create_rand_point(buffer_dir, "ACTIVITY")
            arcpy.da.InsertCursor(habitat_dir, ["NAME", "NEAR_DIST", "SHAPE@XY"]).insertRow(activity)

        # cleanup temporary files
        arcpy.Delete_management(line_dir)
        arcpy.Delete_management(buffer_dir

        return habitat_dir

    def create_route(self):
        # check for extensions
        arcpy.CheckOutExtension("Network")

        # temporary place to store our start and end point for each route
        temp_stops_dir = arcpy.env.scratchGDB + r"\temp_stops"
        fields = ["SHAPE@XY"]
        counter = 0
        network = arcpy.GetParameter(4)

        with arcpy.da.UpdateCursor(self.activity_space, fields) as cursor:
            for row in cursor:
                # for the first row: add the first point as the start point
                # so for next iteration, the current row is end
                if counter == 0:
                    x, y = float(row[0][0]), float(row[0][1])
                    prev = [arcpy.Point(x, y)]
                    counter += 1

                    # start time is 8:00 July 20, 2023 - CAN BE EDITED LATER
                    start_time = datetime.datetime(23, 6, 20, 8, 0, 0)
                    time_zone = "LOCAL_TIME_AT_LOCATIONS"
                else:
                    # overwrite temp_stops after every iteration so that start and end are new
                    arcpy.CreateFeatureclass_management(arcpy.env.scratchGDB, "temp_stops", "POINT")

                    # insert our previous row which was declared last iteration
                    arcpy.da.InsertCursor(temp_stops_dir, fields).insertRow(prev)

                    # insert our current row
                    x, y = float(row[0][0]), float(row[0][1])
                    curr = [arcpy.Point(x, y)]
                    arcpy.da.InsertCursor(temp_stops_dir, fields).insertRow(curr)

                    # travel mode is determined by a function
                    travel_mode = self.determine_transportation()

                    # create route analysis layer from a network
                    route_analysis = arcpy.na.MakeRouteAnalysisLayer(network, travel_mode=travel_mode,
                                                                     sequence="USE_CURRENT_ORDER",
                                                                     time_of_day=start_time,
                                                                     time_zone=time_zone, line_shape="ALONG_NETWORK",
                                                                     generate_directions_on_solve="DIRECTIONS",
                                                                     time_zone_for_time_fields=time_zone,
                                                                     ignore_invalid_locations="SKIP").getOutput(0)

                    # create our fields
                    stops_layer_name = arcpy.na.GetNAClassNames(route_analysis)["Stops"]
                    field_mappings = arcpy.na.NAClassFieldMappings(route_analysis, stops_layer_name)
                    field_mappings["Name"].mappedFieldName = "NAME"

                    # add locations and solve
                    arcpy.na.AddLocations(route_analysis, stops_layer_name, temp_stops_dir, field_mappings,
                                          append="APPEND")
                    arcpy.na.Solve(route_analysis, "SKIP")

                    # grab our routes and stops sub layer
                    routes_sublayer = arcpy.na.GetNASublayer(route_analysis, "Routes")
                    stops_sublayer = arcpy.na.GetNASublayer(route_analysis, "Stops")

                    # save our end times for each route to calculate the start of the next
                    with arcpy.da.SearchCursor(routes_sublayer, ["EndTime"]) as routes:
                        for route in routes:
                            start_time = route[0]

                    # for the first route, create our accumulated route and stops feature classes
                    if counter == 1:
                        route_dir = arcpy.env.workspace + r"\NARoutes"
                        arcpy.CreateFeatureclass_management(arcpy.env.workspace, "NARoutes", "POLYLINE", routes_sublayer)
                        stops_dir = arcpy.env.workspace + r"\NAStops"
                        arcpy.CreateFeatureclass_management(arcpy.env.workspace, "NAStops", "POINT", stops_sublayer)

                    # append routes and stops into feature class
                    arcpy.management.Append(routes_sublayer, route_dir)
                    arcpy.management.Append(stops_sublayer, stops_dir)

                    # set our current end point as the start point for the next iteration
                    prev = curr
                    counter += 1

        return routes_sublayer

    def create_synthetic_points(self):
        # TODO
        pass

    def determine_order_route(self):
        # TODO
        pass

    @staticmethod
    def determine_transportation():
        # TODO
        return "Public transit time"

    @staticmethod
    def create_rand_point(zone, point_type: str) -> tuple:
        points_dir = arcpy.env.scratchGDB + r"\allPoints"
        fields = ["SHAPE@XY"]

        if point_type == "HOME" or point_type == "WORK":
            # turning the zone (shape) to points
            arcpy.FeatureToPoint_management(zone, points_dir, "CENTROID")

            # uses a random index to return a random point from all the points
            random_index = random.randrange(0, int(arcpy.GetCount_management(points_dir)[0]))

            # find point with random object id and return as tuple
            row_num = 0
            with arcpy.da.UpdateCursor(points_dir, fields) as cursor:
                for _ in cursor:
                    if row_num == random_index:
                        break
                    row_num += 1
        else:
            # create random activity points within buffer
            arcpy.CreateRandomPoints_management(arcpy.env.scratchGDB, "allPoints", zone, "", 1, "", "POINT")
            cursor = arcpy.da.UpdateCursor(points_dir, fields)

        for row in cursor:
            x, y = float(row[0][0]), float(row[0][1])
            arcpy.Delete_management(points_dir)
            return point_type, 100, arcpy.Point(x, y)


if __name__ == "__main__":
    test = SyntheticGPS()
