#-------------------------------------------------------------
# Name:       Map Service Monitor
# Purpose:    Checks a map service for instance usage and performance.
#             This tool should be setup as an automated task on the server.
#             - Needs to be run as administrator.
#             - Need to install WMI python package.
# Author:     Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:    11/08/2015
# Last Updated:    14/08/2015
# Copyright:   (c) Eagle Technology
# ArcGIS Version:   10.3+
# Python Version:   2.7
#--------------------------------

# Import modules
import os
import sys
import logging
import smtplib
import httplib
import arcpy
import string
import urllib
import urllib2
import datetime
import json
import math
import urlparse
import wmi
        
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
def mainFunction(agsServerSite,username,password,service,csvFile): # Get parameters from ArcGIS Desktop tool by seperating by comma e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)  
    try:
        # --------------------------------------- Start of code --------------------------------------- #

        arcpy.AddMessage("Connecting to ArcGIS Server...")

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
            # Get service info
            serviceInfo = getServiceInfo(serverName, serverPort, protocol, service, token)
            minInstances = serviceInfo['minInstancesPerNode']
            maxInstances = serviceInfo['maxInstancesPerNode']

            # Get service stats                        
            serviceStats = getServiceStats(serverName, serverPort, protocol, service, token)    
            busyInstances = serviceStats['summary']['busy']
            freeInstances = serviceStats['summary']['free']
            initializingInstances = serviceStats['summary']['initializing']             
            notCreatedInstances = serviceStats['summary']['notCreated']   
            runningInstances = maxInstances - notCreatedInstances

            arcpy.AddMessage(service + " has " + str(minInstances) + " set for minimum instances...")
            arcpy.AddMessage(service + " has " + str(maxInstances) + " set for maximum instances...")            
            arcpy.AddMessage(service + " has " + str(runningInstances) + " instances currently running...")


            # Get memory information
            memoryUsage = 0
            windowsTasks = wmi.WMI()
            for process in windowsTasks.Win32_Process():
              # Find the map service ArcSOCs
              if (process.Name == "ArcSOC.exe"):
                  if (service.replace("/", ".") in process.CommandLine):
                      for processDetail in windowsTasks.Win32_PerfRawData_PerfProc_Process():
                          if (processDetail.IDProcess == process.ProcessId):
                              # Private memory for the process
                              memoryUsage = float(memoryUsage) + float(processDetail.WorkingSetPrivate)        

            arcpy.AddMessage("Memory usage " + str(round(float(memoryUsage)/float(1048576),2)) + " MB...")  
        
            # If the csv file already exists 
            if os.path.isfile(csvFile):
                arcpy.AddMessage("Appending to existing file - " + csvFile + "...")
                # Open csv file for appending
                mapServiceFile = open(csvFile, "a")                   
            else:
                arcpy.AddMessage("Creating new file - " + csvFile + "...")                
                # Open csv file and write header line  
                mapServiceFile = open(csvFile, "w")         
                header = "Time,Min Instances,Max Instances,Running Instances,Memory Usage (MB)\n"
                mapServiceFile.write(header)

            # Get the time/date
            setDateTime = datetime.datetime.now()
            currentDateTime = setDateTime.strftime("%d/%m/%Y - %H:%M:%S")

            # Write the instance details
            instanceDetails = str(currentDateTime) + "," + str(minInstances) + "," + str(maxInstances) + "," + str(runningInstances) + "," + str(round(float(memoryUsage)/float(1048576),2)) + "\n"          
            mapServiceFile.write(instanceDetails)

            mapServiceFile.close()
        
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


# Start of get service info function
def getServiceInfo(serverName, serverPort, protocol, service, token):
    params = urllib.urlencode({'token': token, 'f': 'json'})

    # Construct URL to get the service status
    url = "/arcgis/admin/services/" + service

    # Post to the server
    try:      
        response, data = postToServer(serverName, serverPort, protocol, url, params)
    except:
        arcpy.AddError("Unable to connect to the ArcGIS Server site on " + serverName + ". Check if the server is running.")
        # Logging
        if (enableLogging == "true"):     
            logger.error("Unable to connect to the ArcGIS Server site on " + serverName + ". Check if the server is running.")
        return -1

    # If there is an error
    if (response.status != 200):
        arcpy.AddError("Error getting service status.")
        # Logging
        if (enableLogging == "true"):    
            logger.error("Error getting service status.")
        arcpy.AddError(str(data))
        return -1
    if (not assertJsonSuccess(data)):
        arcpy.AddError("Error getting service status. Check if the server is running and ensure that the username/password provided are correct.")
        # Logging
        if (enableLogging == "true"):  
            logger.error("Error getting service status. Check if the server is running and ensure that the username/password provided are correct.")
        return -1
    # On successful query
    else: 
        dataObject = json.loads(data)     
        return dataObject
# End of get service info function


# Start of get service stats function
def getServiceStats(serverName, serverPort, protocol, service, token):
    params = urllib.urlencode({'token': token, 'f': 'json'})

    # Construct URL to get the service status
    url = "/arcgis/admin/services/" + service + "/statistics"

    # Post to the server
    try:      
        response, data = postToServer(serverName, serverPort, protocol, url, params)
    except:
        arcpy.AddError("Unable to connect to the ArcGIS Server site on " + serverName + ". Check if the server is running.")
        # Logging
        if (enableLogging == "true"):     
            logger.error("Unable to connect to the ArcGIS Server site on " + serverName + ". Check if the server is running.")
        return -1

    # If there is an error
    if (response.status != 200):
        arcpy.AddError("Error getting service status.")
        # Logging
        if (enableLogging == "true"):    
            logger.error("Error getting service status.")
        arcpy.AddError(str(data))
        return -1
    if (not assertJsonSuccess(data)):
        arcpy.AddError("Error getting service status. Check if the server is running and ensure that the username/password provided are correct.")
        # Logging
        if (enableLogging == "true"):  
            logger.error("Error getting service status. Check if the server is running and ensure that the username/password provided are correct.")
        return -1
    # On successful query
    else: 
        dataObject = json.loads(data)     
        return dataObject
# End of get service stats function


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
        return None, None, None, None
# End of split URL function


# Start of status check JSON object function
def assertJsonSuccess(data):
    try:
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
    except ValueError, e:
        return False
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
    # Setup the use of a proxy for requests
    if (enableProxy == "true"):
        # Setup the proxy
        proxy = urllib2.ProxyHandler({requestProtocol : proxyURL})
        openURL = urllib2.build_opener(proxy)
        # Install the proxy
        urllib2.install_opener(openURL)
    mainFunction(*argv)
    
