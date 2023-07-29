import arcpy

import globalvariables as gvar
from classes.SyntheticGPS import SyntheticGPS
from classes.RouteTree import RouteTreeNode

if __name__ == "__main__":
    # home = RouteTreeNode("home")
    # work = RouteTreeNode("work")
    #
    # for i in range(3):
    #     activity = RouteTreeNode("activity_" + str(i), arcpy.Point(0,0))
    #     work.add_child(activity)
    #
    # work.add_all_routes(home)
    # home.add_child(work)
    # print(home)

    arcpy.env.workspace = gvar.WORKSPACE

