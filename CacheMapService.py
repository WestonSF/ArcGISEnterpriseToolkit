#-------------------------------------------------------------
# Name:       Cache Map Service
# Purpose:    Caches a map service by either creating a new cache from scratch using a configuration file
#             or by updating an existing cache.
# Author:     Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:    04/11/2014
# Last Updated:    18/02/2015
# Copyright:   (c) Eagle Technology
# ArcGIS Version:   10.1+
# Python Version:   2.7
#--------------------------------

# Import modules
import os
import sys
import logging
import smtplib
import arcpy
import httplib
import json
import urllib
import urllib2
import urlparse
import time
import xml.etree.ElementTree as ET

# Enable data to be overwritten
arcpy.env.overwriteOutput = True

# Set variables
enableLogging = "false" # Use logger.info("Example..."), logger.warning("Example..."), logger.error("Example...")
logFile = "" # os.path.join(os.path.dirname(__file__), "Example.log")
sendErrorEmail = "false"
emailTo = ""
emailUser = ""
emailPassword = ""
emailSubject = ""
emailMessage = ""
output = None
        
# Start of main function
def mainFunction(agsServerSite,username,password,mapService,updateMode,cacheInstances,cacheConfig): # Get parameters from ArcGIS Desktop tool by seperating by comma e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)         
    try:       
        # --------------------------------------- Start of code --------------------------------------- #     
        # Get the server site details
        protocol, serverName, serverPort, context = splitSiteURL(agsServerSite)

        # If any of the variables are blank
        if (serverName == None or serverPort == None or protocol == None or context == None):
            return -1

        # Add on slash to context if necessary
        if not context.endswith('/'):
            context += '/'

        # Add on admin to context if necessary   
        if not context.endswith('admin/'):
            context += 'admin/'
            
        # Get token
        token = getToken(username, password, serverName, serverPort)

        # If token received
        if (token != -1):
            # If creating a new cache
            if (updateMode.lower() == "new"):
                arcpy.AddMessage("Creating new cache for map service - " + mapService + "...")

                # Convert config file to xml
                configFileXML = ET.parse(cacheConfig)    
                # Import and reference the configuration file
                root = configFileXML.getroot()
            
                # Get the parameters from the config
                cacheFolder = root.find("out_folder").text
                tileOrigin = root.find("tile_origin").text                
                scales = root.find("scales").text
                storageFormat = root.find("storage_format").text
                cacheFormat = root.find("cache_format").text
                tileCompressQuality = root.find("tile_compression_quality").text
                dpi = root.find("dpi").text
                tileWidth = root.find("tile_width").text
                tileHeight = root.find("tile_height").text
                useLocalCache = root.find("use_local_cache_dir").text

                # Create the cache job, which returns a job ID      
                jobID = createCache(serverName, serverPort, protocol, mapService, token, cacheFolder, tileOrigin, scales, storageFormat, cacheFormat, tileCompressQuality, dpi, tileWidth, tileHeight, useLocalCache)

                # Check job status of cache
                jobStatus, messages = checkRunningCache(serverName, serverPort, protocol, token, jobID)

                # If the job has successfully started
                if  ((jobStatus.lower() == "esrijobsubmitted") or (jobStatus.lower() == "esrijobwaiting") or (jobStatus.lower() == "esrijobexecuting") or (jobStatus.lower() == "esrijobsucceeded")):
                        arcpy.AddMessage("Map caching - Started...")
                        arcpy.AddMessage("Check Cache Status from ArcGIS Server Manager for an update on progress...")                            
                        # Logging
                        if (enableLogging == "true"):   
                            logger.info("Map caching - Started...")
                            logger.info("Check Cache Status from ArcGIS Server Manager for an update on progress...") 
                # Caching has failed
                else:
                    arcpy.AddError("Caching has failed, see service logs for more details...")
                    # Logging
                    if (enableLogging == "true"):      
                        logger.error("Caching has failed, see service logs for more details...")
     
            # If updating an existing cache
            else:
                arcpy.AddMessage("Updating cache for map service - " + mapService + "...")
                
                # Get tile info for the service
                arcpy.AddMessage("Getting cache scales...")
                scales = getTileInfo(serverName, serverPort, protocol, mapService, token)

                # If the map service is cached
                if scales:
                    # If recreating all tiles
                    if (updateMode.lower() == "existing - recreate all tiles"):
                        updateMode = "RECREATE_ALL_TILES"
                    # If recreating empty tiles
                    else:
                        updateMode = "RECREATE_EMPTY_TILES"

                    # Start the cache job, which returns a job ID                    
                    jobID = startCache(serverName, serverPort, protocol, mapService, token, scales, updateMode, cacheInstances)

                    # Check job status of cache
                    jobStatus, messages = checkRunningCache(serverName, serverPort, protocol, token, jobID)

                    # If the job has successfully started
                    if  ((jobStatus.lower() == "esrijobsubmitted") or (jobStatus.lower() == "esrijobwaiting") or (jobStatus.lower() == "esrijobexecuting") or (jobStatus.lower() == "esrijobsucceeded")):
                            arcpy.AddMessage("Map caching - Started...")
                            arcpy.AddMessage("Check Cache Status from ArcGIS Server Manager for an update on progress...")                            
                            # Logging
                            if (enableLogging == "true"):   
                                logger.info("Map caching - Started...")
                                logger.info("Check Cache Status from ArcGIS Server Manager for an update on progress...") 
                    # Caching has failed
                    else:
                        arcpy.AddError("Caching has failed, see service logs for more details...")
                        # Logging
                        if (enableLogging == "true"):      
                            logger.error("Caching has failed, see service logs for more details...")                             
                        
                # If this is not a cached map service
                else:
                    arcpy.AddError(mapService + " is not a cached map service. Please select a cached map service or select the \"New\" update mode.")        
                    # Logging
                    if (enableLogging == "true"):   
                        logger.error(mapService + " is not a cached map service. Please select a cached map service or select the \"New\" update mode.") 
                       

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


