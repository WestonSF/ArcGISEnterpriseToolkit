#-------------------------------------------------------------
# Name:       ArcGIS Server Availability 
# Purpose:    Checks ArcGIS server site and services and reports if site is down and/or particular
#             service is down. This tool should be setup as an automated task on the server.       
# Author:     Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:    07/02/2014
# Last Updated:    19/03/2019
# Copyright:   (c) Eagle Technology
# ArcGIS Version:   ArcMap (ArcPy) 10.1+
# Python Version:   2.7
#--------------------------------

# Import main modules
import os
import sys
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import email.mime.application
# Import ArcGIS modules
useArcPy = "true"
useArcGISAPIPython = "false"
if (useArcPy == "true"):
    # Import arcpy module
    import arcpy
    # Enable data to be overwritten
    arcpy.env.overwriteOutput = True
if (useArcGISAPIPython == "true"):
    # Import arcgis module
    import arcgis
import urllib
import urllib2
import ssl
import json

# Set global variables
# Logging
enableLogging = "true" # Use within code to print and log messages - printMessage("xxx","info"), printMessage("xxx","warning"), printMessage("xxx","error")
logFile = os.path.join(os.path.dirname(__file__), "ArcGISServerAvailability.log") # e.g. os.path.join(os.path.dirname(__file__), "Example.log")
# Email Use within code to send email - sendEmail(message,attachment)
sendErrorEmail = "false"
emailServerName = "" # e.g. smtp.gmail.com
emailServerPort = 25 # e.g. 25
emailSubject = "" # Subject in email
emailTo = "" # Address of email sent to
emailUser = "" # Address of email sent from
emailPassword = ""
# Proxy
enableProxy = "false"
requestProtocol = "http" # http or https
proxyURL = ""
# Output
output = None


# Start of main function
def mainFunction(agsSiteURL,agsSiteAdminURL,portalURL,portalUsername,portalPassword,service,errorStoppedServices): # Add parameters sent to the script here e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter) 
    try:
        # --------------------------------------- Start of code --------------------------------------- #

        # Get token
        token = getToken(portalURL, portalUsername, portalPassword)

        # If token received (If no response the script will stop and error in the getToken function)
        if (token):
            # Check ArcGIS Server site directory
            agsVersion = checkAGSSite(agsSiteURL, token)
            # If response (If no response the script will stop and error in the checkAGSSite function)
            if (agsVersion):
                printMessage("ArcGIS Server site " + agsSiteURL + " is running correctly on version " + str(agsVersion) + "...","info")

                # List to hold services and their status
                servicesInfo = []
                
                # If a service is provided
                if (service):
                    services = []
                    services.append(service)
                else:
                    # Get all services (If no response the script will stop and error in the getServices function)
                    services = getServices(agsSiteAdminURL, token)

                # Query all services
                # Iterate through services
                for eachService in services:
                    # Get the service status
                    realtimeStatus = getServiceStatus(agsSiteAdminURL, token, eachService)          
                    # Check the service endpoint
                    serviceInfo = checkService(agsSiteURL, token, eachService)
                    # Query the service if map or feature service
                    if ((eachService.split(".")[-1].lower() == "mapserver") or (eachService.split(".")[-1].lower() == "featureserver")):
                        queryResultCount = queryService(agsSiteURL, serviceInfo, token, eachService)
                    else:
                        queryResultCount = None
                    # Add service info to list
                    servicesInfo.append({'service': eachService, 'status': realtimeStatus, 'info': serviceInfo, 'queryInfo': queryResultCount})

                runningServices = 0
                stoppedServices = 0
                errorServices = 0
                queryErrorServices = 0
                errorMessages = []
                # Iterate through services info dictionary
                for serviceInfo in servicesInfo:
                    # If service is stopped
                    if "stopped" in str(serviceInfo["status"]).lower():
                        stoppedServices += 1
                        # If checking for stopped services or single service provided
                        if ((errorStoppedServices.lower() == "true") or (service)):
                            errorMessages.append(serviceInfo["service"] + " - " + "Service is stopped...")                            
                    # If service started
                    else:
                        runningServices += 1
                        # If error in result
                        if "error" in str(serviceInfo["info"]).lower():
                            errorMessages.append(serviceInfo["service"] + " - " + str(serviceInfo["info"]))
                            errorServices += 1
                        # If error in result
                        if "error" in str(serviceInfo["queryInfo"]).lower():
                            errorMessages.append(serviceInfo["service"] + " - " + str(serviceInfo["queryInfo"]))
                            queryErrorServices += 1

                # If a service is provided
                if (service):
                    # If any errors
                    if (len(errorMessages) > 0):
                        # For each error message
                        for errorMessage in errorMessages:
                            printMessage(errorMessage,"error")

                        if (sendErrorEmail == "true"):
                            message = "There is an issue with one or more services on the ArcGIS Server site - " + agsSiteURL + "..." + "<br/><br/>"
                            for errorMessage in errorMessages:
                                message += errorMessage + "<br/>"
                            # Send email
                            sendEmail(message,None)                            
                    else:
                        printMessage(service + " is running correctly...","info")  
                else:
                    printMessage(str(runningServices) + " services are running...","info")
                    printMessage(str(stoppedServices) + " services are stopped...","info")
                    printMessage(str(errorServices) + " services have errors...","info")
                    printMessage(str(queryErrorServices) + " map or feature services have data errors...","info")
                    # If any errors
                    if (len(errorMessages) > 0):
                        # For each error message
                        for errorMessage in errorMessages:
                            printMessage(errorMessage,"error")

                        if (sendErrorEmail == "true"):
                            message = "There is an issue with one or more services on the ArcGIS Server site - " + agsSiteURL + "..." + "<br/><br/>"
                            message += str(runningServices) + " services are running..." + "<br/>"
                            message += str(stoppedServices) + " services are stopped..." + "<br/>"
                            message += str(errorServices) + " services have errors..." + "<br/>"
                            message += str(queryErrorServices) + " map or feature services have data errors..." + "<br/><br/>"
                            for errorMessage in errorMessages:
                                message += errorMessage + "<br/>"
                            # Send email
                            sendEmail(message,None)   
                    else:
                        printMessage("All services are running correctly...","info")  

        # --------------------------------------- End of code --------------------------------------- #  
            
        # If called from ArcGIS GP tool
        if __name__ == '__main__':
            # Return the output if there is any
            if output:
                # If using ArcPy
                if (useArcPy == "true"):
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
    # If error
    except Exception as e:
        # Build and show the error message
        # errorMessage = arcpy.GetMessages(2)

        errorMessage = ""
        # Build and show the error message
        # If many arguments
        if (e.args):
            for i in range(len(e.args)):
                if (i == 0):
                    errorMessage = str(e.args[i]).encode('utf-8').decode('utf-8')
                else:
                    errorMessage = errorMessage + " " + str(e.args[i]).encode('utf-8').decode('utf-8')
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
            sendEmail(errorMessage,None)
