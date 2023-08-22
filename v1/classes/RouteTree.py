import datetime
import arcpy
import os
import random

import globalvariables as gvar

class RouteTreeNode:
    """
    :param name: (String) the activity location description (e.g., home, work)
    :param start_time: (Datetime) the time when the person arrives at the location
    :param end_time: (Datetime) the time when the person leaves the location
    xy_coord: (Point) the activity location coordinates
    children: (RouteTreeNode) the next points to visit
    ---
    route (Vector) the route sublayer from NA that contains the connection between the previous node to self
    """

    def __init__(self, name, xy_coord, start_time=None, end_time=None, time_spent=None):
        self.name = name
        self.xy_coord = xy_coord
        self.children = []

        # time values
        self.start_time = start_time
        self.time_spent = time_spent
        self.end_time = end_time

        # route values
        self.route = None
        self.transport_mode = None
        self.transport_prob = [0, 0, 0, 0]

    def __str__(self, depth=0):
        tree_str = "{0}{1} ({2}) | started: {3} ended: {4} time spent: {5}\n"\
            .format("\t" * depth, self.name, self.xy_coord, self.start_time, self.end_time, self.time_spent)
        for child in self.children:
            tree_str += child.__str__(depth + 1)
        return tree_str

    """SET methods"""
    def add_child(self, child_node):
        self.children.append(child_node)

    """ROUTING methods"""
    def add_all_routes(self, home_node):
        """
        Creates a tree that will visit all different paths and return home
        :param home_node: (RouteTreeNode) node person will return to at the end of path
        """
        if not self.children:
            self.add_child(RouteTreeNode(home_node.name, home_node.xy_coord, time_spent=8.0))
        else:
            for child in self.children:
                for sibling in self.children:
                    if child != sibling:
                        child.add_child(RouteTreeNode(sibling.name, sibling.xy_coord, time_spent=sibling.time_spent))
                child.add_all_routes(home_node)


    def calculate_all_routes(self, leaf_nodes: list):
        """
        Requires there to be at least home and work nodes
        Sets the route and times for all nodes and saves all routes
        :param leaf_nodes: (List[RouteTreeNode]) will be a list of all leaf nodes at the end
        """
        if not self.children:
            leaf_nodes.append(self)
            path, filename = gvar.create_unique_filename(gvar.ROUTE_NAME, gvar.ROUTES_DIR, ".lyrx")
            self.route.saveACopy(path)
            # arcpy.conversion.ExportFeatures(self.route, filename)

        for child in self.children:
            current_route = self.__calculate_route__(child)
            child.end_time = child.start_time + datetime.timedelta(hours=self.time_spent)
            if self.route:
                arcpy.management.Append(self.route, current_route)
            child.route = current_route
            child.calculate_all_routes(leaf_nodes)

    def __calculate_route__(self, end_node):
        """
        Calculates the route from self to end node using network analysis.
        :param end_node: (RouteTreeNode) the destination of the route
        :return: the routes sublayer from network analysis
        """
        arcpy.CheckOutExtension("Network")
        # create route analysis layer
        end_node.transport_mode, end_node.transport_prob = self.__determine_transport_mode__(end_node)
        route_analysis = arcpy.na.MakeRouteAnalysisLayer(gvar.NETWORK_DIR,
                                                         travel_mode=end_node.transport_mode,
                                                         sequence="USE_CURRENT_ORDER",
                                                         time_of_day=self.end_time,
                                                         time_zone=gvar.TIME_ZONE,
                                                         line_shape="ALONG_NETWORK",
                                                         generate_directions_on_solve="DIRECTIONS",
                                                         time_zone_for_time_fields=gvar.TIME_ZONE,
                                                         ignore_invalid_locations="SKIP").getOutput(0)

        # map field names
        stops_layer_name = arcpy.na.GetNAClassNames(route_analysis)["Stops"]
        field_mappings = arcpy.na.NAClassFieldMappings(route_analysis, stops_layer_name)
        field_mappings["Name"].mappedFieldName = "NAME"

        # add locations
        fields = ["NAME", "SHAPE@XY"]
        stops_dir = os.path.join(gvar.SCRATCH_DIR, "stops")
        arcpy.management.CreateFeatureclass(gvar.SCRATCH_DIR, "stops", "POINT")
        arcpy.management.AddField(stops_dir, "NAME", "TEXT")
        arcpy.da.InsertCursor(stops_dir, fields).insertRow((self.name, self.xy_coord))
        arcpy.da.InsertCursor(stops_dir, fields).insertRow((end_node.name, end_node.xy_coord))
        arcpy.na.AddLocations(route_analysis, stops_layer_name, stops_dir, field_mappings)

        # solve network analysis
        arcpy.na.Solve(route_analysis, "SKIP")
        routes_sublayer = arcpy.na.GetNASublayer(route_analysis, "Routes")

        # save the end of the route time as the end node's start time
        with arcpy.da.SearchCursor(routes_sublayer, ["EndTime"]) as routes:
            for route in routes:
                end_node.start_time = route[0]

        # clean up and return route from start to end node
        arcpy.Delete_management(stops_dir)
        return routes_sublayer

    def __determine_transport_mode__(self, end_node):
        """
        Use census data and posterior probability to determine the transportation mode for each route.
        If distance between points is less than or equal to 1km use transportation mode walking.
        :param end_node: (RouteTreeNode) the destination node
        :return: transportation mode, transportation probability: probability of each transportation mode being used
        which will influence the probability for the consecutive route
        """
        transport_mode = "walk"
        transport_prob = self.transport_prob
        if self.name == "home" and end_node.name == "work":
            census_point = os.path.join(gvar.SCRATCH_DIR, gvar.CENSUS_POINT_DIR)
            arcpy.management.CreateFeatureclass(gvar.SCRATCH_DIR, gvar.CENSUS_POINT_DIR, "POINT")
            arcpy.da.InsertCursor(census_point, ["SHAPE@XY"]).insertRow([self.xy_coord])

            census_tracts = arcpy.management.SelectLayerByLocation(gvar.CENSUS_DIR, "INTERSECT", census_point)
            fields = ["CTUID", "Total", "Vehicle", "Transit", "Walk", "Bicycle"]

            with arcpy.da.SearchCursor(census_tracts, fields) as census_tracts:
                for tract in census_tracts:
                    if tract[1] == 0:
                        transport_prob = [25, 25, 25, 25]
                    else:
                        transport_sum = sum([float(transit) for transit in tract[2:]])
                        for i in range(len(gvar.TRANSPORT_MODES)):
                            transport_prob[i] = float(tract[i+2]) / transport_sum

                if gvar.points_distance(self.xy_coord, end_node.xy_coord) > 1000:
                    transport_mode = random.choices(gvar.TRANSPORT_MODES, weights=transport_prob)[0]
            arcpy.management.Delete(census_point)
        else:
            numerators = []
            denominator = 0
            for i in range(len(gvar.TRANSPORT_MODES)):
                num = gvar.TRANSFER_PROB[gvar.TRANSPORT_MODES.index(self.transport_mode)][i] * self.transport_prob[i]
                numerators.append(num)
                denominator += num
            transport_prob = [num / denominator for num in numerators]

            if gvar.points_distance(self.xy_coord, end_node.xy_coord) > 1000:
                transport_mode = random.choices(gvar.TRANSPORT_MODES, weights=transport_prob)[0]

        print("Transport mode {0} with probabilities {1} with sum {2}"
              .format(transport_mode, transport_prob, sum(transport_prob)))
        return transport_mode, transport_prob