# Start of get tile info function
def getTileInfo(serverName, serverPort, protocol, mapService, token):
    params = urllib.urlencode({'token': token, 'f': 'json'})
            
    # Construct URL to get the service tile info
    url = "/arcgis/rest/services/" + mapService + "/MapServer"

    # Post to the server
    try:
        response, data = postToServer(serverName, serverPort, protocol, url, params)
    except:
        arcpy.AddError("Unable to connect to the ArcGIS Server site on " + serverName + ". Please check if the server is running.")
        # Logging
        if (enableLogging == "true"):      
            logger.error("Unable to connect to the ArcGIS Server site on " + serverName + ". Please check if the server is running.")
            sys.exit()
        return -1

    # If there is an error
    if (response.status != 200):
        arcpy.AddError("Error getting map service tile info.")
        arcpy.AddError(str(data))
        # Logging
        if (enableLogging == "true"):     
            logger.error("Error getting map service tile info.")
            sys.exit()
        return -1
    if (not assertJsonSuccess(data)):
        arcpy.AddError("Error getting map service tile info. Please check if the server is running and ensure that the username/password provided are correct.")
        # Logging
        if (enableLogging == "true"):      
            logger.error("Error getting map service tile info. Please check if the server is running and ensure that the username/password provided are correct.")  
            sys.exit()
        return -1
    # On successful query
    else: 
        dataObject = json.loads(data)
        scales = ""

        # If the map service is cached
        if "tileInfo" in dataObject:
            # Iterate through the scales
            count = 0
            for scale in dataObject['tileInfo']['lods']:
                # Add each of the scales to the array
                if (count > 0):
                    scales = scales + ";"
                scales = scales + str(scale['scale'])
                count = count + 1             
            return scales
            
        # Not cached map service
        else:
            return None
