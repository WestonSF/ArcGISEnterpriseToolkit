#-------------------------------------------------------------
# Name:       ArcGIS Application Test
# Purpose:    Tests an ArcGIS web application (that uses a web map) for performance.
#             - Need to install requests python package.
# Author:     Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:    22/07/2016
# Last Updated:    22/07/2016
# Copyright:   (c) Eagle Technology
# ArcGIS Version:   ArcMap 10.4+ or ArcGIS Pro 1.1+ (Need to be signed into a portal site)
# Python Version:   2.7 or 3.4
#--------------------------------

# Import main modules
import os
import sys
import logging
import smtplib

# Set global variables
# Logging
enableLogging = "false" # Use within code - logger.info("Example..."), logger.warning("Example..."), logger.error("Example...") and to print messages - printMessage("xxx","info"), printMessage("xxx","warning"), printMessage("xxx","error")
logFile = "" # e.g. os.path.join(os.path.dirname(__file__), "Example.log")
# Email logging
sendErrorEmail = "false"
emailServerName = "" # e.g. smtp.gmail.com
emailServerPort = 0 # e.g. 25
emailTo = ""
emailUser = ""
emailPassword = ""
emailSubject = ""
emailMessage = ""
# Proxy
enableProxy = "false"
requestProtocol = "http" # http or https
proxyURL = ""
# Output
output = None
# ArcGIS desktop installed
arcgisDesktop = "true"

# If ArcGIS desktop installed
if (arcgisDesktop == "true"):
    # Import extra modules
    import arcpy
    # Enable data to be overwritten
    arcpy.env.overwriteOutput = True
# Python version check
if sys.version_info[0] >= 3:
    # Python 3.x
    import urllib.request as urllib2
else:
    # Python 2.x
    import urllib2  
import urllib
import json
import csv
import requests


# Start of main function
def mainFunction(portalUrl, portalAdminName, portalAdminPassword, webmapId, applicationId, javascriptAPIURL, csvFile): # Get parameters from ArcGIS Desktop tool by seperating by comma e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)  
    try:
        # --------------------------------------- Start of code --------------------------------------- #
        
        printMessage("Connecting to Portal - " + portalUrl + "...","info")
        # Generate token for portal
        token = generateToken(portalAdminName, portalAdminPassword, portalUrl)

        # Setup the requests needed
        webRequests = []
        webRequests.append(javascriptAPIURL + "/init.js")
        webRequests.append(portalUrl + "/sharing/rest/portals/self?f=json&token=" + token)
        webRequests.append(portalUrl + "/sharing/rest/content/items/" + webmapId + "/data?f=json&token=" + token)
        webRequests.append(portalUrl + "/sharing/rest/content/items/" + applicationId + "/data?f=json&token=" + token)

        # Get all the service requests needed from the webmap
        printMessage("Retrieving all services from the web map - " + webmapId + "...","info")
        serviceRequests = servicesWebmap(portalUrl,token,webmapId)
        for servicesRequest in serviceRequests:
            webRequests.append(servicesRequest)

        printMessage("Creating report CSV file - " + csvFile + "...","info")
        # Create a CSV file and setup header
        file = open(csvFile, 'wb')
        writer = csv.writer(file, delimiter=",")

        # Add in header information   
        headerRow = []                               
        headerRow.append("Request")
        headerRow.append("Time (Seconds)")
        writer.writerow(headerRow)
        
        # Make all the web requests needed
        totalRequestTime = 0
        for request in webRequests:
            printMessage("Making web request - " + request + "...","info")
            time = webRequest(request)
            totalRequestTime = totalRequestTime + float(time.microseconds)
            printMessage("Time - " + str(round(float(time.microseconds)/1000000,4)) + "...","info")

            # Write results to CSV
            row = []                               
            row.append(request)
            row.append(str(round(float(time.microseconds)/1000000,4)))
            writer.writerow(row)
                
        printMessage("Total request time - " + str(round(totalRequestTime/1000000,4)) + "...","info")
            
        # --------------------------------------- End of code --------------------------------------- #
        # If called from gp tool return the arcpy parameter   
        if __name__ == '__main__':
            # Return the output if there is any
            if output:
                # If ArcGIS desktop installed
                if (arcgisDesktop == "true"):
                    arcpy.SetParameter(1, output)
                # ArcGIS desktop not installed
                else:
                    return output 
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
            logMessage.flush()
            logMessage.close()
            logger.handlers = []
    # If arcpy error
    except arcpy.ExecuteError:           
        # Build and show the error message
        errorMessage = arcpy.GetMessages(2)   
        printMessage(errorMessage,"error")           
        # Logging
        if (enableLogging == "true"):
            # Log error          
            logger.error(errorMessage)
            # Log end of process
            logger.info("Process ended.")            
            # Remove file handler and close log file        
            logMessage.flush()
            logMessage.close()
            logger.handlers = []   
        if (sendErrorEmail == "true"):
            # Send email
            sendEmail(errorMessage)
    # If python error
    except Exception as e:
        errorMessage = ""         
        # Build and show the error message
        # If many arguments
        if (e.args):
            for i in range(len(e.args)):        
                if (i == 0):
                    # Python version check
                    if sys.version_info[0] >= 3:
                        # Python 3.x
                        errorMessage = str(e.args[i]).encode('utf-8').decode('utf-8')
                    else:
                        # Python 2.x
                        errorMessage = unicode(e.args[i]).encode('utf-8')
                else:
                    # Python version check
                    if sys.version_info[0] >= 3:
                        # Python 3.x
                        errorMessage = errorMessage + " " + str(e.args[i]).encode('utf-8').decode('utf-8')
                    else:
                        # Python 2.x
                        errorMessage = errorMessage + " " + unicode(e.args[i]).encode('utf-8')
        # Else just one argument
        else:
            errorMessage = e
        printMessage(errorMessage,"error")
        # Logging
        if (enableLogging == "true"):
            # Log error            
            logger.error(errorMessage)
            # Log end of process
            logger.info("Process ended.")            
            # Remove file handler and close log file        
            logMessage.flush()
            logMessage.close()
            logger.handlers = []   
        if (sendErrorEmail == "true"):
            # Send email
            sendEmail(errorMessage)            
