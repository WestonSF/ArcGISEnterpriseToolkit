#-------------------------------------------------------------
# Name:       ArcGIS Server Stats
# Purpose:    Generates a CSV file with statistics around how often services are being used and how well they
#             are performing in the ArcGIS server site.
# Author:     Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:    07/11/2014
# Last Updated:    13/04/2015
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
import datetime

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
def mainFunction(agsServerSite,username,password,csvFile,timeFilter): # Get parameters from ArcGIS Desktop tool by seperating by comma e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)  
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
            # If querying 1 day
            if (timeFilter.lower() == "last 24 hours"):
                millisecondsToQuery = 86400000
            # If querying 7 days
            if (timeFilter.lower() == "last week"):
                millisecondsToQuery = 604800000
            # If querying 30 days
            if (timeFilter.lower() == "last 30 days"):
                millisecondsToQuery = 2592000000

            startTime = int(round(time.time() * 1000))
            endTime = startTime - millisecondsToQuery

            # Query logs
            servicesStats = {}
            queryResult,lastRecordDate = queryLogs(serverName,serverPort,startTime,endTime,servicesStats,token)

            # While there are still more queries - More than 10,000
            while (queryResult == -1):
                # Query logs
                queryResult,lastRecordDate = queryLogs(serverName,serverPort,lastRecordDate,endTime,servicesStats,token)         

            arcpy.AddMessage("Creating CSV file with stats...")
            
            # Open text file and write header line       
            summaryFile = open(csvFile, "w")        
            header = "Service,Requests,Request Time,Draw Requests,Draw Time,Query Requests,Query Time\n"
            summaryFile.write(header)

            # Read through dictionary and write totals into file 
            for service in servicesStats:
                requestCount = servicesStats[service][0]
                requestTimeCount = servicesStats[service][1]
                avgRequestTime = 0
                
                drawCount = servicesStats[service][2]
                drawTimeCount = servicesStats[service][3]
                avgDrawTime = 0

                queryCount = servicesStats[service][4]
                queryTimeCount = servicesStats[service][5]
                avgQueryTime = 0
                
                # Get average time
                if requestCount > 0:     
                    avgRequestTime = (1.0 * (requestTimeCount / requestCount))
                if drawCount > 0:     
                    avgDrawTime = (1.0 * (drawTimeCount / drawCount))
                if queryCount > 0:     
                    avgQueryTime = (1.0 * (queryTimeCount / queryCount))                            

                # Construct and write the comma-separated line         
                serviceLine = service + "," + str(requestCount) + "," + str(avgRequestTime) + "," + str(drawCount) + "," + str(avgDrawTime) + "," + str(queryCount) + "," + str(avgQueryTime) + "\n"
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


# Start of query logs function
def queryLogs(serverName,serverPort,startTime,endTime,servicesStats,token):
    # Construct URL to query the logs
    logQueryURL = "/arcgis/admin/logs/query"
    logFilter = "{'services':'*','server':'*','machines':'*'}"          
    params = urllib.urlencode({'level': 'FINE', 'startTime': startTime, 'endTime': endTime, 'filter':logFilter, 'token': token, 'f': 'json', 'pageSize':10000})
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

    # Connect to URL and post parameters
    arcpy.AddMessage("Querying the ArcGIS Server logs...")
    arcpy.AddMessage("ArcGIS Server logs query showing from " + datetime.datetime.fromtimestamp(int(startTime) / 1000).strftime('%d/%m/%Y %H:%M:%S') + "...")
            
    httpConn = httplib.HTTPConnection(serverName, int(serverPort))
    httpConn.request("POST", logQueryURL, params, headers)
    
    # Read response
    response = httpConn.getresponse()
    if (response.status != 200):
        httpConn.close()
        arcpy.AddError("Error while querying logs.")
        # Logging
        if (enableLogging == "true"):      
            logger.error("Error while querying logs.")
        return
    else:
        data = response.read()

        # Check that data returned is not an error object
        if not assertJsonSuccess(data):
            arcpy.AddError("Error returned by operation. " + data)
            # Logging
            if (enableLogging == "true"):      
                logger.error("Error returned by operation. " + data)
        else:
            # Deserialize response into Python object
            dataObj = json.loads(data)
            httpConn.close()
            # Setup the variables       
            logs = dataObj["logMessages"]
            logCount = 0           

            # For each log message                    
            for item in logs:
                # Get request stats
                if "request successfully processed" in item["message"]:
                    serviceName = item["source"]

                    if serviceName in servicesStats:
                        # Add 1 to request count
                        servicesStats[serviceName][0] += 1
                        
                        # Add elapsed time to request time count
                        servicesStats[serviceName][1] += float(item["elapsed"])
                    else:
                        # Add key with one count and total elapsed time
                        servicesStats[serviceName] = [1,float(item["elapsed"]),0,0,0,0]
                        
                # Get draw stats
                if "End ExportMapImage" in item["message"]:
                    serviceName = item["source"]

                    if serviceName in servicesStats:
                        # Add 1 to draw count
                        servicesStats[serviceName][2] += 1
                        
                        # Add elapsed time to draw time count
                        servicesStats[serviceName][3] += float(item["elapsed"])
                    else:
                        # Add key with one count and total elapsed time
                        servicesStats[serviceName] = [0,0,1,float(item["elapsed"]),0,0]

                # Get query stats
                if ("End Query" or "End Find" or "End Identify") in item["message"]:
                    serviceName = item["source"]

                    if serviceName in servicesStats:
                        # Add 1 to query count
                        servicesStats[serviceName][4] += 1
                        
                        # Add elapsed time to draw time count
                        servicesStats[serviceName][5] += float(item["elapsed"])
                    else:
                        # Add key with one count and total elapsed time
                        servicesStats[serviceName] = [0,0,0,0,1,float(item["elapsed"])]

                # When at the last record
                if (logCount == (len(logs)-1)):
                    lastRecordDate = item["time"]
                    arcpy.AddMessage("ArcGIS Server logs query to (Last log record found to filter set) " + datetime.datetime.fromtimestamp(int(lastRecordDate) / 1000).strftime('%d/%m/%Y %H:%M:%S') + "...")
                    if (dataObj["hasMore"] == 1):
                        return -1,lastRecordDate
                    else:
                        arcpy.AddMessage("Querying finished...")
                        return 1,lastRecordDate
                logCount += 1 
# End of query logs function

      
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
    # Setup the use of a proxy for requests
    if (enableProxy == "true"):
        # Setup the proxy
        proxy = urllib2.ProxyHandler({requestProtocol : proxyURL})
        openURL = urllib2.build_opener(proxy)
        # Install the proxy
        urllib2.install_opener(openURL)
    mainFunction(*argv)
    
