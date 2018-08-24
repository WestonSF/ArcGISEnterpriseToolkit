#-------------------------------------------------------------
# Name:       Map Service Test
# Purpose:    Runs a configurable query against a map service and produces a report on draw times at specified scales.
# Author:     Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:    05/08/2015
# Last Updated:    11/08/2015
# Copyright:   (c) Eagle Technology
# ArcGIS Version:   10.3+
# Python Version:   2.7
#--------------------------------

# Import modules
import os
import sys
import logging
import smtplib
import arcpy
import string
import urllib
import urllib2
import time
import json
import math
from urlparse import urlparse

# Enable data to be overwritten
arcpy.env.overwriteOutput = True

# Set global variables
enableLogging = "false" # Use logger.info("Example..."), logger.warning("Example..."), logger.error("Example...")
logFile = "" # os.path.join(os.path.dirname(__file__), "Example.log")
sendErrorEmail = "false"
emailTo = ""
emailUser = ""
emailPassword = ""
emailSubject = ""
emailMessage = ""
enableProxy = "false"
requestProtocol = "http" # http or https
proxyURL = ""
output = None

# Start of main function
def mainFunction(mapService,username,password,boundingBox,scales,imageFormat,numberQueries,csvFile): # Get parameters from ArcGIS Desktop tool by seperating by comma e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)  
    try:
        # --------------------------------------- Start of code --------------------------------------- #
        # Set constant variables
        dpi = 96
        ImageWidth = 1280
        ImageHeight = 768
        
        # GlobalVariables
        cachedMapService = False
        scaleData = []

        # Seperate out XY coordinates
        boundingBox = boundingBox.split(" ")

        # Get the image format
        if (imageFormat == "PNG"):
            imageFormat = "png"
        if (imageFormat == "JPG"):
            imageFormat = "jpg"            

        # Get the server name and port
        parse_object = urlparse(mapService)
        protocol = parse_object.scheme
        serverNameAndPort = parse_object.netloc.split(":")
        serverName = serverNameAndPort[0]
        if (len(serverNameAndPort) > 1):
            serverPort = serverNameAndPort[1]
        else:
            serverPort = 80
            if (protocol.lower() == "https"):
                serverPort = 443
        
        # Get token if needed
        token = ""
        if (username and password):
            token = getToken(username, password, serverName, serverPort)

        # If token received
        if (token):
            # Setup the query
            query = mapService + "?f=json&token=" + token;
        else:
            # Setup the query
            query = mapService + "?f=json";

        # Make the query to the map service
        response, downloadTime = urlQuery(query)
        dataObject = json.loads(response)
        # If the map service is cached
        if "tileInfo" in dataObject:
            arcpy.AddMessage("Map Service is cached...")
            cachedMapService = True
        
            # Get the tile info
            tileInfo = dataObject['tileInfo']
            tileHeight = tileInfo['rows']
            tileWidth = tileInfo['cols']
            tileOriginX = tileInfo['origin']['x']
            tileOriginY = tileInfo['origin']['y']
            dpi = tileInfo['dpi']

            # Get the centre point of the bounding box
            searchPointX = float(boundingBox[0]) + ((float(boundingBox[2]) - float(boundingBox[0])) / 2);
            searchPointY = float(boundingBox[1]) + ((float(boundingBox[3]) - float(boundingBox[1])) / 2);

            count = 0
            # Make the number of queries as specified
            while (count < int(numberQueries)):
                arcpy.AddMessage("Map service query " + str(count + 1))
                
                # Iterate through the levels
                for level in tileInfo['lods']:
                    thisLevel = level['level']
                    thisScale = level['scale']
                    thisResolution = level['resolution']
                    
                    # Dividing image width by DPI to get it in inches
                    imgWidthInInch = ImageWidth / dpi;
                    imgHeightInInch = ImageHeight / dpi;

                    # Converting inch to metre (assume the map is in metre)
                    imgWidthInMapUnit = imgWidthInInch * 0.0254;
                    imgHeightInMapUnit = imgHeightInInch * 0.0254;

                    # Calculating half of maps height & width at the specific scale
                    halfX = (imgWidthInMapUnit * thisScale) / 2;
                    halfY = (imgHeightInMapUnit * thisScale) / 2;

                    # Setup the extent
                    XMin = searchPointX - halfX
                    XMax = searchPointX + halfX
                    YMin = searchPointY - halfY
                    YMax = searchPointY + halfY

                    # Get the tile info - Top left
                    topLeftPointX = XMin
                    topLeftPointY = YMax
                    # Get the tile info - Bottom right
                    bottomRightPointX = XMax
                    bottomRightPointY = YMin
                    
                    # Find the tile row and column - Top left
                    topLeftTileColumn = int(math.floor((float(topLeftPointX) - float(tileOriginX)) / (float(thisResolution) * float(tileWidth))))                    
                    topLeftTileRow = int(math.floor((float(tileOriginY) - float(topLeftPointY)) / (float(thisResolution) * float(tileHeight))))        
                    # Find the tile row and column - Bottom right
                    bottomRightTileColumn = int(math.floor((float(bottomRightPointX) - float(tileOriginX)) / (float(thisResolution) * float(tileWidth))))                    
                    bottomRightTileRow = int(math.floor((float(tileOriginY) - float(bottomRightPointY)) / (float(thisResolution) * float(tileHeight))))       

                    # Return all the tiles in between
                    tileCount = 0
                    tileMissingCount = 0
                    totalDownloadTime = 0
                    column = topLeftTileColumn
                    while (column < bottomRightTileColumn):
                        row = topLeftTileRow
                        while (row < bottomRightTileRow):
                            query = mapService + "/tile/" + str(thisLevel) + "/" + str(row) + "/" + str(column);
                            # If token received
                            if (token):
                                # Add token to query
                                query = query + "?token=" + token
                        
                            # Make the query to the map service
                            response, downloadTime = urlQuery(query)

                            # If tile returned
                            if (response.lower() != "missing"):
                                # Update total download time
                                totalDownloadTime = totalDownloadTime + downloadTime

                                # Set the file path
                                file = os.path.join(arcpy.env.scratchFolder, "MapService_" + str(thisScale) + "_" + str(row) + "_" + str(column) + "." + str(imageFormat))

                                # Open the file for writing
                                responseImage = open(file, "wb")

                                # Read from request while writing to file
                                responseImage.write(response)
                                responseImage.close()
                    
                                tileCount = tileCount + 1
                            # Missing tiles
                            else:
                                tileMissingCount = tileMissingCount + 1
                            row = row + 1
                        column = column + 1

                    arcpy.AddMessage("Tiles found - " + str(tileCount) + "...")
                    arcpy.AddMessage("Tiles missing - " + str(tileMissingCount) + "...")
                    arcpy.AddMessage("1:" + str(thisScale) + " draw time - " + str(totalDownloadTime) + "...")
                    
                    # Add results to array
                    for eachScaleData in scaleData:             
                        # If scale is already in array
                        if (str(thisScale) == str(eachScaleData[0])):
                            # Add results to existing array value
                            eachScaleData[2] = float(eachScaleData[2]) + float(totalDownloadTime)
                            
                    # If on the first query
                    if (count == 0):
                        # Add results to array
                        scaleData.append([str(thisScale), str(tileCount), str(tileMissingCount), str(totalDownloadTime)])

                count = count + 1
        # Dynamic map service
        else:
            arcpy.AddMessage("Map Service is dynamic...")
            cachedMapService = False
            
            # If a string, convert to array for scales
            if isinstance(scales, basestring):
                scales = string.split(scales, ";")

            count = 0
            # Make the number of queries as specified
            while (count < int(numberQueries)):
                arcpy.AddMessage("Map service query " + str(count + 1))
                                    
                # For each scale specified
                for scale in scales:
                    # Setup the query
                    query = mapService + "/export?f=image&dpi=" + str(dpi);
                    query = query + "&format=" + str(imageFormat)            
                    query = query + "&size=" + str(ImageWidth) + "," + str(ImageHeight)
                    query = query + "&mapScale=" + str(scale)
                    query = query + "&bbox=" + str(boundingBox[0]) + "," + str(boundingBox[1]) + "," + str(boundingBox[2]) + "," + str(boundingBox[3])

                    # If token received
                    if (token):
                        # Add token to query
                        query = query + "&token=" + token
            
                    # Make the query to the map service
                    response, downloadTime = urlQuery(query)                 

                    arcpy.AddMessage("1:" + str(scale) + " draw time - " + str(downloadTime) + "...")

                    # Add results to array
                    for eachScaleData in scaleData:
                        # If scale is already in array
                        if (str(scale) == str(eachScaleData[0])):
                            # Add results to existing array value
                            eachScaleData[1] = float(eachScaleData[1]) + float(downloadTime)

                    # If on the first query
                    if (count == 0):
                        # Add results to array
                        scaleData.append([str(scale), str(downloadTime)])
                                     
                    # Set the file path
                    file = os.path.join(arcpy.env.scratchFolder, "MapService_" + str(scale) + "." + str(imageFormat))
                    
                    # Open the file for writing
                    responseImage = open(file, "wb")

                    # Read from request while writing to file
                    responseImage.write(response)
                    responseImage.close()
                    
                count = count + 1

        arcpy.AddMessage("Downloaded images location - " + arcpy.env.scratchFolder)
                    
        # Open text file and write header line and data     
        summaryFile = open(csvFile, "w")         
                        
        if (cachedMapService == True):               
            header = "Scale,Number of Tiles Found,Number of Tiles Missing,Draw Time (Seconds)\n"
            summaryFile.write(header)
            for eachScaleData in scaleData:
                scale = eachScaleData[0]
                tileCount = eachScaleData[1]
                tileMissingCount = eachScaleData[2]
                drawTime = eachScaleData[3]
                serviceLine = str(scale) + "," + str(tileCount) + "," + str(tileMissingCount) + "," + str(round(float(drawTime)/float(numberQueries),4)) + "\n"          
                summaryFile.write(serviceLine)          
        else:
            header = "Scale,Draw Time (Seconds)\n"            
            summaryFile.write(header)
            for eachScaleData in scaleData:
                scale = eachScaleData[0]
                drawTime = eachScaleData[1]   
                serviceLine = str(scale) + "," + str(round(float(drawTime)/float(numberQueries),4)) + "\n"          
                summaryFile.write(serviceLine)
        summaryFile.close()
            
        # --------------------------------------- End of code --------------------------------------- #  
            
        # If called from gp tool return the arcpy parameter   
        if __name__ == '__main__':
            # Return the output if there is any
            if output:
                arcpy.SetParameterAsText(1, output)
        # Otherwise return the result          
        else:
            # Return the output if there is any
            if output:
                return output      
        # Logging
        if (enableLogging == "true"):
            # Log end of process
            logger.info("Process ended.")
            # Remove file handler and close log file            
            logging.FileHandler.close(logMessage)
            logger.removeHandler(logMessage)
        pass
    # If arcpy error
    except arcpy.ExecuteError:           
        # Build and show the error message
        errorMessage = arcpy.GetMessages(2)   
        arcpy.AddError(errorMessage)           
        # Logging
        if (enableLogging == "true"):
            # Log error          
            logger.error(errorMessage)
            # Log end of process
            logger.info("Process ended.")            
            # Remove file handler and close log file
            logging.FileHandler.close(logMessage)
            logger.removeHandler(logMessage)
        if (sendErrorEmail == "true"):
            # Send email
            sendEmail(errorMessage)
    # If python error
    except Exception as e:
        errorMessage = ""
        # Build and show the error message
        for i in range(len(e.args)):
            if (i == 0):
                errorMessage = unicode(e.args[i]).encode('utf-8')
            else:
                errorMessage = errorMessage + " " + unicode(e.args[i]).encode('utf-8')
        arcpy.AddError(errorMessage)              
        # Logging
        if (enableLogging == "true"):
            # Log error            
            logger.error(errorMessage)
            # Log end of process
            logger.info("Process ended.")            
            # Remove file handler and close log file
            logging.FileHandler.close(logMessage)
            logger.removeHandler(logMessage)
        if (sendErrorEmail == "true"):
            # Send email
            sendEmail(errorMessage)            