# End of main function


# Start of web request function
def webRequest(url):
    # Make the request
    response = requests.get(url)
    # Return the load time
    return response.elapsed
# End of web request function


# Start of services in web map function
def servicesWebmap(portalUrl,token,webmap):
    # Setup parameters for web map query
    dict = {}
    dict['f'] = 'json'
    dict['token'] = token
    # Python version check
    if sys.version_info[0] >= 3:
        # Python 3.x
        # Encode parameters
        params = urllib.parse.urlencode(dict)
    else:
        # Python 2.x
        # Encode parameters
        params = urllib.urlencode(dict)
    params = params.encode('utf-8')

    # POST the request - web map query
    requestURL = urllib2.Request(portalUrl + "/sharing/rest/content/items/" + webmap + "/data",params)
    response = urllib2.urlopen(requestURL)
    # Python version check
    if sys.version_info[0] >= 3:
        # Python 3.x
        # Read json response
        responseJSON = json.loads(response.read().decode('utf8'))
    else:
        # Python 2.x
        # Read json response
        responseJSON = json.loads(response.read())

    # Log results
    if "error" in responseJSON:
        errDict = responseJSON['error']
        message =  "Error Code: %s \n Message: %s" % (errDict['code'],
        errDict['message'])
        printMessage(message,"error")
    else:
        # Setup the dictionary to return
        services = []

        # For each of the operational layers returned
        for operationalLayer in responseJSON["operationalLayers"]:
            # If URL to service
            if ("url" in operationalLayer):
                # Append data into array
                services.append(operationalLayer["url"] + "/data?f=json")

        # For each of the basemap layers returned
        for basemap in responseJSON["baseMap"]["baseMapLayers"]:
            # If URL to service
            if ("url" in basemap):       
                # If URL to service
                services.append(basemap["url"] + "/data?f=json")

        # Return dictionary
        return services     
# End of services in web map function


# Start of get token function
def generateToken(username, password, portalUrl):
    '''Retrieves a token to be used with API requests.'''
    parameters = urllib.urlencode({'username' : username,
                                   'password' : password,
                                   'client' : 'referer',
                                   'referer': portalUrl,
                                   'expiration': 60,
                                   'f' : 'json'})
    try:
        response = urllib2.urlopen(portalUrl + '/sharing/rest/generateToken?',
                              parameters).read()     
    except Exception as e:
        arcpy.AddError( 'Unable to open the url %s/sharing/rest/generateToken' % (portalUrl))
        arcpy.AddError(e)
    responseJSON =  json.loads(response.strip(' \t\n\r'))
    # Log results
    if responseJSON.has_key('error'):
        errDict = responseJSON['error']
        if int(errDict['code'])==498:
            message = 'Token Expired. Getting new token... '
            token = generateToken(username,password, portalUrl)
        else:
            message =  'Error Code: %s \n Message: %s' % (errDict['code'],
            errDict['message'])
            arcpy.AddError(message)
    token = responseJSON.get('token')
    return token
# End of get token function


# Start of print message function
def printMessage(message,type):
    # If ArcGIS desktop installed
    if (arcgisDesktop == "true"):
        if (type.lower() == "warning"):
            arcpy.AddWarning(message)
        elif (type.lower() == "error"):
            arcpy.AddError(message)
        else:
            arcpy.AddMessage(message)
    # ArcGIS desktop not installed
    else:
        print(message)
# End of print message function


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
    printMessage("Sending email...","info")
    # Server and port information
    smtpServer = smtplib.SMTP(emailServerName,emailServerPort) 
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
    # Test to see if ArcGIS desktop installed
    if ((os.path.basename(sys.executable).lower() == "arcgispro.exe") or (os.path.basename(sys.executable).lower() == "arcmap.exe") or (os.path.basename(sys.executable).lower() == "arccatalog.exe")):
        arcgisDesktop = "true"
        
    # If ArcGIS desktop installed
    if (arcgisDesktop == "true"):
        argv = tuple(arcpy.GetParameterAsText(i)
            for i in range(arcpy.GetArgumentCount()))
    # ArcGIS desktop not installed
    else:
        argv = sys.argv
        # Delete the first argument, which is the script
        del argv[0] 
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
