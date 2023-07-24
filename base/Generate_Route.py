"""
Designed and built by Sajeeth Wimalasuriyan and Jue Wang.
Property of the University of Toronto Mississauga.
"""

#Imports
import arcpy
import random
import math
import datetime 

#Global UI parameters.
spatial_ref = int(arcpy.GetParameter(0))#Grabs number of wanted activity locations.
bufferSize = arcpy.GetParameter(1)#Grabs buffer size.
datasetAmount = arcpy.GetParameter(2)#Grabs number of datasets a user wants.
gpsNoise = arcpy.GetParameter(3)#Grabs extend of GPS noise user wants in dataset in M.
minTime = arcpy.GetParameter(4)#Grabs min time for activity locations. 
maxTime = arcpy.GetParameter(5)#Grabs the max time for activity locations.
minTimeWork = arcpy.GetParameter(6)#Grabs min time for work locations. 
maxTimeWork = arcpy.GetParameter(7)#Grabs max time for work locations. 
minTimeHome = arcpy.GetParameter(8)#Grabs min time for the home location. 
maxTimeHome = arcpy.GetParameter(9)#Grabs max time for the home location.
pointNumber = int(arcpy.GetParameter(10))#Points per second.

#Global operational parameters.
homePoint = ''#Stores home point in dataset.
workPoint = ''#Stores work point in dataset.
randomHouse = 10#Stores random ID of home location.
randomWork = 10#Stores random ID of work location.

