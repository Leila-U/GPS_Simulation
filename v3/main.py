import arcpy
import time

from Classes.SyntheticGPS import SyntheticGPS

if __name__ == "__main__":
    start_time = time.time()
    arcpy.CheckOutExtension("Network")

    print("STARTING SYNTHETIC GPS TRAJECTORY...")
    example = SyntheticGPS()

    print("--- Execution time for program: {0} sec ---".format(time.time() - start_time))