# End of main function


# Start of check AGS site function
def checkAGSSite(agsSiteURL, token):
    # Setup the parameters
    parameters = urllib.urlencode({'token': token,
                  'f': 'json'})
    queryString = parameters.encode('utf-8')

    # Post request
    try:
        printMessage("Querying ArcGIS Server - " + agsSiteURL + "/rest/services" + "...","info") 
        context = ssl._create_unverified_context()
        request = urllib2.Request(agsSiteURL + "/rest/services",queryString)
        responseJSON = json.loads(urllib2.urlopen(request, context=context).read())
        if "error" in str(responseJSON).lower():
            printMessage("There is an issue with the ArcGIS Server site - " + agsSiteURL,"error")
            printMessage(responseJSON,"error")
            if (sendErrorEmail == "true"):
                message = "There is an issue with the ArcGIS Server site - " + agsSiteURL + "..." + "<br/><br/>"
                message += str(responseJSON) + "<br/>"
                # Send email
                sendEmail(message,None)                             
            # Exit the python script
            sys.exit()
        else:
            # Return response
            return responseJSON['currentVersion']          
    except urllib2.URLError, error:
        printMessage("There is an issue connecting to the ArcGIS Server site - " + agsSiteURL + "...","error")
        printMessage(error,"error")
        if (sendErrorEmail == "true"):
            message = "There is an issue connecting to the ArcGIS Server site - " + agsSiteURL + "..." + "<br/><br/>"
            message += str(error) + "<br/>"
            # Send email
            sendEmail(message,None) 
        # Exit the python script
        sys.exit()
# End of check AGS site function


