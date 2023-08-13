import os
import arcpy

# DIRECTORIES
WORKSPACE = r"C:\Users\Denise\Desktop\Git\GPS_Simulation\v1"
COORD_SYSTEM = arcpy.SpatialReference("WGS 1984 UTM ZONE 17N")

# INPUT DIRECTORIES
HOME_ZONE_DIR = os.path.join(WORKSPACE, r"input\home\Residential_Zone.shp")
WORK_ZONE_DIR = os.path.join(WORKSPACE, r"input\work\Work_Zone.shp")

NETWORK_DATABASE_DIR = os.path.join(WORKSPACE, r"input\network\TransitNetwork.gdb")
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

# DATA VARIABLES
DATA_EXTENT = 1000
NUM_ACTIVITIES = 3
TIME_ZONE = "LOCAL_TIME_AT_LOCATIONS"

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
