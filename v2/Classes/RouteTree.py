import arcpy
import datetime
import os
import random

import globalvariables as gvar


class RouteTreeNode:
    """
    A tree data structure that contains the path from the current node to the next activity locations with transit and
    time parameters.
    ...
    Attributes
    __________
    name : String
        activity location description (e.g., home, work)
    xy_coord : Point
        activity location coordinates
    next_nodes : List[RouteTreeNode]
        next nodes to visit in the path
    start_time : Datetime
        time when the person arrives at the node location
    end_time : Datetime
        time when the person leaves the node location
    time_spent : Float
        time spent at the node location
    route : FeatureClass
        route sublayer from NA connecting the parent node to self
    transport_mode : String
        transportation mode used between the parent node to self
    transport_prob : List[Float]
        list of probabilities of using the transportation modes in global variables
    ...
    Methods
    _______
    add_next_location(node: RouteTreeNode)
        adds node to the list of next locations to visit
    add_all_routes(home_node: RouteTreeNode)
        add all path variations from self, goes through all node locations, and ends at the home_node
    calculate_all_routes(leaf_nodes: List[RouteTreeNode])
        calculates the route between all the nodes in the path and sets the times
    *calculate_route(end_node: RouteTreeNode)
        calculate the route from self to end_node using arcpy network analysis
    *determine_transportation_mode(end_node: RouteTreeNode)
        determine the transportation mode from self to end_node using census data and posterior probability
    """

    def __init__(self, name: str, xy_coord: arcpy.Point, start_time: datetime = None, end_time: datetime = None,
                 time_spent: float = None):
        """
        :param name: activity location description (e.g., home, work)
        :param xy_coord: activity location coordinates
        :param start_time: time when the person arrives at the node location
        :param end_time: time when the person leaves the node location
        :param time_spent: time spent at the node location
        """
        self.name = name
        self.xy_coord = xy_coord
        self.next_nodes = []

        # time values
        self.start_time = start_time
        self.end_time = end_time
        self.time_spent = time_spent

        # route values
        self.route = None
        self.transport_mode = None
        self.transport_prob = [0 for _ in gvar.TRANSPORT_MODES]

    def __str__(self, depth: int = 0) -> str:
        """ Makes a formatted string representation of the node and its children.
        :param depth: the depth of the node in the full path
        :return: string representation of the tree
        """
        tree_str = "{0}{1} at ({2}) | arrived: {3} | left: {4} | spent: {5}\n"\
            .format("\t" * depth, self.name, self.xy_coord, self.start_time, self.end_time, self.time_spent)
        for node in self.next_nodes:
            tree_str += node.__str__(depth + 1)
        return tree_str

    def add_next_location(self, node):
        """ Adds node to the list of next locations to visit.
        :param node: RouteTreeNode that will be added to the list of next locations
        :return: None
        """
        self.next_nodes.append(node)

    def add_all_routes(self, home_node):
        """ Add all path variations from self, goes through all node locations, and ends at the home_node.
        :param home_node: RouteTreeNode that the person will return to at the end of the path
        :return: None
        """
        # if all activity locations have been visited return home
        if not self.next_nodes:
            self.add_next_location(RouteTreeNode(name=home_node.name,
                                                 xy_coord=home_node.xy_coord,
                                                 time_spent=8.0))

        # add all other nodes at the same depth as children (nodes to visit next)
        else:
            for child in self.next_nodes:
                for sibling in self.next_nodes:
                    if child != sibling:
                        child.add_next_location(RouteTreeNode(name=sibling.name,
                                                              xy_coord=sibling.xy_coord,
                                                              time_spent=sibling.time_spent))

                # recurse for all children
                child.add_all_routes(home_node)

    def calculate_all_routes(self, leaf_nodes: list):
        """ Calculates the route between all the nodes in the path and sets the times.
        :param leaf_nodes: List[RouteTreeNode] of all leaf nodes at the end of the path
        :return: None
        """
        # save the route if it is the last node in the path
        if not self.next_nodes:
            leaf_nodes.append(self)
            filename = gvar.create_unique_filename(gvar.ROUTE_NAME, gvar.ROUTE_DIR, "lyrx")
            self.route.saveACopy(os.path.join(gvar.ROUTE_DIR, filename))

        # calculate the route from self to every child and save it in child.route
        for child in self.next_nodes:
            current_route = self.__calculate_route__(child)
            child.end_time = child.start_time + datetime.timedelta(hours=self.time_spent)
            if self.route:
                arcpy.management.Append(self.route, current_route)
            child.route = current_route

            # recurse for all children
            child.calculate_all_routes(leaf_nodes)

    def __calculate_route__(self, end_node):
        """ Calculate the route from self to end_node using arcpy network analysis.
        :param end_node: RouteTreeNode the destination of the route
        :return: the routes sublayer from network analysis
        """
        # get transportation mode
        end_node.transport_mode, end_node.transport_prob = self.__determine_transport_mode__(end_node)

        # create route analysis layer
        route_analysis = arcpy.na.MakeRouteAnalysisLayer(gvar.NETWORK,
                                                         travel_mode=end_node.transport_mode,
                                                         sequence="USE_CURRENT_ORDER",
                                                         time_of_day=self.end_time,
                                                         time_zone=gvar.TIME_ZONE,
                                                         line_shape="ALONG_NETWORK",
                                                         generate_directions_on_solve="NO_DIRECTIONS",
                                                         ignore_invalid_locations="HALT").getOutput(0)

        # map field names
        stops_layer_name = arcpy.na.GetNAClassNames(route_analysis)["Stops"]
        field_mappings = arcpy.na.NAClassFieldMappings(route_analysis, stops_layer_name)
        field_mappings["Name"].mappedFieldName = "NAME"

        # add locations
        fields = ["NAME", "SHAPE@XY"]
        stops = os.path.join(gvar.SCRATCH, "stops")
        arcpy.management.CreateFeatureclass(gvar.SCRATCH, "stops", "POINT")
        arcpy.management.AddField(stops, "NAME", "TEXT")
        arcpy.da.InsertCursor(stops, fields).insertRow((self.name, self.xy_coord))
        arcpy.da.InsertCursor(stops, fields).insertRow((end_node.name, end_node.xy_coord))
        arcpy.na.AddLocations(route_analysis, stops_layer_name, stops, field_mappings)

        # solve network analysis
        arcpy.na.Solve(route_analysis, "SKIP")
        routes_sublayer = arcpy.na.GetNASublayer(route_analysis, "Routes")

        # save the end of the route time as the end node's start time
        with arcpy.da.SearchCursor(routes_sublayer, ["EndTime"]) as routes:
            for route in routes:
                end_node.start_time = route[0]

        # clean up and return route from start to end node
        arcpy.Delete_management(stops)
        return routes_sublayer

    def __determine_transport_mode__(self, end_node):
        """ Determine the transportation mode from self to end_node using census data and posterior probability.
        If distance between points is less than or equal to 1km use transportation mode walking.
        If no census data for home then default all probabilities to equal
        Returns the updated transportation probabilities which will influence future transportation modes taken from
        end_node.
        :param end_node: RouteTreeNode the destination of the route
        :return: transportation mode, transportation probability
        """
        # default transportation mode
        transport_mode = "walk"
        transport_prob = self.transport_prob

        # if heading from home to work then use census data
        if self.name == "home" and end_node.name == "work":
            # select tract where home is located
            census_point = os.path.join(gvar.SCRATCH, "census_point")
            arcpy.management.CreateFeatureclass(gvar.SCRATCH, "census_point", "POINT")
            arcpy.da.InsertCursor(census_point, ["SHAPE@XY"]).insertRow([self.xy_coord])

            census_tracts = arcpy.management.SelectLayerByLocation(gvar.CENSUS, "INTERSECT", census_point)
            fields = ["CTUID", "Total", "Vehicle", "Transit", "Walk", "Bicycle"]

            # get probabilities using figures from tract
            with arcpy.da.SearchCursor(census_tracts, fields) as tracts:
                for tract in tracts:
                    if tract[1] == 0:   # if census data does not exist then make all probabilities equal
                        transport_prob = [100/len(gvar.TRANSPORT_MODES) for _ in gvar.TRANSPORT_MODES]
                    else:
                        transport_sum = sum([float(transit) for transit in tract[2:]])
                        for i in range(len(gvar.TRANSPORT_MODES)):
                            transport_prob[i] = float(tract[i + 2]) / transport_sum

            # clean up
            arcpy.management.Delete(census_point)

        # update the probabilities using posterior probability
        else:
            numerators = []
            denominator = 0
            for i in range(len(gvar.TRANSPORT_MODES)):
                num = gvar.TRANSFER_PROB[gvar.TRANSPORT_MODES.index(self.transport_mode)][i] * self.transport_prob[i]
                numerators.append(num)
                denominator += num
            transport_prob = [num / denominator for num in numerators]

        # randomly determine transport mode unless it is closer than 1000 meters than use default
        if gvar.points_distance(self.xy_coord, end_node.xy_coord) > 1000:
            transport_mode = random.choices(gvar.TRANSPORT_MODES, weights=transport_prob)[0]

        # print transport information and return
        print("{0} to {1} | Mode: {2} | Prob.: {3}".format(self.name, end_node.name, transport_mode, transport_prob))
        return transport_mode, transport_prob