# Start of get services function
def getServices(agsSiteAdminURL, token):
    # Setup the parameters
    parameters = urllib.urlencode({'token': token,
                  'f': 'json'})
    queryString = parameters.encode('utf-8')

    # Post request
    try:
        printMessage("Querying ArcGIS Server for a list of services - " + agsSiteAdminURL + "/admin/services" + "...","info")         
        context = ssl._create_unverified_context()
        request = urllib2.Request(agsSiteAdminURL + "/admin/services",queryString)
        responseJSON = json.loads(urllib2.urlopen(request, context=context).read())
        if "error" in str(responseJSON).lower():
            printMessage(responseJSON,"error")
            if (sendErrorEmail == "true"):
                message = "There is an issue with the ArcGIS Server site - " + agsSiteAdminURL + "..." + "<br/><br/>"
                message += str(responseJSON) + "<br/>"
                # Send email
                sendEmail(message,None)
            # Exit the python script
            sys.exit()
        else:
            # Iterate through services
            services = []
            for eachService in responseJSON['services']:                
                services.append(eachService['serviceName']+ "." + eachService['type'])

            # Iterate through folders
            for folder in responseJSON['folders']:
                # Ignore the system or utilities folder
                if ((folder.lower() != "system") or (folder.lower() != "utilities")):
                    context = ssl._create_unverified_context()
                    request = urllib2.Request(agsSiteAdminURL + "/admin/services/" + folder,queryString)
                    responseJSON = json.loads(urllib2.urlopen(request, context=context).read())
                    if "error" in str(responseJSON).lower():
                        printMessage(responseJSON,"error")
                        if (sendErrorEmail == "true"):
                            message = "There is an issue with the ArcGIS Server site - " + agsSiteAdminURL + "..." + "<br/><br/>"
                            message += str(responseJSON) + "<br/>"
                            # Send email
                            sendEmail(message,None)
                        # Exit the python script
                        sys.exit()
                    else:
                        # Iterate through services
                        for eachService in responseJSON['services']:                
                            services.append(folder + "/" + eachService['serviceName']+ "." + eachService['type'])
            # Return services list 
            return services           
    except urllib2.URLError, error:
        printMessage("There is an issue connecting to the ArcGIS Server site - " + agsSiteAdminURL + "...","error")
        printMessage(error,"error")
        if (sendErrorEmail == "true"):
            message = "There is an issue connecting to the ArcGIS Server site - " + agsSiteAdminURL + "..." + "<br/><br/>"
            message += str(error) + "<br/>"
            # Send email
            sendEmail(message,None)        
        # Exit the python script
        sys.exit()
# End of get services function


# Start of get service status function
def getServiceStatus(agsSiteAdminURL, token, service):
    # Setup the parameters
    parameters = urllib.urlencode({'token': token,
                  'f': 'json'})
    queryString = parameters.encode('utf-8')

    # Post request
    try:
        printMessage("Querying for service status - " + agsSiteAdminURL + "/admin/services/" + service + "/status" + "...","info")         
        context = ssl._create_unverified_context()
        request = urllib2.Request(agsSiteAdminURL + "/admin/services/" + service + "/status",queryString)
        responseJSON = json.loads(urllib2.urlopen(request, context=context).read())
        if "error" in str(responseJSON).lower():
            return responseJSON
        else:
            # Return response
            return responseJSON['realTimeState']                     
    except urllib2.URLError, error:
        return "Error: Could not connect..."
# End of get service status function


# Start of check service function
def checkService(agsSiteURL, token, service):
    # Setup the parameters
    parameters = urllib.urlencode({'token': token,
                  'f': 'json'})
    queryString = parameters.encode('utf-8')

    # Post request
    try:
        printMessage("Querying service for info - " + agsSiteURL + "/rest/services/" + service.replace(".", "/") + "...","info") 
        context = ssl._create_unverified_context()
        request = urllib2.Request(agsSiteURL + "/rest/services/" + service.replace(".", "/"),queryString)
        responseJSON = json.loads(urllib2.urlopen(request, context=context).read())
        
        if "error" in str(json.dumps(responseJSON)).lower():
            return responseJSON
        else:
            # Return response
            return responseJSON                    
    except urllib2.URLError, error:
        return "Error: Could not connect..."
# End of check service function


# Start of query service function
def queryService(agsSiteURL, serviceInfo, token, service):
    # Setup the parameters
    parameters = urllib.urlencode({'token': token,
                  'where': '1=1',
                  'returnCountOnly': 'true',
                  'f': 'json'})
    queryString = parameters.encode('utf-8')

    if "layers" in str(serviceInfo).lower():
        dataLayerFound = False
        layerId = "0"
        for layer in serviceInfo["layers"]:
            # If sublayers in layer object
            if "sublayerids" in str(serviceInfo["layers"]):
                # If not a group layer
                if (layer["subLayerIds"] == None):
                    dataLayerFound = True
                    layerId = str(layer["id"])                 
            else:
                dataLayerFound = True
                layerId = str(layer["id"])                
        # If there is a data layer in the service
        if (dataLayerFound == True):                  
            # Post request
            try:
                printMessage("Querying data in service - " + agsSiteURL + "/rest/services/" + service.replace(".", "/") + "/" + layerId + "/query" + "...","info")           
                context = ssl._create_unverified_context()
                request = urllib2.Request(agsSiteURL + "/rest/services/" + service.replace(".", "/") + "/" + layerId + "/query",queryString)
                responseJSON = json.loads(urllib2.urlopen(request, context=context).read())
                if "error" in str(responseJSON).lower():
                    return responseJSON
                else:
                    # Return response
                    return responseJSON["count"]                    
            except urllib2.URLError, error:
                return "Error: Could not connect..."
        else:
            return "Error: No data in the service..."          
    else:
        return "Error: No layers in the service..."  
