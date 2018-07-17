#-------------------------------------------------------------
# Name:       Portal Services Report
# Purpose:    Queries an ArcGIS Online/Portal for ArcGIS site to find all services that are being used in web maps
#             then aggregates these in a CSV file. This tool needs to be run as an ArcGIS Online/Portal administrator.
# Author:     Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:    05/04/2016
# Last Updated:    11/04/2017
# Copyright:   (c) Eagle Technology
# ArcGIS Version:   ArcMap 10.4+
# Python Version:   2.7
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
import ssl


# Start of main function
def mainFunction(portalUrl,portalAdminName,portalAdminPassword,csvFile,csvFile2): # Get parameters from ArcGIS Desktop tool by seperating by comma e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)  
    try:
        # --------------------------------------- Start of code --------------------------------------- #
        
        printMessage("Connecting to Portal - " + portalUrl + "...","info")
        # Generate token for portal
        token = generateToken(portalAdminName, portalAdminPassword, portalUrl)

        printMessage("Getting organisation ID for portal site...","info")
        # Setup parameters for organisation query
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
                 
        # POST the request - organisation query
        context = ssl._create_unverified_context()
        requestURL = urllib2.Request(portalUrl + "/sharing/rest/portals/self",params)
        response = urllib2.urlopen(requestURL, context=context)
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
            # Get the organisation ID
            orgID = responseJSON["id"]

            # Setup the query
            query = "type:\"web map\" AND -type:\"web mapping application\" AND orgid:\"" + orgID + "\""
            startQueryNum = 0
            
            # Setup the dictionary to store the web maps
            webmaps = []
        
            # Search content on the site
            printMessage("Searching web maps on portal site...","info")
            # Return all the web maps - 100 at a time
            while (startQueryNum != -1):
                totalWebmaps,nextStartID,webMapsReturned = searchWebmaps(portalUrl,token,query,startQueryNum)
                startQueryNum = nextStartID
                webmaps = webmaps + webMapsReturned
                if (startQueryNum != -1):
                    printMessage("Queried " + str(nextStartID-1) + " of " + str(totalWebmaps) + " web maps...","info")
                else:
                    printMessage("Queried " + str(totalWebmaps) + " of " + str(totalWebmaps) + " web maps...","info")                    

            # Setup the dictionary to store the services
            services = []
            
            # For each of the web maps returned
            count = 0
            for webmap in webmaps:
                printMessage("Querying web map - " + webmap["id"] + "...","info")
                servicesReturned = servicesWebmap(portalUrl,token,webmap["id"])
                services = services + servicesReturned
                count = count + 1
                printMessage("Number of services in web map - " + str(len(servicesReturned)),"info")
                printMessage("Queried " + str(count) + " of " + str(totalWebmaps) + " web maps...","info")

            printMessage("Creating full services list CSV file - " + csvFile + "...","info")
            # Create a CSV file and setup header
            file = open(csvFile, 'wb')
            writer = csv.writer(file, delimiter=",")

            # Add in header information   
            headerRow = []                               
            headerRow.append("Service")
            headerRow.append("Title")
            headerRow.append("Web Map URL")
            writer.writerow(headerRow)

            # Add in rows
            for service in services:
                row = []                               
                row.append(service["url"])
                row.append(service["title"])
                row.append(portalUrl + "/home/item.html?id=" + service["webmap"])
                writer.writerow(row)                

            printMessage("Creating grouped services list CSV file - " + csvFile2 + "...","info")
            servicesGrouped = {}
            # Reference CSV file
            file = open(csvFile, 'rb')
            csvreader = csv.reader(file, delimiter=',')
            # For each row in the file
            count = 0
            for row in csvreader:
                key = row[0]
                # If not the first row
                if (count > 0):
                    # If service already added, increment by 1
                    if key in servicesGrouped:
                        servicesGrouped[key] = servicesGrouped[key] + 1
                    # If service is not added, add it
                    else:
                        servicesGrouped[key] = 1
                count = count + 1
                
            # Create a CSV file and setup header
            file = open(csvFile2, 'wb')
            writer = csv.writer(file, delimiter=",")

            # Add in header information   
            headerRow = []                               
            headerRow.append("Service")
            headerRow.append("Count")
            writer.writerow(headerRow)

            # Sort the services by the grouping count            
            sortedServicesGrouped = sorted(servicesGrouped, key=servicesGrouped.__getitem__, reverse=True)

            # Add in rows
            for sortedServiceGrouped in sortedServicesGrouped:
                row = []                               
                row.append(sortedServiceGrouped)
                row.append(servicesGrouped[sortedServiceGrouped])
                writer.writerow(row)
            
        # --------------------------------------- End of code --------------------------------------- #
        # If called from gp tool return the arcpy parameter   
        if __name__ == '__main__':
            # Return the output if there is any
            if output:
                # If ArcGIS desktop installed
                if (arcgisDesktop == "true"):
                    arcpy.SetParameterAsText(1, output)
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


