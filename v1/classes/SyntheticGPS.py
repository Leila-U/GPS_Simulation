import arcpy
import os
import datetime

import globalvariables as gvar
from Person import Person


class SyntheticGPS:
    def __init__(self):
        """
         activity_space: (Points) HOME, WORK, and ACTIVITY
         route: (Vectors) the route connecting all points in the activity_space
         synthetic_points: (Points) synthetic GPS data created from the route
         """
        self.person = Person()
        self.points = self.__route_to_points__()

    def __route_to_points__(self):
        synthetic_gps = os.path.join(gvar.FINAL_DIR, gvar.SYNTHETIC_GPS_POINTS)
        arcpy.management.CreateFeatureclass(gvar.FINAL_DIR, gvar.SYNTHETIC_GPS_POINTS, "POINT")
        arcpy.management.AddField(synthetic_gps, "TrackerID", "TEXT")
        arcpy.management.AddField(synthetic_gps, "Time", "TEXT")

        fields = ["SHAPE@", "StartTime", "EndTime", "Total_Length"]
        gps_fields = ["SHAPE@XY", "TrackerID", "Time"]

        with arcpy.da.UpdateCursor(self.person.route, fields) as cursor:
            for row in cursor:
                start_time = row[1]
                end_time = row[2]
                total_time = (end_time - start_time).total_seconds() / 60
                print(end_time - start_time)
                print("Start time: {0} | End time: {1} | Total time: {2}".format(start_time, end_time, total_time))

                total_distance = row[3]
                print("Distance: {0}".format(total_distance))

                meters_per_time = (total_distance / total_time) * gvar.TIME_BETWEEN_POINTS
                print("Meters per {0} minute: {1}".format(gvar.TIME_BETWEEN_POINTS, meters_per_time))

                points = os.path.join(gvar.SCRATCH_DIR, "Row_Points")
                arcpy.management.GeneratePointsAlongLines(row[0], points, "DISTANCE",
                                                          Distance="{0} Meters".format(meters_per_time),
                                                          Include_End_Points="END_POINTS")

                with arcpy.da.UpdateCursor(points, ["SHAPE@"]) as cursor2:
                    date_time = start_time
                    tracker_ID = "0"  # edit later

                    for row_point in cursor2:
                        buffer = os.path.join(gvar.SCRATCH_DIR, "Point_Buffer")
                        arcpy.analysis.Buffer(row_point, buffer, "{0} Meters".format(gvar.GPS_ACCURACY))

                        buffered_point = os.path.join(gvar.SCRATCH_DIR, "Buffered_Point")
                        arcpy.management.CreateRandomPoints(gvar.SCRATCH_DIR, "Buffered_Point", buffer, "", 1, "",
                                                            "POINT")

                        with arcpy.da.UpdateCursor(buffered_point, ["SHAPE@XY"]) as cursor3:
                            for row_point2 in cursor3:
                                x, y = float(row_point2[0][0]), float(row_point2[0][1])

                        point = (arcpy.Point(x, y), tracker_ID, date_time.strftime("%Y/%m/%d, %H:%M:%S"))
                        arcpy.da.InsertCursor(synthetic_gps, gps_fields).insertRow(point)

                        arcpy.management.Delete(buffer)
                        arcpy.management.Delete(buffered_point)
                        date_time += datetime.timedelta(minutes=gvar.TIME_BETWEEN_POINTS)
                arcpy.management.Delete(points)
        return synthetic_gps


if __name__ == "__main__":
    test = SyntheticGPS()

