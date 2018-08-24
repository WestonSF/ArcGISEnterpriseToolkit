#-------------------------------------------------------------
# Name:       ArcGIS Server Availability 
# Purpose:    Checks ArcGIS server site and services and reports if site is down and/or particular
#             service is down. This tool should be setup as an automated task on the server.       
# Author:     Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:    07/02/2014
# Last Updated:    22/06/2015
# Copyright:   (c) Eagle Technology
# ArcGIS Version:   10.1+
# Python Version:   2.7
#--------------------------------

# Import modules
import os
import sys
import logging
import datetime
import smtplib
import httplib
import json
import urllib
import urlparse
import arcpy

# Enable data to be overwritten
arcpy.env.overwriteOutput = True

# Set variables
enableLogging = "false"
logFile = r""
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
def mainFunction(agsServerSite,username,password,service): # Get parameters from ArcGIS Desktop tool by seperating by comma e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)  
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
        token = getToken(username, password, serverName, serverPort, protocol)

        # If token received
        if (token != -1):
            # Check server web adaptor
            webAdaptors = getWebAdaptor(serverName, serverPort, protocol, token) 

            for webAdaptor in webAdaptors:
                # Get the server site details on web adaptor
                protocolWeb, serverNameWeb, serverPortWeb, contextWeb = splitSiteURL(webAdaptor['webAdaptorURL'])

                # Query arcgis server via the web adaptor
                webStatusVersion = checkWebAdaptor(serverNameWeb, serverPortWeb, protocolWeb, contextWeb, token)               

                if (webStatusVersion != -1):
                    arcpy.AddMessage("ArcGIS Server With Web Adaptor " + webAdaptor['webAdaptorURL'] + " is running correctly on version " + str(webStatusVersion) + "...")
                    # Logging
                    if (enableLogging == "true"):
                        logger.info("ArcGIS Server With Web Adaptor " + webAdaptor['webAdaptorURL'] + " is running correctly on version " + str(webStatusVersion) + "...")
                # Else
                else:
                    arcpy.AddError("There is an issue with the web adaptor - " + webAdaptor['webAdaptorURL'])
                    # Logging
                    if (enableLogging == "true"):                    
                        logger.error("There is an issue with the web adaptor - " + webAdaptor['webAdaptorURL'])
                    # Email
                    if (sendErrorEmail == "true"):
                        # Send email
                        sendEmail("There is an issue with the web adaptor - " + webAdaptor['webAdaptorURL'])                     
                    
            # List to hold services and their status
            servicesStatus = []
            
            # If a service is provided
            if (len(str(service)) > 0): 
                # Query the service status
                realtimeStatus = getServiceStatus(serverName, serverPort, protocol, service, token)
                # Check the service
                serviceInfo = checkService(serverName, serverPort, protocol, service, token)
                
                serviceDetails = {'status': realtimeStatus, 'info': serviceInfo, 'service': service}
                servicesStatus.append(serviceDetails)
            # Else
            else:
                # Get all services
                services = getServices(serverName, serverPort, protocol, token)
                # Query all services
                # Iterate through services
                for eachService in services:
                    # Query the service status
                    realtimeStatus = getServiceStatus(serverName, serverPort, protocol, eachService, token)          
                    # Check the service
                    serviceInfo = checkService(serverName, serverPort, protocol, eachService, token)

                    serviceDetails = {'status': realtimeStatus, 'info': serviceInfo, 'service': eachService}
                    servicesStatus.append(serviceDetails)
                    
            stoppedServices = 0
            errorServices = 0
            errors = []
            # Iterate through services
            for eachServicesStatus in servicesStatus:
                # If status is stopped add to stopped counter
                if (eachServicesStatus['status'] == "STOPPED"):
                    stoppedServices = stoppedServices + 1
                else:
                    # If error with service add to error counter
                    if 'error' in eachServicesStatus['info']:
                        errorServices = errorServices + 1
                        errors.append(eachServicesStatus['info']['error']['message'])
                    
            # If any services are stopped/have errors
            if (stoppedServices > 0) or (errorServices > 0):
                arcpy.AddError(str(stoppedServices) + " services are stopped...")
                arcpy.AddError(str(errorServices) + " services have errors...")
                for error in errors:
                    arcpy.AddError(error)
                # Logging
                if (enableLogging == "true"):
                    logger.error(str(stoppedServices) + " services are stopped")
                    logger.error(str(errorServices) + " services have errors")
                    for error in errors:
                        logger.error(error)
                # Email
                if (sendErrorEmail == "true"):
                    errorMessage = str(stoppedServices) + " services are stopped" + "\n"
                    errorMessage += str(errorServices) + " services have errors" + "\n" + "\n"
                    for error in errors:
                        errorMessage += error + "\n"
                    # Send email
                    sendEmail(errorMessage)                     
            else:
                arcpy.AddMessage("All services are running correctly...")
                # Logging
                if (enableLogging == "true"):
                    logger.info("All services are running correctly...")            

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