# End of main function


# Start of url query function
def urlQuery(query):
    # Make the query to the map service
    try:
        startTime = time.time()
        response = urllib2.urlopen(query).read()
    except urllib2.URLError, error:
        # If no image found
        if (error.code == 404):
            response = "Missing"
        # If any other error
        else:
            arcpy.AddError(error)
            # Logging
            if (enableLogging == "true"):
                logger.error(error)
            sys.exit()

    # If there is an error in the response
    if "error" in response:
        arcpy.AddError("Error in the query response.")
        arcpy.AddError(response)        
        # Logging
        if (enableLogging == "true"):     
            logger.error("Error in the query response.")
            logger.error(response)
        sys.exit()  
    else:
        # Get the time for the request
        endTime = time.time()
        downloadTime = endTime - startTime                            
        return response, downloadTime
# End of url query function


# Start of get token function
def getToken(username, password, serverName, serverPort):
    
    parameters = {'username':   username,
                  'password':   password,
                  'expiration': "60",
                  'client':     'requestip',
                  'f' : 'json'}
    
    parameters = urllib.urlencode(parameters)
    url = "https://{}:{}/arcgis/tokens/generateToken?".format(serverName, serverPort)
   
    try:
        response = urllib2.urlopen(url,parameters)
        # Python version check
        if sys.version_info[0] >= 3:
            # Python 3.x
            # Read json response
            responseJSON = json.loads(response.read().decode('utf8'))
        else:
            # Python 2.x
            # Read json response
            responseJSON = json.loads(response.read())
        if "token" not in responseJSON or responseJSON == None:
            arcpy.AddError("Failed to get token, return message from server:")
            arcpy.AddError(responseJSON)           
            # Logging
            if (enableLogging == "true"):   
                logger.error("Failed to get token, return message from server:")
                logger.error(responseJSON)                
            sys.exit()
        else:
            # Return the token to the function which called for it
            return responseJSON['token']
    
    except urllib2.URLError, error:
        arcpy.AddError("Could not connect to machine {} on port {}".format(serverName, serverPort))
        arcpy.AddError(error)
        # Logging
        if (enableLogging == "true"):   
            logger.error("Could not connect to machine {} on port {}".format(serverName, serverPort))
            logger.error(error)         
        sys.exit()
