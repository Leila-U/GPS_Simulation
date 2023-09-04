import arcpy
from Classes.SyntheticGPS import SyntheticGPS

if __name__ == "__main__":
    arcpy.CheckOutExtension("Network")

    print("STARTING SYNTHETIC GPS TRAJECTORY...")
    example = SyntheticGPS()
