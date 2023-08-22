import arcpy
import random
import os
import datetime
import googlemaps
import arcgis.geocoding

from pprint import pprint
from activity_hours import activity_hours
from arcgis.gis import GIS

import numpy as np


import globalvariables as gvar
import localvariables as lvar
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

        home_time_spent = np.random.normal(7, 2)
        home_start_time = datetime.datetime(2023, 6, 20, 0, 0, 0)
        home_end_time = home_start_time + datetime.timedelta(hours=home_time_spent)
        self.home = self.create_rand_point("home", gvar.HOME_ZONE_DIR)
        arcpy.da.InsertCursor(output_dir, fields).insertRow(self.home)
        home_rt = RouteTreeNode(self.home[0], self.home[1],
                                start_time=home_start_time,
                                end_time=home_end_time,
                                time_spent=home_time_spent)

        work_time_spent = np.random.normal(8, 4)
        self.work = self.create_rand_point("work", gvar.WORK_ZONE_DIR)
        arcpy.da.InsertCursor(output_dir, fields).insertRow(self.work)
        work_rt = RouteTreeNode(self.work[0], self.work[1], time_spent=work_time_spent)

        activities = self.__get_activity_locations__()
        for activity in activities:
            arcpy.da.InsertCursor(output_dir, fields).insertRow(("activity", activity.get("point")))
            activity_rt = RouteTreeNode(name="activity",
                                        xy_coord=activity.get("point"),
                                        time_spent=activity.get("hours_stayed"))
            work_rt.add_child(activity_rt)

        work_rt.add_all_routes(home_rt)
        home_rt.add_child(work_rt)
        print("Route Tree:\n{0}".format(home_rt))

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
        self.route = final_route.route

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

    def __get_activity_locations__(self):
        """
        Give the time stayed at the location using arcgis and google maps queries (for establishment details)
        and cross-referencing to a dictionary based on statistics data.
        :return: hours stayed at location
        """
        GIS(profile="your_online_profile")
        # turn work into an address
        location = {"x": self.work[1].X, "y": self.work[1].Y, "spatialReference": {"wkid": 32617}}
        location_query = arcgis.geocoding.reverse_geocode(location)
        pprint(location_query)
        work_lat_long = (location_query.get("location").get("y"), location_query.get("location").get("x"))
        print("Work Establishment: {0}".format(work_lat_long))

        # google maps client
        map_client = googlemaps.Client(lvar.API_KEY)

        # grab all businesses in area
        activity_list = []
        business_list = []
        nearby_search_query = map_client.places_nearby(
            location=work_lat_long,
            radius=5000
        )
        business_list.extend(nearby_search_query.get('results'))

        if nearby_search_query.get("status") == "OK":
            for i in range(1, gvar.NUM_ACTIVITIES + 1):
                # get lat and long
                activity_address = business_list[i].get("vicinity")
                activity_geocode = arcgis.geocoding.geocode(activity_address, out_sr=32617)[0]["location"]
                activity_point = arcpy.Point(activity_geocode.get("x"), activity_geocode.get("y"))

                # get hours
                activity_type = business_list[i].get("types")[0]
                hours_stayed = activity_hours.get(activity_type)
                curved_hours_stayed = np.random.normal(hours_stayed, hours_stayed / 2)
                print("Activity Point: {0} | Hours Stayed: {1}".format(activity_point, curved_hours_stayed))

                activity_list.append({"point": activity_point, "hours_stayed": curved_hours_stayed})
        else:
            raise Exception("No establishments around the area")

        return activity_list


if __name__ == "__main__":
    person = Person()
    # work_rt = RouteTreeNode("home",
    #                         arcpy.Point(636817.150044013, 4836472.92922353),
    #                         datetime.datetime(23, 6, 20, 0, 0, 0),
    #                         datetime.datetime(23, 6, 20, 8, 0, 0))
    #
    # home_rt.__determine_time_at_location__()