# Start of get web adaptor function
def getWebAdaptor(serverName, serverPort, protocol, token):
    params = urllib.urlencode({'token': token, 'f': 'json'})

    # Construct URL to get the web adaptor
    url = "/arcgis/admin/system/webadaptors"

    # Post to the server
    try:
        response, data = postToServer(serverName, serverPort, protocol, url, params)   
    except:
        arcpy.AddError("Unable to connect to the ArcGIS Server site on " + serverName + ". Please check if the server is running.")
        # Log error
        if (logging == "true") or (sendErrorEmail == "true"):       
            logger.error("Unable to connect to the ArcGIS Server site on " + serverName + ". Please check if the server is running.")
            sys.exit()
        return -1

    # If there is an error
    if (response.status != 200):
        arcpy.AddError("Error getting web adaptor.")
        # Logging
        if (enableLogging == "true"):     
            logger.error("Error getting web adaptor.")
            sys.exit()
        arcpy.AddError(str(data))
        return -1
    if (not assertJsonSuccess(data)):
        arcpy.AddError("Error getting web adaptor. Please check if the server is running and ensure that the username/password provided are correct.")
        # Logging
        if (enableLogging == "true"): 
            logger.error("Error getting web adaptor. Please check if the server is running and ensure that the username/password provided are correct.")
            sys.exit()
        return -1
    # On successful query
    else: 
        dataObject = json.loads(data)
        return dataObject['webAdaptors']
# End of get web adaptor function


# Start of get web adaptor function
def checkWebAdaptor(serverName, serverPort, protocol, webName, token):
    params = urllib.urlencode({'token': token, 'f': 'json'})

    # Construct URL to check the web adaptor
    url = webName + "/rest/services"

    # Post to the server
    try:
        response, data = postToServer(serverName, serverPort, protocol, url, params)         
    except:
        arcpy.AddError("Unable to connect to the ArcGIS Server site on " + serverName + ". Please check if the server is running.")
        # Log error
        if (logging == "true") or (sendErrorEmail == "true"):       
            logger.error("Unable to connect to the ArcGIS Server site on " + serverName + ". Please check if the server is running.")
            sys.exit()
        return -1
    # If there is an error
    if (response.status != 200):
        arcpy.AddError("Error checking web adaptor.")
        # Logging
        if (enableLogging == "true"):     
            logger.error("Error checking web adaptor.")
            sys.exit()
        arcpy.AddError(str(data))
        return -1
    if (not assertJsonSuccess(data)):
        arcpy.AddError("Error checking web adaptor. Please check if the server is running and ensure that the username/password provided are correct.")
        # Logging
        if (enableLogging == "true"): 
            logger.error("Error checking web adaptor. Please check if the server is running and ensure that the username/password provided are correct.")
            sys.exit()
        return -1
    # On successful query
    else:
        dataObject = json.loads(data)
        return dataObject['currentVersion']
# End of get web adaptor function


# Start of get services function
def getServices(serverName, serverPort, protocol, token):
    params = urllib.urlencode({'token': token, 'f': 'json'})

    # Services list
    services = []
    
    # Construct URL to get services
    url = "/arcgis/admin/services"

    # Post to the server
    try:
        response, data = postToServer(serverName, serverPort, protocol, url, params)
    except:
        arcpy.AddError("Unable to connect to the ArcGIS Server site on " + serverName + ". Check if the server is running.")
        # Logging
        if (enableLogging == "true"):     
            logger.error("Unable to connect to the ArcGIS Server site on " + serverName + ". Check if the server is running.")
            sys.exit()
        return -1

    # If there is an error
    if (response.status != 200):
        arcpy.AddError("Error getting services.")
        arcpy.AddError(str(data))
        # Logging
        if (enableLogging == "true"): 
            logger.error("Error getting services.")
            sys.exit()
        return -1
    if (not assertJsonSuccess(data)):
        arcpy.AddError("Error getting services. Check if the server is running and ensure that the username/password provided are correct.")
        # Logging
        if (enableLogging == "true"):
            logger.error("Error getting services. Check if the server is running and ensure that the username/password provided are correct.")  
            sys.exit()
        return -1
    # On successful query
    else: 
        dataObject = json.loads(data)
        
        # Iterate through services
        for eachService in dataObject['services']:
            # Add to list
            services.append(eachService['serviceName'] + "." + eachService['type'])
                    
        # Iterate through folders
        for folder in dataObject['folders']:

            # Construct URL to get services for the folder
            url = "/arcgis/admin/services/" + folder

            # Post to the server
            try:
                response, data = postToServer(serverName, serverPort, protocol, url, params)
            except:
                arcpy.AddError("Unable to connect to the ArcGIS Server site on " + serverName + ". Check if the server is running.")
                # Logging
                if (enableLogging == "true"):     
                    logger.error("Unable to connect to the ArcGIS Server site on " + serverName + ". Check if the server is running.")
                    sys.exit()
                return -1
    
            # If there is an error
            if (response.status != 200):
                arcpy.AddError("Error getting services.")
                arcpy.AddError(str(data))
                # Logging
                if (enableLogging == "true"):     
                    logger.error("Error getting services.")
                    sys.exit()
                return -1
            if (not assertJsonSuccess(data)):
                arcpy.AddError("Error getting services. Check if the server is running and ensure that the username/password provided are correct.")
                # Logging
                if (enableLogging == "true"):   
                    logger.error("Error getting services. Check if the server is running and ensure that the username/password provided are correct.")
                    sys.exit()
                return -1
            # On successful query
            else: 
                dataObject = json.loads(data)
                # Iterate through services
                for eachService in dataObject['services']:                
                    services.append(folder + "/" + eachService['serviceName']+ "." + eachService['type'])
        # Return a list of services
        return services                    