# Start of search web maps function
def searchWebmaps(portalUrl,token,query,startQueryNum):
    # Setup parameters for search query 
    dict = {}
    dict['f'] = 'json'
    dict['token'] = token
    dict['num'] = "100"
    dict['sortField'] = "title"
    dict['sortOrder'] = "asc"
    #dict['restrict'] = "true"
    dict['focus'] = "maps"    
    dict['q'] = query
    dict['start'] = startQueryNum
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

    # POST the request - Creates a new item in the ArcGIS online site
    requestURL = urllib2.Request(portalUrl + "/sharing/rest/search",params)
    context = ssl._create_unverified_context()
    response = urllib2.urlopen(requestURL, context=context)
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
        webmaps = []
        # Get the total web maps found
        totalWebmaps = responseJSON["total"]        
        # Get the ID to start from for the next search
        nextStartID = responseJSON["nextStart"]
        # For each of the results returned
        for result in responseJSON["results"]:
            # Append data into dictionary
            webmaps.append({"id":result["id"],"title":result["title"],"owner":result["owner"],"access":result["access"]})

        # Return dictionary
        return totalWebmaps,nextStartID,webmaps
# End of search web maps function


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
    context = ssl._create_unverified_context()
    response = urllib2.urlopen(requestURL, context=context)
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
                # Append data into dictionary
                services.append({"url":operationalLayer["url"],"title":operationalLayer["title"],"webmap":webmap})

        # For each of the basemap layers returned
        for basemap in responseJSON["baseMap"]["baseMapLayers"]:
            # If URL to service
            if ("url" in basemap):       
                # If URL to service
                services.append({"url":basemap["url"],"title":"Basemap","webmap":webmap})

        # Return dictionary
        return services     
# End of services in web map function


# Start of get token function
def generateToken(username, password, portalUrl):
    # Python version check
    if sys.version_info[0] >= 3:
        # Python 3.x
        # Encode parameters
        parameters = urllib.parse.urlencode({'username' : username,
                        'password' : password,
                        'client' : 'referer',
                        'referer': portalUrl,
                        'expiration': 60,
                        'f' : 'json'})
    else:
        # Python 2.x
        # Encode parameters
        parameters = urllib.urlencode({'username' : username,
                        'password' : password,
                        'client' : 'referer',
                        'referer': portalUrl,
                        'expiration': 60,
                        'f' : 'json'})
    parameters = parameters.encode('utf-8')
    try:
        requestURL = urllib2.Request(portalUrl + '/sharing/rest/generateToken?',parameters)
        context = ssl._create_unverified_context()
        response = urllib2.urlopen(requestURL, context=context)
    except Exception as e:
        printMessage( 'Unable to open the url %s/sharing/rest/generateToken' % (portalUrl),'error')
        printMessage(e,'error')

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
        if int(errDict['code'])==498:
            message = 'Token Expired. Getting new token... '
            token = generateToken(username,password, portalUrl)
        else:
            message =  'Error Code: %s \n Message: %s' % (errDict['code'],
            errDict['message'])
            printMessage(message,'error')
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