# End of query service function


# Start of get token function
def getToken(portalURL,portalUser,portalPassword):
    printMessage("Getting portal token - " + portalURL + "/sharing/rest/generateToken","info")
        
    # Setup the parameters
    parameters = urllib.urlencode({'username': portalUser,
                  'password': portalPassword,
                  'client': 'referer',
                  'referer': portalURL,
                  'expiration': '60',
                  'f': 'json'})
    queryString = parameters.encode('utf-8')

    # Request to get token
    try:
        context = ssl._create_unverified_context()
        request = urllib2.Request(portalURL + "/sharing/rest/generateToken",queryString)
        responseJSON = json.loads(urllib2.urlopen(request, context=context).read())
        if "error" in str(responseJSON).lower():
            printMessage(responseJSON,"error")
            if (sendErrorEmail == "true"):
                message = "There was an issue retrieving the token from the ArcGIS Enterprise site - " + portalURL + "..." + "<br/><br/>"
                message += str(responseJSON) + "<br/>"
                # Send email
                sendEmail(message,None)
            # Exit the python script
            sys.exit()
        else:
            token = responseJSON.get('token')
            return token
    except urllib2.URLError, error:
        printMessage("Could not connect...","error")
        printMessage(error,"error")
        if (sendErrorEmail == "true"):
            message = "There was an issue retrieving the token from the ArcGIS Enterprise site - " + portalURL + "..." + "<br/><br/>"
            message += str(error) + "<br/>"
            # Send email
            sendEmail(message,None)
        # Exit the python script
        sys.exit()
# End of get token function


# Start of print and logging message function
def printMessage(message,type):
    # If using ArcPy
    if (useArcPy == "true"):
        if (type.lower() == "warning"):
            arcpy.AddWarning(message)
            # Logging
            if (enableLogging == "true"):
                logger.warning(message)
        elif (type.lower() == "error"):
            arcpy.AddError(message)
            # Logging
            if (enableLogging == "true"):
                logger.error(message)
        else:
            arcpy.AddMessage(message)
            # Logging
            if (enableLogging == "true"):
                logger.info(message)
    else:
        print(message)
        # Logging
        if (enableLogging == "true"):
            logger.info(message)
# End of print and logging message function


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
def sendEmail(message,attachment):
    # Send an email
    printMessage("Sending email...","info")
    # Server and port information
    smtpServer = smtplib.SMTP(emailServerName,emailServerPort)
    smtpServer.ehlo()
    smtpServer.starttls()
    smtpServer.ehlo
    # Setup content for email (In html format)
    emailMessage = MIMEMultipart('alternative')
    emailMessage['Subject'] = emailSubject
    emailMessage['From'] = emailUser
    emailMessage['To'] = emailTo
    emailText = MIMEText(message, 'html')
    emailMessage.attach(emailText)

    # If there is a file attachment
    if (attachment):
        fp = open(attachment,'rb')
        fileAttachment = email.mime.application.MIMEApplication(fp.read(),_subtype="pdf")
        fp.close()
        fileAttachment.add_header('Content-Disposition','attachment',filename=os.path.basename(attachment))
        emailMessage.attach(fileAttachment)

    # Login with sender email address and password
    if (emailUser and emailPassword):
        smtpServer.login(emailUser, emailPassword)
    # Send the email and close the connection
    smtpServer.sendmail(emailUser, emailTo, emailMessage.as_string())
    smtpServer.quit()
# End of send email function


# This test allows the script to be used from the operating
# system command prompt (stand-alone), in a Python IDE,
# as a geoprocessing script tool, or as a module imported in
# another script
if __name__ == '__main__':
    # If using ArcPy
    if (useArcPy == "true"):
        argv = tuple(arcpy.GetParameterAsText(i)
            for i in range(arcpy.GetArgumentCount()))
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
    