class SyntheticGPSTrajectory():
	"""
	Contains all functions necessary to create a synthetic GPS dataset.
	"""
	def __init__(self,DataSetNumber):
		"""
		Initialize object.
		"""
		self.Internal_Count = DataSetNumber#Current dataset being made.

	def fcs_in_workspace(self):  
		"""
		Exploits ArcGIS data storage format to extract hidden files 
		necessary for the creation of synthetic datasets.
		"""
		workspace = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb"
		walk = arcpy.da.Walk(workspace, datatype="FeatureClass", type="Polyline")#Allows program to peer into filestructure.
		mainDir = ''; #Save file path of parent directory created by routing. 
		dirOfDirection = ''; #Filename for direction lines produced by routing. 
		dirStops = ''; #Stores the stops in a route. 

		#Below code looks for files of interest within randomly generated dataset.
		for dirpath, dirnames, filenames in walk:
			mainDir = dirpath #Reference to Route parent folder. 
			#Looks through all files in directory to find Routes folder and saves reference to it. 
			for filename in filenames:
				if 'Routes' in str(filename):
					dirOfDirection = mainDir + "\\" + filename 

		walk = arcpy.da.Walk(workspace, datatype="FeatureClass", type="Point")
		for dirpath, dirnames, filenames in walk:
			#Looks through all files in directory to find Stops folder and saves reference to it. 
			for filename in filenames:
				if 'Stops' in str(filename):
					dirStops = mainDir + "\\" + filename

		return (mainDir,dirOfDirection,dirStops) #Returns references to critical files as a tuple. 

	def Find_Point(self):
		"""
		Determines random home and work location to be used in the output dataset. 
		Adds random points to the dataset and creates a line between them that has 
		a buffer specified by the user around it (represents the total extent of the dataset).
		"""

		#Variables below point to projected reference data. 
		HomesLoc = r"C:\SyntheticGPSTrajectory\Projected\WherePeopleLive.shp"
		WorkLoc = r'C:\SyntheticGPSTrajectory\Projected\Work.shp'
		Homes = r'C:\SyntheticGPSTrajectory\Projected\Homes.shp'
		Works = r'C:\SyntheticGPSTrajectory\Projected\Works.shp'

		#Below control flow uses zoning datasets to create potential home and work locations then chooses random locations.
		if arcpy.Exists(Homes):
			arcpy.Delete_management(Homes)
			arcpy.FeatureToPoint_management(HomesLoc, Homes,"CENTROID")
		else:
			arcpy.FeatureToPoint_management(HomesLoc, Homes,"CENTROID")
		randomHouse = random.randrange(int(arcpy.GetCount_management(Homes)[0]))
		if arcpy.Exists(Works):
			arcpy.Delete_management(Works)
			arcpy.FeatureToPoint_management(WorkLoc, Works,"CENTROID")
		else:
			arcpy.FeatureToPoint_management(WorkLoc, Works,"CENTROID")
		randomWork = random.randrange(int(arcpy.GetCount_management(Works)[0]))

		#Creates files used to store key information that may include work, home and activity areas at any given time. 
		WorkSpace = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb"
		NewPointDataset = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb\habitatareas"
		arcpy.CreateFeatureclass_management(WorkSpace, 'habitatareas', 'POINT')
		homeForLTR = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb\homeForLTR"
		workForLTR = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb\workForLTR"
		arcpy.CreateFeatureclass_management(WorkSpace, 'homeForLTR', 'POINT')
		arcpy.CreateFeatureclass_management(WorkSpace, 'workForLTR', 'POINT')

		#Below code grabs a random home location based on zoning data.
		fields = ['SHAPE@XY']
		count = 0#Used to track and find points of interest.
		#Code below grabs houses from Homes dataset.
		with arcpy.da.UpdateCursor(Homes, fields) as cursor:
			for row in cursor:
				old_X = float(row[0][0])
				old_Y = float(row[0][1])
				count = count + 1
				if randomHouse == count:
					homePoint = ("HOME", 100, arcpy.Point(old_X, old_Y))#Saves randomly chosen home location.
		count = 0#Used to track and find points of interest.

		#Code below grabs workplaces using zoning data.
		with arcpy.da.UpdateCursor(Works, fields) as cursor:
			for row in cursor:
				old_X = float(row[0][0])
				old_Y = float(row[0][1])
				count = count + 1
				if randomWork == count:
					workPoint = ("WORK", 100, arcpy.Point(old_X, old_Y))#Saves randomly chosen work location.


		#Creates new feature class containing selected home point for future use in generating algorithm.
		arcpy.AddField_management(homeForLTR, "NAME", "TEXT")
		arcpy.AddField_management(homeForLTR, "NEAR_DIST", "LONG")
		cursor = arcpy.da.InsertCursor(homeForLTR, ["NAME","NEAR_DIST","SHAPE@XY"])
		xy = homePoint
		cursor.insertRow(xy)
		# Delete cursor object
		del cursor

		#Creates new feature class containing selected work point for future use in generating algorithm.
		arcpy.AddField_management(workForLTR, "NAME", "TEXT")
		arcpy.AddField_management(workForLTR, "NEAR_DIST", "LONG")
		cursor = arcpy.da.InsertCursor(workForLTR, ["NAME","NEAR_DIST","SHAPE@XY"])
		xy = workPoint
		cursor.insertRow(xy)
		# Delete cursor object
		del cursor

		#Below new feature class is created containing work and home locations for buffer analysis.
		arcpy.AddField_management(NewPointDataset, "NAME", "TEXT")
		arcpy.AddField_management(NewPointDataset, "NEAR_DIST", "LONG")
		cursor = arcpy.da.InsertCursor(NewPointDataset, ["NAME","NEAR_DIST","SHAPE@XY"])
		xy = homePoint
		cursor.insertRow(xy)
		cursor.insertRow(workPoint)
		# Delete cursor object
		del cursor

		#Code below prepares data further in order for buffer analysis to be run
		betweenWorkAndHome = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb\WorkNHome"
		betweenWorkAndHomeBuffer = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb\WorkNHomeBuffer"
		temp = r'C:\SyntheticGPSTrajectory\WorkSpace\temp.shp'
		BufferStorage = r'C:\SyntheticGPSTrajectory\WorkSpace\BufferStorage.shp'
		arcpy.Copy_management(Homes, temp)
		arcpy.DeleteFeatures_management(temp)
		arcpy.AddField_management(temp, "NAME", "TEXT")
		arcpy.AddField_management(temp, "NEAR_DIST", "LONG")
		cursor = arcpy.da.InsertCursor(temp, ["NAME","NEAR_DIST","SHAPE@XY"])
		xy = homePoint
		cursor.insertRow(xy)
		cursor.insertRow(workPoint)
		# Delete cursor object
		del cursor

		#Buffer between work and home point is made.
		arcpy.PointsToLine_management(temp, BufferStorage)
		arcpy.Buffer_analysis(BufferStorage, betweenWorkAndHomeBuffer, str(bufferSize) + " Meters")

		#Cleanup is below. 
		arcpy.Delete_management(temp)
		arcpy.Delete_management(BufferStorage)

	def Network_Analysis(self):
		"""
		Finds the optimal route between home, work, and activity locations
		based on input .nd file. Most of the geoprocessing necessary for the
		operation of the algorithm occurs here.
		"""

		#Variables below refer to all datasets needed to run route generating algorithm. 
		torontoOutline =  r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb\buffeting"
		workspaceForPoints = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb"
		betweenWorkAndHomeBuffer = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb\WorkNHomeBuffer"
		final = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb\finalDestinations"
		habitatareas = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb\habitatareas"
		RandomPointsPlusHome = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb\RandomPointsPlusHome"
		workForLTR = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb\workForLTR"
		homeForLTR = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb\homeForLTR"
		homeForLTR2 = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb\homeForLTR2"

		# Check out any necessary licenses.
		arcpy.env.overwriteOutput = False
		arcpy.CheckOutExtension("Network")
		arcpy.CheckOutExtension("GeoStats")

		#Makes the route layer to enable route calculations.
		Network_Data_Source = r"C:\SyntheticGPSTrajectory\TorontoRoad.gdb\RoadNetwork\RoadNetwork_ND"
		RandDest = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb\RandomDestination"
		Route = arcpy.na.MakeRouteAnalysisLayer(network_data_source=Network_Data_Source,
		layer_name="RouteSKIA" +str(self.Internal_Count))
		
		#Copies features management takes points from homeForLTR and adds them to homeForLTR2.
		arcpy.CopyFeatures_management(homeForLTR, homeForLTR2)
		WorkSpace = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb"
		ResidualPoints = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb\ResidualPoints"

		#Creates ResidualPoints feature class which is critical in making the datasets.
		#All points are stored in ResidualPoints dataset and it is the precursor to the final dataset. 
		arcpy.CreateFeatureclass_management(WorkSpace, 'ResidualPoints', 'POINT')
		
		#This loop block contains all the code used to generate points between various locations. This loop
		#block also deals with assigning times for all points. 
		
		for i in range(spatial_ref + 2):

			#Creates random point based off zoning information previously used.
			arcpy.CreateRandomPoints_management(workspaceForPoints,"RandomDestination",betweenWorkAndHomeBuffer, 
			"",1,"", "POINT")
			
			if i == 0:
				#This if condition deals with the beggining of the loop which is home and adds it to dataset used in route processing.
				tempSave = ''
				fields = ["SHAPE@XY"]
				with arcpy.da.UpdateCursor(workForLTR, fields) as cursor:
					for row in cursor:
						old_X = float(row[0][0])
						old_Y = float(row[0][1])
						tempSave = [arcpy.Point(old_X, old_Y)]
				del cursor #delete cursor
				cursor = arcpy.da.InsertCursor(homeForLTR,['SHAPE@XY'])		
				cursor.insertRow(tempSave)
				# Delete cursor object
				del cursor

			elif i == spatial_ref + 1:
				#This if condition deals with the end of the loop which aims to route the algorithm back home and adds it to dataset used in route processing.
				tempSave = ''
				fields = ["SHAPE@XY"]
				with arcpy.da.UpdateCursor(homeForLTR2, fields) as cursor:
					for row in cursor:
						old_X = float(row[0][0])
						old_Y = float(row[0][1])
						tempSave = [arcpy.Point(old_X, old_Y)]
				del cursor #delete cursor
				cursor = arcpy.da.InsertCursor(homeForLTR,['SHAPE@XY'])		
				cursor.insertRow(tempSave)
				# Delete cursor object
				del cursor

			else: 
				#This else condition adds activity locations to the dataset used in route processing. 
				tempSave = ''
				fields = ["SHAPE@XY"]
				with arcpy.da.UpdateCursor(RandDest, fields) as cursor:
					for row in cursor:
						old_X = float(row[0][0])
						old_Y = float(row[0][1])

						tempSave = [arcpy.Point(old_X, old_Y)]
				del cursor #delete cursor
				cursor = arcpy.da.InsertCursor(homeForLTR,['SHAPE@XY'])		
				cursor.insertRow(tempSave)
				# Delete cursor object
				del cursor

			#Code below sets up a network analysis layer with individual routes between either work, home or activity locations.
			Updated_Input_Network_Analysis_Layer = arcpy.AddLocations_na(in_network_analysis_layer=Route, sub_layer="Stops", 
			in_table=homeForLTR, field_mappings="Name Name #", search_tolerance="5000 Meters", sort_field="", 
			search_criteria=[], match_type="MATCH_TO_CLOSEST", append="APPEND", snap_to_position_along_network="NO_SNAP", 
			snap_offset="5 Meters", exclude_restricted_elements="EXCLUDE", search_query=[])[0]

			#Code below finds the shortest route between 2 points (either work, home or activity locations).
			Network_Analyst_Layer, Solve_Succeeded = arcpy.Solve_na(in_network_analysis_layer=Updated_Input_Network_Analysis_Layer, 
			ignore_invalids="SKIP", terminate_on_solve_error="TERMINATE", simplification_tolerance="", overrides="")

			#Following chunk of code is used to scale time and number of points generated.
			timeForMovement = 16 #16 is a scaling factor used. The scaling factor controls the speed of the simulated car traveling between routes.
			secondsPerPoint = pointNumber 
			distanceTimeCalc = str(timeForMovement * secondsPerPoint) + ' meters' #Calculation done to determine distance between points.

			findr = self.fcs_in_workspace()#Grabs the files created by route analysis (Solve_na).
			PAL = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb\PointAlongLine"
			TemporaryWorkspace = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb"

			#Creates points along route direction lines based on user specified parameters.
			arcpy.GeneratePointsAlongLines_management(findr[1], PAL, 'DISTANCE', Distance=distanceTimeCalc)#210 was found to be optimal distance for subsequent steps.

			#Code below grabs each individual point from a list of points of interest and adds it to a new feature.
			getFirstPoints = []
			PALPointStorage = []
			fields = ["SHAPE@XY"]
			with arcpy.da.UpdateCursor(PAL, fields) as cursor:
				for row in cursor:
					old_X = float(row[0][0])
					old_Y = float(row[0][1])
					PALPointStorage.append([arcpy.Point(old_X, old_Y)])
			del cursor #delete cursor

			#Code chunk below saves first point from previously generated dualpoint dataset.
			old_X = True 
			old_Y = True 
			fields = ["SHAPE@XY"]
			with arcpy.da.UpdateCursor(homeForLTR, fields) as cursor:
				for row in cursor:
					old_X = float(row[0][0])
					old_Y = float(row[0][1])
					break #Ensures only first point in dataset is grabbed. 
				del cursor #delete cursor

			timeForPOI = 60 / secondsPerPoint#Calculates increment factor for the time saved to individual points.
			minTime = int(arcpy.GetParameter(4))#Grabs min time for activity locations. 
			maxTime = int(arcpy.GetParameter(5))#Grabs the max time for activity locations.
			minTimeWork = int(arcpy.GetParameter(6))#Grabs min time for work locations. 
			maxTimeWork = int(arcpy.GetParameter(7))#Grabs max time for work locations. 
			minTimeHome = int(arcpy.GetParameter(8))#Grabs min time for the home location. 
			maxTimeHome = int(arcpy.GetParameter(9))#Grabs max time for the home location.

			if i == 0: 
				#Adds location clustors to the home location. 
				amountOfHomePoints = random.randint(minTimeHome,maxTimeHome) // secondsPerPoint #Determines amount of home points. 
				cursor = arcpy.da.InsertCursor(ResidualPoints,['SHAPE@XY'])		
				for row in range(amountOfHomePoints):
					#Code chunk below uses gaussian displacement to disperce points in a certain radius to simulate clusters.
					random_angle = random.uniform(0.0, math.pi*2)
					random_number = random.gauss(0,1)
					hypothenuse = random_number * 10
					delta_X = (math.cos(random_angle)) * hypothenuse
					delta_Y = (math.sin(random_angle)) * hypothenuse
					new_X = old_X + delta_X
					new_Y = old_Y + delta_Y
					cursor.insertRow([arcpy.Point(new_X, new_Y)])
				# Delete cursor object
				del cursor

			elif i == 1: 
				#Adds location clustors to the work location. 
				amountOfWorkPoints = random.randint(minTimeWork,maxTimeWork) // secondsPerPoint#Determines amount of work points. 
				cursor = arcpy.da.InsertCursor(ResidualPoints,['SHAPE@XY'])		
				for row in range(amountOfWorkPoints):
					#Code chunk below uses gaussian displacement to disperce points in a certain radius to simulate clusters.
					random_angle = random.uniform(0.0, math.pi*2)
					random_number = random.gauss(0,1)
					hypothenuse = random_number * 14
					delta_X = (math.cos(random_angle)) * hypothenuse
					delta_Y = (math.sin(random_angle)) * hypothenuse
					new_X = old_X + delta_X
					new_Y = old_Y + delta_Y
					cursor.insertRow([arcpy.Point(new_X, new_Y)])
				# Delete cursor object
				del cursor

			else:
				#Adds location clustors to the activity locations. 
				amountOfActPoints = random.randint(minTime,maxTime) // secondsPerPoint#Determines amount of activity location points. 
				cursor = arcpy.da.InsertCursor(ResidualPoints,['SHAPE@XY'])		
				for row in range(amountOfActPoints):
					#Code chunk below uses gaussian displacement to disperce points in a certain radius to simulate clusters.
					random_angle = random.uniform(0.0, math.pi*2)
					random_number = random.gauss(0,1)
					hypothenuse = random_number * 16
					delta_X = (math.cos(random_angle)) * hypothenuse
					delta_Y = (math.sin(random_angle)) * hypothenuse
					new_X = old_X + delta_X
					new_Y = old_Y + delta_Y
					cursor.insertRow([arcpy.Point(new_X, new_Y)])
				# Delete cursor object
				del cursor

			#Code chunk below takes points saved from PAL dataset and adds them to the ResidualPoints dataset.
			cursor = arcpy.da.InsertCursor(ResidualPoints,['SHAPE@XY'])		
			for row in PALPointStorage:
				cursor.insertRow(row)
			# Delete cursor object
			del cursor

			#Code chunk below removes first point from homeForLTR dataset setting up the next iteration of the loop.
			#Deletes first item so next iteration can add new point location creating a continuous route. 
			fields = ["SHAPE@XY"]
			with arcpy.da.UpdateCursor(homeForLTR, fields) as cursor:
				for row in cursor:
					cursor.deleteRow()
					break
				del cursor #delete cursor

			#Cleanup 
			arcpy.Delete_management(PAL)
			arcpy.Delete_management(RandDest)

			#Adds field to ResidualPoints preparing dataset for the addition of time information. 
			arcpy.AddField_management(ResidualPoints, "UTC_DATE", "TEXT")

		#Below code chunk adds time data to all points in synthetic trajectory dataset.
		time = datetime.datetime(2021, 10, 1,0,0,0)
		fields = ["SHAPE@XY", "UTC_DATE"]
		# Create update cursor for feature class 
		with arcpy.da.UpdateCursor(ResidualPoints, fields) as cursor:
			for row in cursor:
				time += datetime.timedelta(seconds=secondsPerPoint)
				row[1] = str(time) #Adds string representation of datetime object to point.
				cursor.updateRow(row) #Saves updated time information.

	def Generate_Route(self):
		"""
		Orchestrates other methods to run the algorithm. The function also helps 
		to clean up after the algorithm is done (delete stopgap files).
		"""
		#Runs necessary function to assemple final output dataset.

		#Methods are run in the order needed to succesfully run algorithm.
		self.Find_Point() #Method uses zoning information to find suitable work and home locations.
		self.Network_Analysis()#Finds routes between work, home and activity locations. This method also assembles data into semifinal dataset.
		findr = self.fcs_in_workspace()#Method finds the Route dataset. Called here for cleanup purposes.

		#Reference to all datasets made when algorithm runs.
		workspace = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb"
		habitatareas = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb\habitatareas"
		homeForLTR = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb\homeForLTR"
		homeForLTR2 = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb\homeForLTR2"
		ResidualPoints = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb\ResidualPoints"
		workForLTR = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb\workForLTR"
		WorkNHomeBuffer = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb\WorkNHomeBuffer"
		
		newName = 'SyntheticGPSTrajectory_' + str(self.Internal_Count)#Final dataset name is generated. 
		if arcpy.Exists(newName):#Checks if existing file with same name as newName exists. If a file exists it is deleted.
			arcpy.Delete_management(newName)
		arcpy.CopyFeatures_management(ResidualPoints, newName)#Final output dataset is generated based on ResidualPoints dataset.

		#The newly created dataset is projected into the WGS 1984 UTM Zone 17N which is used exclusively throughout the algorithm. 
		newFile = r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb\\" + newName #Reference to final output dataset.
		sr = arcpy.SpatialReference("WGS 1984 UTM Zone 17N")#References projection.
		arcpy.DefineProjection_management(newFile, sr)#Projects the final output dataset.

		#Cleanup
		arcpy.Delete_management(findr[0])
		arcpy.Delete_management(habitatareas)
		arcpy.Delete_management(homeForLTR)
		arcpy.Delete_management(homeForLTR2)
		arcpy.Delete_management(ResidualPoints)
		arcpy.Delete_management(workForLTR)
		arcpy.Delete_management(WorkNHomeBuffer)

#Runs program in ArcGIS Pro
if __name__ == '__main__':
	with arcpy.EnvManager(scratchWorkspace=r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb", 
	workspace=r"C:\SyntheticGPSTrajectory\SyntheticGPSTrajectory.gdb"): #Set up environment and run code within it.
		for i in range(datasetAmount):#Loops to control the number of datasets made.
			runner = SyntheticGPSTrajectory(i)#Creates new object.
			runner.Generate_Route()#Runs object to create data.