import arcpy
import csv
import datetime
import numpy
import os
import random

import globalvariables as gvar
from Classes.RouteTree import RouteTreeNode


class Person:
    """
    A working person (ages:25-50) with an activity space that will contain a route throughout the day.
    ...
    Attributes
    __________
    home : Point
        location of their home
    work : Point
        location of their work
    activity_space : FeatureClass
        contains all the locations of the home, work, and activities
    route_tree : RouteTreeNode
        contains all possible paths that the person will take during the day to hit every activity
    route : Layer
        the final route chosen from all possible routes
    ...
    Methods
    _______
    create_activity_space
        creates points that include home, work, and specified amount of activity locations and route tree
    find_route
        finds the final route for the person through the day
    *create_rand_point
        creates random points in a certain zone
    *choose_activity_location
        get random activity locations using the distance as an estimated probability (using inverse square)
    *get_activity_time
        use activity hours csv to find the average time spent at the activity type then apply normal distribution
    *convert_route_to_shapefile
        convert route layer file to a shapefile and sorts by start datetime
    """

    def __init__(self):
        # create activity space
        self.home = None
        self.work = None
        self.activity_space = None
        self.route_tree = None
        self.create_activity_space()

        # choose route
        self.route = None
        self.find_route()

    def create_activity_space(self):
        """ Creates points that include home, work, and specified amount of activity locations and route tree.
        Route tree contains all possible paths from home -> work -> activity -> ... -> home.
        :return: None
        """
        print("\n-------")
        print("CREATING PERSON...")

        # activity space feature class variables
        spatial_reference = gvar.COORD_SYSTEM
        self.activity_space = os.path.join(gvar.HABITAT_DIR, gvar.HABITAT_NAME)
        fields = ["NAME", "SHAPE@XY"]

        # create activity space feature class
        arcpy.management.CreateFeatureclass(gvar.HABITAT_DIR, gvar.HABITAT_NAME, "POINT")
        arcpy.management.AddField(self.activity_space, "NAME", "TEXT")
        arcpy.management.DefineProjection(self.activity_space, spatial_reference)

        # create home point
        home_time_spent = numpy.random.normal(7, 2)
        home_start_time = datetime.datetime(2023, 6, 20, 0, 0, 0)
        home_end_time = home_start_time + datetime.timedelta(hours=home_time_spent)
        self.home = self.__create_rand_point__("home", gvar.HOME)
        arcpy.da.InsertCursor(self.activity_space, fields).insertRow(self.home)
        home_rt = RouteTreeNode(self.home[0], self.home[1],
                                start_time=home_start_time,
                                end_time=home_end_time,
                                time_spent=home_time_spent)
        print("{0} | location: ({1}) | time spent: {2}".format(self.home[0], self.home[1], home_time_spent))

        # create work point
        work_time_spent = numpy.random.normal(6, 3)
        self.work = self.__create_rand_point__("work", gvar.WORK)
        arcpy.da.InsertCursor(self.activity_space, fields).insertRow(self.work)
        work_rt = RouteTreeNode(self.work[0], self.work[1], time_spent=work_time_spent)
        print("{0} | location: ({1}) | time spent: {2}".format(self.work[0], self.work[1], work_time_spent))

        # choose activity locations and get approx. time spent at location
        activities = self.__choose_activity_location__()
        for activity in activities:
            arcpy.da.InsertCursor(self.activity_space, fields).insertRow(activity)
            activity_time_spent = self.__get_activity_time__(activity[0])
            activity_rt = RouteTreeNode(name=activity[0],
                                        xy_coord=activity[1],
                                        time_spent=activity_time_spent)
            work_rt.add_next_location(activity_rt)
            print("{0} | location: ({1}) | time spent: {2}".format(activity[0], activity[1], activity_time_spent))

        # add all possible routes the person can take that goes through every activity location
        work_rt.add_all_routes(home_rt)
        home_rt.add_next_location(work_rt)
        self.route_tree = home_rt

    def find_route(self):
        """ Finds the final route for the person through the day.
        Requires there to be at least home and work nodes.
        Assigns high probability to routes with a more optimal time.
        :return: route that returns back home
        """
        print("\nROUTE TREE:\n{0}".format(self.route_tree))

        # calculate all routes and sort by most optimized to least
        leaf_nodes = []
        print("-------")
        print("CALCULATING ROUTES...")
        self.route_tree.calculate_all_routes(leaf_nodes)
        leaf_nodes.sort(key=lambda x: x.start_time)

        # default route is the most optimized
        final_route = leaf_nodes[0]

        # select a route with less probability to less optimized routes
        for i in range(len(leaf_nodes)):
            if i == len(leaf_nodes) - 1 or i == random.randint(0, i + 1):
                final_route = leaf_nodes[i]
                print("\nChose Route: {0}".format(i))
                break

        # save final route
        # final_route.route.saveACopy(os.path.join(gvar.ROUTE_DIR, gvar.FINAL_ROUTE_NAME))
        # self.route = final_route.route

        self.route = self.__convert_route_to_shapefile__(final_route.route)

    @staticmethod
    def __convert_route_to_shapefile__(route_to_convert):
        """
        Convert route layer file to a shapefile and sorts by start datetime.
        Separates datetime field into a date field and time field due to shapefile limitations.
        Time is saved as a string due to shapefile limitation.
        :param route_to_convert: route layer that will be converted to a shapefile.
        :return: sorted shapefile of the routes.
        """
        # create new shapefile
        shapefile = os.path.join(gvar.ROUTE_DIR, gvar.FINAL_ROUTE_NAME)
        arcpy.management.CreateFeatureclass(gvar.ROUTE_DIR, gvar.FINAL_ROUTE_NAME, "POLYLINE")
        arcpy.management.AddField(shapefile, "Name", "TEXT")
        arcpy.management.AddField(shapefile, "StartDate", "DATE")
        arcpy.management.AddField(shapefile, "StartTime", "TEXT")
        arcpy.management.AddField(shapefile, "EndDate", "DATE")
        arcpy.management.AddField(shapefile, "EndTime", "TEXT")
        arcpy.management.AddField(shapefile, "Length", "DOUBLE")

        fields = ["SHAPE@", "Name", "StartTime", "EndTime", "Total_Length"]
        new_fields = ["SHAPE@", "Name", "StartDate", "StartTime", "EndDate", "EndTime", "Length"]

        # loop through all routes in the path
        with arcpy.da.UpdateCursor(route_to_convert, fields) as cursor:
            for row in cursor:
                # get the values
                coord = row[0]
                name = row[1]
                start_date = row[2].date()
                start_time = row[2].strftime("%H:%M:%S")
                end_date = row[3].date()
                end_time = row[3].strftime("%H:%M:%S")
                length = row[4]

                print("name: {0} | start date: {1} | start time: {2} | end date: {3} | end time: {4} | length: {5}"
                      .format(name, start_date, start_time, end_date, end_time, length))

                # add the route to new shapefile
                single_route = (coord, name, start_date, start_time, end_date, end_time, length)
                arcpy.da.InsertCursor(shapefile, new_fields).insertRow(single_route)

        # organize routes in shapefile by start date and time
        sorted_routes = os.path.join(gvar.ROUTE_DIR, gvar.SORTED_ROUTE_NAME)
        arcpy.management.Sort(shapefile, sorted_routes, [["StartDate", "ASCENDING"], ["StartTime", "ASCENDING"]])

        return sorted_routes

    @staticmethod
    def __create_rand_point__(point_type: str, zone):
        """
        Creates random points in a certain zone.
        :param point_type: String contains a short description of the type of location (e.g., home, work)
        :param zone: Shapefile that bounds the points
        :return: Point with random x, y coordinates
        """
        # create feature class
        points_dir = os.path.join(gvar.SCRATCH, point_type)
        arcpy.management.FeatureToPoint(zone, points_dir, "CENTROID")

        # choose random point and loop through all the points till we encounter the point and save
        random_index = random.randrange(0, int(arcpy.management.GetCount(points_dir)[0]))
        row_num = 0
        with arcpy.da.UpdateCursor(points_dir, ["SHAPE@XY"]) as cursor:
            for row in cursor:
                if row_num == random_index:
                    x, y = float(row[0][0]), float(row[0][1])
                    arcpy.management.Delete(points_dir)
                    random_points = (point_type, arcpy.Point(x, y))
                row_num += 1

        # clean up and return
        arcpy.management.Delete(points_dir)
        return random_points

    def __choose_activity_location__(self):
        """ Get random activity locations using the distance as an estimated probability (using inverse square).
        :return: a list of the activity locations
        """
        # return value will contain tuples (point(x,y), location category)
        final_activity_locations = []

        # choose a random distance using weights of inverse square (1/x**2)
        buffer_distances = random.choices(gvar.ACTIVITY_BUFFER_DISTANCE,
                                          weights=[1/(d**2)for d in gvar.ACTIVITY_BUFFER_DISTANCE],
                                          k=gvar.NUM_ACTIVITIES)
        buffer_distances = gvar.list_to_dictionary(buffer_distances)

        # loop through the chosen distances
        for distance in buffer_distances.keys():
            # create buffer
            buffer = os.path.join(gvar.SCRATCH, "buffer_{0}".format(distance))
            arcpy.analysis.Buffer(self.activity_space, buffer, "{0} Kilometers".format(str(distance)))

            # exclude inner distance
            if distance != 1:
                excl_buffer = os.path.join(gvar.SCRATCH, "excl_buffer")
                excl_distance = gvar.ACTIVITY_BUFFER_DISTANCE[gvar.ACTIVITY_BUFFER_DISTANCE.index(distance) - 1]
                arcpy.analysis.Buffer(self.activity_space, excl_buffer, "{0} Kilometers".format(str(excl_distance)))
                arcpy.analysis.Erase(buffer, excl_buffer, "{0}_erased".format(buffer))
                arcpy.management.Delete(buffer)
                arcpy.management.Delete(excl_buffer)
                arcpy.management.Rename("{0}_erased".format(buffer), buffer)

            # select all point of interests within the area
            locations = arcpy.management.SelectLayerByLocation(gvar.POI,
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
                        row_num += 1

        return final_activity_locations

    @staticmethod
    def __get_activity_time__(activity_type: str):
        """ Use activity hours csv to find the average time spent at the activity type then apply normal distribution.
        :param activity_type: String with the activity type to get the average time
        :return: the time spent at the location
        """
        # open csv and loop through till we find the activity type
        with open(gvar.ACTIVITY_HOURS, "r") as file:
            csv_reader = csv.reader(file, delimiter=";")
            for row in csv_reader:
                if activity_type == row[0]:
                    hours_stayed = numpy.random.normal(float(row[1]), float(row[1]) * 0.5)   # normal distribution
                    return hours_stayed

        # error if no activity exists
        raise Exception("No activity {0} found in activity_hours.csv".format(activity_type))