# End of get token function


# Start of set logging function
def setLogging(logFile):
    # Create a logger
    logger = logging.getLogger(os.path.basename(__file__))
    logger.setLevel(logging.DEBUG)
    # Setup log message handler
    logMessage = logging.FileHandler(logFile)
    # Setup the log formatting
    logFormat = logging.Formatter("%(asctime)s: %(levelname)s - %(message)s", "%d/%m/%Y - %H:%M:%S")
    # Add formatter to log message handler
    logMessage.setFormatter(logFormat)
    # Add log message handler to logger
    logger.addHandler(logMessage) 

    return logger, logMessage               
# End of set logging function


# Start of send email function
def sendEmail(message):
    # Send an email
    arcpy.AddMessage("Sending email...")
    # Server and port information
    smtpServer = smtplib.SMTP("smtp.gmail.com",587) 
    smtpServer.ehlo()
    smtpServer.starttls() 
    smtpServer.ehlo
    # Login with sender email address and password
    smtpServer.login(emailUser, emailPassword)
    # Email content
    header = 'To:' + emailTo + '\n' + 'From: ' + emailUser + '\n' + 'Subject:' + emailSubject + '\n'
    body = header + '\n' + emailMessage + '\n' + '\n' + message
    # Send the email and close the connection
    smtpServer.sendmail(emailUser, emailTo, body)    
# End of send email function


# This test allows the script to be used from the operating
# system command prompt (stand-alone), in a Python IDE, 
# as a geoprocessing script tool, or as a module imported in
# another script
if __name__ == '__main__':
    # Arguments are optional - If running from ArcGIS Desktop tool, parameters will be loaded into *argv
    argv = tuple(arcpy.GetParameterAsText(i)
        for i in range(arcpy.GetArgumentCount()))
    # Logging
    if (enableLogging == "true"):
        # Setup logging
        logger, logMessage = setLogging(logFile)
        # Log start of process
        logger.info("Process started.")
    # Setup the use of a proxy for requests
    if (enableProxy == "true"):
        # Setup the proxy
        proxy = urllib2.ProxyHandler({requestProtocol : proxyURL})
        openURL = urllib2.build_opener(proxy)
        # Install the proxy
        urllib2.install_opener(openURL)
    mainFunction(*argv)
    