# End of get tile info function


# Start of create cache function
def createCache(serverName, serverPort, protocol, mapService, token, cacheFolder, tileOrigin, scales, storageFormat, cacheFormat, tileCompressQuality, dpi, tileWidth, tileHeight, useLocalCache):
    params = urllib.urlencode({'service_url': mapService + ":MapServer",
                               'out_folder': cacheFolder,
                               'tile_origin': tileOrigin,
                               'levels': scales,
                               'storage_format': storageFormat,
                               'cache_format': cacheFormat,
                               'tile_compression_quality': tileCompressQuality,
                               'dpi': dpi,
                               'tile_width': tileWidth,
                               'tile_height': tileHeight,
                               'use_local_cache_dir': useLocalCache,
                               'token': token,
                               'f': 'json'})
                
    # Construct URL to start the updating of the cache
    url = "/arcgis/rest/services/System/CachingTools/GPServer/Create Map Cache/submitJob"

    # Post to the server
    try:
        response, data = postToServer(serverName, serverPort, protocol, url, params)
    except:
        arcpy.AddError("Error creating map service cache on " + serverName + ". Please check if the server is running.")
        # Logging
        if (enableLogging == "true"):      
            logger.error("Error creating map service cache on " + serverName + ". Please check if the server is running.")
            sys.exit()
        return -1

    # If there is an error
    if (response.status != 200):
        arcpy.AddError("Error creating map service cache.")
        arcpy.AddError(str(data))
        # Logging
        if (enableLogging == "true"):     
            logger.error("Error creating map service cache.")
            sys.exit()
        return -1
    if (not assertJsonSuccess(data)):
        arcpy.AddError("Error creating map service cache. Please check if the server is running and ensure that the username/password provided are correct.")
        # Logging
        if (enableLogging == "true"):      
            logger.error("Error creating map service cache. Please check if the server is running and ensure that the username/password provided are correct.")  
            sys.exit()
        return -1
    # On successful query
    else:
        dataObject = json.loads(data)
        jobStatus = dataObject['jobStatus']
        jobID = dataObject['jobId']

        # If the job has been succesfully submitted 
        if (jobStatus.lower() == "esrijobsubmitted"): 
            return jobID
        # If there is an error
        else:
            arcpy.AddError("Error creating the map service cache.")
            arcpy.AddError(str(dataObject))
            # Logging
            if (enableLogging == "true"):     
                logger.error("Error creating the map service cache.")
                logger.error(str(dataObject))
                sys.exit()
            return -1               
# End of create cache function


# Start of start cache function
def startCache(serverName, serverPort, protocol, mapService, token, scales, updateMode, cacheInstances):
    params = urllib.urlencode({'service_url': mapService + ":MapServer",
                               'levels': scales,
                               'thread_count': cacheInstances,
                               'update_mode': updateMode,
                               'token': token,
                               'f': 'json'})
            
    # Construct URL to start the updating of the cache
    url = "/arcgis/rest/services/System/CachingTools/GPServer/Manage Map Cache Tiles/submitJob"

    # Post to the server
    try:
        response, data = postToServer(serverName, serverPort, protocol, url, params)
    except:
        arcpy.AddError("Error updating map service cache on " + serverName + ". Please check if the server is running.")
        # Logging
        if (enableLogging == "true"):      
            logger.error("Error updating map service cache on " + serverName + ". Please check if the server is running.")
            sys.exit()
        return -1

    # If there is an error
    if (response.status != 200):
        arcpy.AddError("Error updating map service cache.")
        arcpy.AddError(str(data))
        # Logging
        if (enableLogging == "true"):     
            logger.error("Error updating map service cache.")
            sys.exit()
        return -1
    if (not assertJsonSuccess(data)):
        arcpy.AddError("Error updating map service cache. Please check if the server is running and ensure that the username/password provided are correct.")
        # Logging
        if (enableLogging == "true"):      
            logger.error("Error updating map service cache. Please check if the server is running and ensure that the username/password provided are correct.")  
            sys.exit()
        return -1
    # On successful query
    else:
        dataObject = json.loads(data)
        jobStatus = dataObject['jobStatus']
        jobID = dataObject['jobId']

        # If the job has been succesfully submitted 
        if (jobStatus.lower() == "esrijobsubmitted"): 
            return jobID
        # If there is an error
        else:
            arcpy.AddError("Error starting the map service cache.")
            arcpy.AddError(str(dataObject))
            # Logging
            if (enableLogging == "true"):     
                logger.error("Error starting the map service cache.")
                logger.error(str(dataObject))
                sys.exit()
            return -1               
