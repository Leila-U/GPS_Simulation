import arcpy
import datetime
import math
import os
import datetime

import globalvariables as gvar
from Classes.Person import Person


class SyntheticGPS:
    """
    Synthetic GPS points that contain the route of a person throughout their daily routine.
    ...
    Attributes
    __________
    person : Person
        the information of the person including their activity space and route
    points : FeatureClass
        the synthetic gps points
    ...
    Methods
    _______
    *route_to_points
        converts the route layer to points at a specified time interval (e.g., GPS point taken every 1min)
    *create_point_inaccuracies
        Moves point at a random x,y coordinate within a specified buffer distance.
    """

    def __init__(self):
        self.person = Person()
        self.points = self.__route_to_points__()
        print("PROGRAM FINISHED WITHOUT ERRORS. CHECK OUTPUT FOLDER.")

    def __route_to_points__(self):
        """ Converts the route layer to points at a specified time interval (e.g., GPS point taken every 1min).
        :return: shapefile with synthetic GPS points
        """
        print("-------")
        print("\nCONVERTING ROUTE TO POINTS...")
        # create feature class
        synthetic_gps = os.path.join(gvar.SYNTHETIC_POINTS_DIR, gvar.SYNTHETIC_POINTS)
        arcpy.management.CreateFeatureclass(gvar.SYNTHETIC_POINTS_DIR, gvar.SYNTHETIC_POINTS, "POINT")
        arcpy.management.AddField(synthetic_gps, "Time", "TEXT")

        # fields to grab and fields to add to feature class
        fields = ["SHAPE@", "Name", "StartDate", "StartTime", "EndDate", "EndTime", "Length"]
        gps_fields = ["SHAPE@XY", "Time"]

        # loop through all the routes
        point_time = None
        with arcpy.da.UpdateCursor(self.person.route, fields) as cursor:
            for row in cursor:
                print("\nStarting route from {0}".format(row[1]))

                # calculate the time travelled for each route then use distance to find travel speed (meters per minute)
                start_date = row[2].strftime("%Y/%m/%d")
                start_time = row[3]
                start_datetime = datetime.datetime.strptime("{0}, {1}"
                                                            .format(start_date, start_time), "%Y/%m/%d, %H:%M:%S")

                end_date = row[4].strftime("%Y/%m/%d")
                end_time = row[5]
                end_datetime = datetime.datetime.strptime("{0}, {1}"
                                                          .format(end_date, end_time), "%Y/%m/%d, %H:%M:%S")

                total_time = (end_datetime - start_datetime).total_seconds() / 60
                print("Start time: {0} | End time: {1} | Total time (min): {2}"
                      .format(start_datetime, end_datetime, total_time))

                total_distance = row[6]
                print("Distance: {0}".format(total_distance))

                meters_per_time = (total_distance / total_time) * gvar.TIME_BETWEEN_POINTS
                print("Meters per {0} minute: {1}".format(gvar.TIME_BETWEEN_POINTS, meters_per_time))
                print("...")

                # current position from start of route row
                current_distance = 0

                print("Populating activity location with points")
                # if there was no previous row then set start time of points to midnight at start date
                if not point_time:
                    point_time = datetime.datetime.strptime("{0}, 00:00:00".format(start_date), "%Y/%m/%d, %H:%M:%S")

                # populate activity location with points
                while point_time < start_datetime:
                    accurate_location = row[0].positionAlongLine(current_distance)
                    adjusted_x, adjusted_y = self.create_point_inaccuracies(accurate_location)

                    point = (arcpy.Point(adjusted_x, adjusted_y), point_time.strftime("%Y/%m/%d, %H:%M:%S"))
                    arcpy.da.InsertCursor(synthetic_gps, gps_fields).insertRow(point)

                    point_time = point_time + (datetime.timedelta(minutes=gvar.TIME_BETWEEN_POINTS))

                # create points throughout our current route
                while current_distance < total_distance:
                    print("Current distance {0} of {1} | Time: {2}"
                          .format(current_distance, total_distance, point_time))
                    accurate_location = row[0].positionAlongLine(current_distance)
                    adjusted_x, adjusted_y = self.create_point_inaccuracies(accurate_location)

                    point = (arcpy.Point(adjusted_x, adjusted_y), point_time.strftime("%Y/%m/%d, %H:%M:%S"))
                    arcpy.da.InsertCursor(synthetic_gps, gps_fields).insertRow(point)

                    # update distance and time
                    current_distance += meters_per_time
                    point_time = point_time + (datetime.timedelta(minutes=gvar.TIME_BETWEEN_POINTS))

        return synthetic_gps

    @staticmethod
    def create_point_inaccuracies(point):
        """
        Moves point at a random x,y coordinate within a specified buffer distance.
        :param point: point to add inaccuracies to
        :return: x coordinate and y coordinate
        """
        # create buffer to limit GPS accuracy
        buffer = os.path.join(gvar.SCRATCH, "Point_Buffer")
        arcpy.analysis.Buffer(point, buffer, "{0} Meters".format(gvar.GPS_ACCURACY))

        buffered_point = os.path.join(gvar.SCRATCH, "Buffered_Point")
        arcpy.management.CreateRandomPoints(gvar.SCRATCH, "Buffered_Point", buffer, "", 1, "",
                                            "POINT")

        with arcpy.da.UpdateCursor(buffered_point, ["SHAPE@XY"]) as cursor:
            for row_point2 in cursor:
                x, y = float(row_point2[0][0]), float(row_point2[0][1])

        arcpy.management.Delete(buffer)
        arcpy.management.Delete(buffered_point)

        return x, y


if __name__ == "__main__":
    test = SyntheticGPS()
    route_dir = os.path.join(gvar.ROUTE_DIR, gvar.SORTED_ROUTE_NAME + ".shp")
    test.__route_to_points__(route_dir)

