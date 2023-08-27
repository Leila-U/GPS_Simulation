import csv
import arcpy
import random
import os
import datetime
import numpy

import globalvariables as gvar
from RouteTree import RouteTreeNode


class Person:
    def __init__(self):
        # Create activity space
        self.home = None
        self.work = None
        self.activity_space = None
        self.route_tree = None
        self.create_activity_space()

        # Choose route
        self.route = None
        self.tract_name = None
        self.probability = None
        self.find_route()

    def create_activity_space(self):
        """
        Creates points that include home, work, and specified amount of activity locations and RouteTreeNode for
        calculating the route
        :return: directory containing the activity space points and a RouteTreeNode containing all possible paths from
        home -> work -> activities ... -> home
        """
        # Activity space feature class variables
        spatial_reference = gvar.COORD_SYSTEM
        self.activity_space = os.path.join(gvar.HABITAT_DIR, gvar.HABITAT_NAME)
        fields = ["NAME", "SHAPE@XY"]

        # Create activity space feature class
        arcpy.management.CreateFeatureclass(gvar.HABITAT_DIR, gvar.HABITAT_NAME, "POINT")
        arcpy.management.AddField(self.activity_space, "NAME", "TEXT")
        arcpy.management.DefineProjection(self.activity_space, spatial_reference)

        # Create home point
        home_time_spent = numpy.random.normal(7, 2)
        home_start_time = datetime.datetime(2023, 6, 20, 0, 0, 0)
        home_end_time = home_start_time + datetime.timedelta(hours=home_time_spent)
        self.home = self.__create_rand_point__("home", gvar.HOME_ZONE_DIR)
        arcpy.da.InsertCursor(self.activity_space, fields).insertRow(self.home)
        home_rt = RouteTreeNode(self.home[0], self.home[1],
                                start_time=home_start_time,
                                end_time=home_end_time,
                                time_spent=home_time_spent)

        # Create work point
        work_time_spent = numpy.random.normal(6, 3)
        self.work = self.__create_rand_point__("work", gvar.WORK_ZONE_DIR)
        arcpy.da.InsertCursor(self.activity_space, fields).insertRow(self.work)
        work_rt = RouteTreeNode(self.work[0], self.work[1], time_spent=work_time_spent)

        # Choose activity locations and get approx. time spent at location
        activities = self.__choose_activity_location__()
        for activity in activities:
            arcpy.da.InsertCursor(self.activity_space, fields).insertRow(activity)
            activity_time_spent = self.__get_activity_time__(activity[0])
            activity_rt = RouteTreeNode(name=activity[0],
                                        xy_coord=activity[1],
                                        time_spent=activity_time_spent)
            work_rt.add_child(activity_rt)

        # add all possible routes the person can take that goes through every activity location
        work_rt.add_all_routes(home_rt)
        home_rt.add_child(work_rt)
        print("Route Tree:\n{0}".format(home_rt))
        self.route_tree = home_rt

    def find_route(self):
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
    def __create_rand_point__(point_type: str, zone):
        """
        Creates random points in a certain zone for home, work, and activities
        :param point_type: (String) contains a short description of the type of location (e.g., HOME, WORK, ACTIVITY)
        :param zone: (Vector) the boundary the points will be contained in
        :return: point_type, a single point or a list of points with random x, y coordinates
        """
        points_dir = os.path.join(gvar.SCRATCH_DIR, point_type)

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

        arcpy.management.Delete(points_dir)
        return random_points

    def __choose_activity_location__(self):
        """
        Get random activity locations using the distance as an estimated probability (using inverse square)
        :return: a list of the activity locations
        """
        # return value will contain tuples (point(x,y), location category)
        final_activity_locations = []

        # choose a random distance using weights of inverse square (1/x**2)
        buffer_distances = random.choices(gvar.ACTIVITY_BUFFER_DISTANCE,
                                          weights=[1/(d**2)for d in gvar.ACTIVITY_BUFFER_DISTANCE],
                                          k=gvar.NUM_ACTIVITIES)
        buffer_distances = gvar.list_to_dictionary(buffer_distances)

        print(buffer_distances)
        # loop through the chosen distances
        for distance in buffer_distances.keys():
            # create buffer
            buffer = os.path.join(gvar.SCRATCH_DIR, "buffer_{0}".format(distance))
            arcpy.analysis.Buffer(self.activity_space, buffer, "{0} Kilometers".format(str(distance)))

            # exclude inner distance
            if distance != 1:
                excl_buffer = os.path.join(gvar.SCRATCH_DIR, "excl_buffer")
                excl_distance = gvar.ACTIVITY_BUFFER_DISTANCE[gvar.ACTIVITY_BUFFER_DISTANCE.index(distance) - 1]
                arcpy.analysis.Buffer(self.activity_space, excl_buffer, "{0} Kilometers".format(str(excl_distance)))
                arcpy.analysis.Erase(buffer, excl_buffer, "{0}_erased".format(buffer))
                arcpy.management.Delete(buffer)
                arcpy.management.Delete(excl_buffer)
                arcpy.management.Rename("{0}_erased".format(buffer), buffer)

            # select all point of interests within the area
            locations = arcpy.management.SelectLayerByLocation(gvar.POI_POINTS_DIR,
                                                               overlap_type="INTERSECT",
                                                               select_features=buffer)
            arcpy.management.Delete(buffer)

            # get a random poi for every location that was determined to be within the buffer
            for _ in range(buffer_distances[distance]):
                random_index = random.randrange(0, int(arcpy.management.GetCount(locations)[0]))
                row_num = 0
                with arcpy.da.SearchCursor(locations, ["SHAPE@XY", "top_catego"]) as cursor:
                    for row in cursor:
                        if row_num == random_index:
                            x, y = float(row[0][0]), float(row[0][1])
                            location_type = row[1]
                            final_activity_locations.append((location_type, arcpy.Point(x, y)))
                            print("{0} {1} {2}".format(x, y, location_type))
                        row_num += 1

        return final_activity_locations

    @staticmethod
    def __get_activity_time__(activity_type):
        """
        Read the activity hours csv and finds the average time spent at the activity type then apply a normal
        distribution probability.
        :param activity_type: the activity type to get the average time for
        :return: the time spent at the location
        """
        with open(gvar.ACTIVITY_HOURS_DIR, "r") as file:
            csv_reader = csv.reader(file, delimiter=";")
            for row in csv_reader:
                if activity_type == row[0]:
                    hours_stayed = numpy.random.normal(float(row[1]), float(row[1]) * 0.9)
                    return hours_stayed
        raise Exception("No activity {0} found in activity_hours.csv".format(activity_type))


if __name__ == "__main__":
    person = Person()