# End of start cache function


# Start of check cache creation function
def checkCreateCache(serverName, serverPort, protocol, token, jobID): 
    params = urllib.urlencode({'token': token,
                               'f': 'json'})
            
    # Construct URL to start the updating of the cache
    url = "/arcgis/rest/services/System/CachingTools/GPServer/Create Map Cache/jobs/" + jobID

    # Post to the server
    try:
        response, data = postToServer(serverName, serverPort, protocol, url, params)
    except:
        arcpy.AddError("Error checking map service cache creation on " + serverName + ". Please check if the server is running.")
        # Logging
        if (enableLogging == "true"):      
            logger.error("Error checking map service cache creation on " + serverName + ". Please check if the server is running.")
            sys.exit()
        return -1

    # If there is an error
    if (response.status != 200):
        arcpy.AddError("Error checking map service cache creation.")
        arcpy.AddError(str(data))
        # Logging
        if (enableLogging == "true"):     
            logger.error("Error checking map service cache creation.")
            sys.exit()
        return -1
    if (not assertJsonSuccess(data)):
        arcpy.AddError("Error checking map service cache creation. Please check if the server is running and ensure that the username/password provided are correct.")
        # Logging
        if (enableLogging == "true"):      
            logger.error("Error checking map service cache creation. Please check if the server is running and ensure that the username/password provided are correct.")  
            sys.exit()
        return -1
    # On successful query
    else:
        dataObject = json.loads(data)
        jobStatus = dataObject['jobStatus']
        messages = dataObject['messages']
        
        return jobStatus, messages
# End of check cache creation function


# Start of check running cache function
def checkRunningCache(serverName, serverPort, protocol, token, jobID):
    params = urllib.urlencode({'token': token,
                               'f': 'json'})
            
    # Construct URL to start the updating of the cache
    url = "/arcgis/rest/services/System/CachingTools/GPServer/Manage Map Cache Tiles/jobs/" + jobID

    # Post to the server
    try:
        response, data = postToServer(serverName, serverPort, protocol, url, params)
    except:
        arcpy.AddError("Error checking map service cache on " + serverName + ". Please check if the server is running.")
        # Logging
        if (enableLogging == "true"):      
            logger.error("Error checking map service cache on " + serverName + ". Please check if the server is running.")
            sys.exit()
        return -1

    # If there is an error
    if (response.status != 200):
        arcpy.AddError("Error checking map service cache.")
        arcpy.AddError(str(data))
        # Logging
        if (enableLogging == "true"):     
            logger.error("Error checking map service cache.")
            sys.exit()
        return -1
    if (not assertJsonSuccess(data)):
        arcpy.AddError("Error checking map service cache. Please check if the server is running and ensure that the username/password provided are correct.")
        # Logging
        if (enableLogging == "true"):      
            logger.error("Error checking map service cache. Please check if the server is running and ensure that the username/password provided are correct.")  
            sys.exit()
        return -1
    # On successful query
    else:
        dataObject = json.loads(data)
        jobStatus = dataObject['jobStatus']
        messages = dataObject['messages']
        
        return jobStatus, messages
