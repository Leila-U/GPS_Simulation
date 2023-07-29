import os

""" DIRECTORIES """
WORKSPACE = r"C:\Users\Denise\Desktop\Git\GPS_Simulation\v1"
COORD_SYSTEM = "WGS 1984 UTM ZONE 17N"

# INPUT DIRECTORIES
HOME_ZONE_DIR = os.path.join(WORKSPACE, r"input\home\Residential_Zone.shp")
WORK_ZONE_DIR = os.path.join(WORKSPACE, r"input\work\Work_Zone.shp")

# OUTPUT DIRECTORIES
OUTPUT_DIR = os.path.join(WORKSPACE, r"output")

SCRATCH_DIR = os.path.join(OUTPUT_DIR, r"scratch")

HABITAT_NAME = "Habitat_Points"
HABITAT_DIR = os.path.join(OUTPUT_DIR, "habitat")

""" DATA VARIABLES """
DATA_EXTENT = 1000
NUM_ACTIVITIES = 4
