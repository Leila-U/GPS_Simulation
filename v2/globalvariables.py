import arcpy
import os

""" DIRECTORIES """


# WORKSPACE
WORKSPACE = r"C:\Users\Denise\Desktop\Git\GPS_Simulation\v2"
INPUT = os.path.join(WORKSPACE, "Input")
OUTPUT = os.path.join(WORKSPACE, "Output")
SCRATCH = os.path.join(WORKSPACE, "Scratch")

# IMPORT DIRECTORIES
BOUNDARY = os.path.join(INPUT, "Boundary", "Boundary.shp")
CENSUS = os.path.join(INPUT, "Census", "Home_To_Work_Transportation.shp")
HOME = os.path.join(INPUT, "Home", "Residential_Zone.shp")
NETWORK = os.path.join(INPUT, "Network", "TransitNetwork.gdb", "TransitNetwork", "TransitNetwork_ND")
POI = os.path.join(INPUT, "POI", "POI.shp")
ACTIVITY_HOURS = os.path.join(INPUT, "POI", "Activity_Hours.csv")
WORK = os.path.join(INPUT, "Work", "Work_Zone.shp")

# OUTPUT DIRECTORIES
HABITAT_NAME = "Habitat_Points"
HABITAT_DIR = os.path.join(OUTPUT, "Habitat")

ROUTE_NAME = "Route"
FINAL_ROUTE_NAME = "Final_Route"
SORTED_ROUTE_NAME = "Sorted_Route"
ROUTE_DIR = os.path.join(OUTPUT, "Routes")

SYNTHETIC_POINTS = "Synthetic_Points"
SYNTHETIC_POINTS_DIR = os.path.join(OUTPUT, "Synthetic_Points")


""" VARIABLES """


# DATA
COORD_SYSTEM = arcpy.SpatialReference("WGS 1984 UTM ZONE 17N")
TIME_ZONE = "LOCAL_TIME_AT_LOCATIONS"

# ACTIVITIES
NUM_ACTIVITIES = 2
ACTIVITY_BUFFER_DISTANCE = [1, 2, 3, 5, 8, 13]

# TRANSPORTATION
TRANSPORT_MODES = ("vehicle", "transit", "walk", "bicycle")
TRANSFER_PROB = [[0.75, 0.25, 0.25, 0.25],
                 [0.25, 0.75, 0.50, 0.25],
                 [0.25, 0.50, 0.75, 0.50],
                 [0.25, 0.25, 0.50, 0.75]]

# GPS POINTS
TIME_BETWEEN_POINTS = 2
GPS_ACCURACY = 10


""" FUNCTIONS """


def create_unique_filename(base_name, directory, extension=""):
    """
    Creates a unique filename by adding a number to the end of the name
    :param base_name: name of the file
    :param directory: directory to save file
    :param extension: type of file
    :return: unique filename
    """
    counter = 0
    filename = "{0}_{1}.{2}".format(base_name, counter, extension)
    while os.path.exists(os.path.join(directory, filename)):
        counter += 1
        filename = "{0}_{1}.{2}".format(base_name, counter, extension)
    return filename


def points_distance(start, end):
    """
    Calculates the distance between start and end point using method GEODESIC
    :param start: (Point) starting point
    :param end: (Point) end point
    :return: float with distance
    """
    p1 = arcpy.PointGeometry(start, COORD_SYSTEM)
    p2 = arcpy.PointGeometry(end, COORD_SYSTEM)
    a1, d2 = p1.angleAndDistanceTo(p2, 'GEODESIC')
    return d2


def list_to_dictionary(lst):
    """
    Turns the list into a dictionary where key is the item and the value counts how many times the item shows up
    :param lst: items to count
    :return: dictionary(item, count)
    """
    counts = {}
    for i in lst:
        counts[i] = counts.get(i, 0) + 1
    return counts