# End of check running cache function


# Start of get token function
def getToken(username, password, serverName, serverPort):
    query_dict = {'username':   username,
                  'password':   password,
                  'expiration': "60",
                  'client':     'requestip'}
    
    query_string = urllib.urlencode(query_dict)
    url = "http://{}:{}/arcgis/admin/generateToken?f=json".format(serverName, serverPort)
   
    try:
        token = json.loads(urllib2.urlopen(url, query_string).read())
        if "token" not in token or token == None:
            arcpy.AddError("Failed to get token, return message from server:")
            arcpy.AddError(token['messages'])            
            # Logging
            if (enableLogging == "true"):   
                logger.error("Failed to get token, return message from server:")
                logger.error(token['messages'])                
            sys.exit()
        else:
            # Return the token to the function which called for it
            return token['token']
    
    except urllib2.URLError, error:
        arcpy.AddError("Could not connect to machine {} on port {}".format(serverName, serverPort))
        arcpy.AddError(error)
        # Logging
        if (enableLogging == "true"):   
            logger.error("Could not connect to machine {} on port {}".format(serverName, serverPort))
            logger.error(error)         
        sys.exit()
# End of get token function


# Start of HTTP POST request to the server function
def postToServer(serverName, serverPort, protocol, url, params):
    # If on standard port
    if (serverPort == -1 and protocol == 'http'):
        serverPort = 80

    # If on secure port
    if (serverPort == -1 and protocol == 'https'):
        serverPort = 443
        
    if (protocol == 'http'):
        httpConn = httplib.HTTPConnection(serverName, int(serverPort))

    if (protocol == 'https'):
        httpConn = httplib.HTTPSConnection(serverName, int(serverPort))
        
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain",'referer':'backuputility','referrer':'backuputility'}
     
    # URL encode the resource URL
    url = urllib.quote(url.encode('utf-8'))

    # Build the connection to add the roles to the server
    httpConn.request("POST", url, params, headers) 

    response = httpConn.getresponse()
    data = response.read()

    httpConn.close()

    # Return response
    return (response, data)
# End of HTTP POST request to the server function


# Start of split URL function 
def splitSiteURL(siteURL):     
    try:
        serverName = ''
        serverPort = -1
        protocol = 'http'
        context = '/arcgis'
        # Split up the URL provided
        urllist = urlparse.urlsplit(siteURL)
        # Put the URL list into a dictionary
        d = urllist._asdict()

        # Get the server name and port
        serverNameAndPort = d['netloc'].split(":")

        # User did not enter the port number, so we return -1
        if (len(serverNameAndPort) == 1):
            serverName = serverNameAndPort[0]
        else:
            if (len(serverNameAndPort) == 2):
                serverName = serverNameAndPort[0]
                serverPort = serverNameAndPort[1]

        # Get protocol
        if (d['scheme'] is not ''):
            protocol = d['scheme']

        # Get path
        if (d['path'] is not '/' and d['path'] is not ''):
            context = d['path']

        # Return variables
        return protocol, serverName, serverPort, context  
    except:
        arcpy.AddError("The ArcGIS Server site URL should be in the format http(s)://<host>:<port>/arcgis")
        # Logging
        if (enableLogging == "true"):      
            logger.error("The ArcGIS Server site URL should be in the format http(s)://<host>:<port>/arcgis")
            sys.exit()
        return None, None, None, None
# End of split URL function


# Start of status check JSON object function
def assertJsonSuccess(data):
    obj = json.loads(data)
    if 'status' in obj and obj['status'] == "error":
        if ('messages' in obj):
            errMsgs = obj['messages']
            for errMsg in errMsgs:
                arcpy.AddError(errMsg)
                # Logging
                if (enableLogging == "true"):      
                    logger.error(errMsg)
            sys.exit()
        return False
    else:
        return True
# End of status check JSON object function


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
    mainFunction(*argv)