# End of get services function


# Start of get service status function
def getServiceStatus(serverName, serverPort, protocol, service, token):
    params = urllib.urlencode({'token': token, 'f': 'json'})

    # Construct URL to get the service status
    url = "/arcgis/admin/services/" + service + "/status"

    # Post to the server
    try:
        response, data = postToServer(serverName, serverPort, protocol, url, params)
    except:
        arcpy.AddError("Unable to connect to the ArcGIS Server site on " + serverName + ". Check if the server is running.")
        # Logging
        if (enableLogging == "true"):     
            logger.error("Unable to connect to the ArcGIS Server site on " + serverName + ". Check if the server is running.")
            sys.exit()
        return -1

    # If there is an error
    if (response.status != 200):
        arcpy.AddError("Error getting service status.")
        # Logging
        if (enableLogging == "true"):    
            logger.error("Error getting service status.")
            sys.exit()
        arcpy.AddError(str(data))
        return -1
    if (not assertJsonSuccess(data)):
        arcpy.AddError("Error getting service status. Check if the server is running and ensure that the username/password provided are correct.")
        # Logging
        if (enableLogging == "true"):  
            logger.error("Error getting service status. Check if the server is running and ensure that the username/password provided are correct.")
            sys.exit()
        return -1
    # On successful query
    else: 
        dataObject = json.loads(data)
        # Return the real time state
        return dataObject['realTimeState']
# End of get service status function


# Start of check service function
def checkService(serverName, serverPort, protocol, service, token):
    params = urllib.urlencode({'token': token, 'f': 'json'})

    # Construct URL to get the service status
    url = "/arcgis/rest/services/" + service.replace(".", "/")

    # Post to the server
    try:
        response, data = postToServer(serverName, serverPort, protocol, url, params)
    except:
        arcpy.AddError("Unable to connect to the ArcGIS Server site on " + serverName + ". Check if the server is running.")
        # Logging
        if (enableLogging == "true"):      
            logger.error("Unable to connect to the ArcGIS Server site on " + serverName + ". Check if the server is running.")
            sys.exit()
        return -1

    # If there is an error
    if (response.status != 200):
        arcpy.AddError("Error getting service status.")
        # Logging
        if (enableLogging == "true"):  
            logger.error("Error getting service status.")
            sys.exit()
        arcpy.AddError(str(data))
        return -1
    if (not assertJsonSuccess(data)):
        arcpy.AddError("Error getting service status. Check if the server is running and ensure that the username/password provided are correct.")
        # Logging
        if (enableLogging == "true"):    
            logger.error("Error getting service status. Check if the server is running and ensure that the username/password provided are correct.")
            sys.exit()
        return -1
    # On successful query
    else:    
        dataObject = json.loads(data)
        
        # Return the service object
        return dataObject
# End of check service function


# Start of get token function
def getToken(username, password, serverName, serverPort, protocol):
    params = urllib.urlencode({'username': username.decode(sys.stdin.encoding or sys.getdefaultencoding()).encode('utf-8'), 'password': password.decode(sys.stdin.encoding or sys.getdefaultencoding()).encode('utf-8'),'client': 'referer','referer':'backuputility','f': 'json'})
           
    # Construct URL to get a token
    url = "/arcgis/tokens/generateToken"
        
    try:
        response, data = postToServer(serverName, serverPort, protocol, url, params)
    except:
        arcpy.AddError("Unable to connect to the ArcGIS Server site on " + serverName + ". Check if the server is running.")
        # Logging
        if (enableLogging == "true"):  
            logger.error("Unable to connect to the ArcGIS Server site on " + serverName + ". Check if the server is running.")
            sys.exit()
        return -1    
    # If there is an error getting the token
    if (response.status != 200):
        arcpy.AddError("Error while generating the token.")
        arcpy.AddError(str(data))
        # Logging
        if (enableLogging == "true"):  
            logger.error("Error while generating the token.")
            sys.exit()
        return -1
    if (not assertJsonSuccess(data)):
        arcpy.AddError("Error while generating the token. Check if the server is running and ensure that the username/password provided are correct.")
        # Logging
        if (enableLogging == "true"):      
            logger.error("Error while generating the token. Check if the server is running and ensure that the username/password provided are correct.")
            sys.exit()
        return -1
    # Token returned
    else:
        # Extract the token from it
        dataObject = json.loads(data)

        # Return the token if available
        if "error" in dataObject:
            arcpy.AddError("Error retrieving token.")
            # Logging
            if (enableLogging == "true"):     
                logger.error("Error retrieving token.")
                sys.exit()
            return -1        
        else:
            return dataObject['token']
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
    
