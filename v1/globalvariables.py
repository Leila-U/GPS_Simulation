import os
import arcpy

# DIRECTORIES
WORKSPACE = r"C:\Users\Denise\Desktop\Git\GPS_Simulation\v1"
COORD_SYSTEM = arcpy.SpatialReference("WGS 1984 UTM ZONE 17N")

# INPUT DIRECTORIES
HOME_ZONE_DIR = os.path.join(WORKSPACE, "input", "home", "Residential_Zone.shp")
WORK_ZONE_DIR = os.path.join(WORKSPACE, "input", "work", "Work_Zone.shp")
POI_POINTS_DIR = os.path.join(WORKSPACE, "input", "poi", "Toronto_POI.shp")
ACTIVITY_HOURS_DIR = os.path.join(WORKSPACE, "input", "poi", "activity_hours.csv")

NETWORK_DATABASE_DIR = os.path.join(WORKSPACE, "input", "network", "TransitNetwork.gdb")
NETWORK_DIR = os.path.join(NETWORK_DATABASE_DIR, "TransitNetwork", "TransitNetwork_ND")

# OUTPUT DIRECTORIES
OUTPUT_DIR = os.path.join(WORKSPACE, r"output")

SCRATCH_DIR = os.path.join(OUTPUT_DIR, r"scratch")

HABITAT_NAME = "Habitat_Points"
HABITAT_DIR = os.path.join(OUTPUT_DIR, "habitat")

FINAL_ROUTE_NAME = "Final_Route"
ROUTE_NAME = "Route"
ROUTES_DIR = os.path.join(OUTPUT_DIR, "routes")

CENSUS_POINT_DIR = "Census_Point"
CENSUS_DIR = os.path.join(WORKSPACE, "input", "census", "work_transport_mode")

SYNTHETIC_GPS_POINTS = "Synthetic_Points"
FINAL_DIR = os.path.join(OUTPUT_DIR, "final")

# DATA VARIABLES
DATA_EXTENT = 1000
NUM_ACTIVITIES = 5
ACTIVITY_BUFFER_DISTANCE = [1, 2, 3, 5, 8, 13, 21]
TIME_ZONE = "LOCAL_TIME_AT_LOCATIONS"

TIME_BETWEEN_POINTS = 2
GPS_ACCURACY = 10

# TRANSPORTATION MATRIX
TRANSPORT_MODES = ("vehicle", "transit", "walk", "bicycle")
TRANSFER_PROB = [[0.75, 0.25, 0.25, 0.25],
                 [0.25, 0.75, 0.50, 0.25],
                 [0.25, 0.50, 0.75, 0.50],
                 [0.25, 0.25, 0.50, 0.75]]


# FUNCTIONS
def create_unique_filename(base_name, directory, extension=""):
    """
    :param base_name: name of the file
    :param directory: directory to save file in
    :param extension: the type of file
    :return: tuple(path with updated filename, unique file name with base name and number)
    """
    path_updated = os.path.join(directory, base_name + "_" + "0" + extension)
    counter = 0
    while os.path.exists(path_updated):
        counter += 1
        path_updated = os.path.join(directory, base_name + "_" + str(counter) + extension)

    filename = base_name + "_" + str(counter) + extension
    return path_updated, filename


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
