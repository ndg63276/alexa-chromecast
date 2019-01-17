# -*- coding: utf-8 -*-

import logging
import time
import json
import uuid
import socket
from os import environ
import pychromecast
# Setup logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

ip_address = socket.gethostbyname(environ['MY_IP_ADDRESS'])
port_no = int(environ['MY_PORT_NUMBER'])
c = pychromecast.Chromecast(ip_address, port_no)
mc = c.media_controller


appliances = [
    {
        "applianceId": "chromecast-001",
        "manufacturerName": "Google",
        "modelName": "Chromecast",
        "version": "1",
        "friendlyName": "Chromecast",
        "description": "Chromecast",
        "isReachable": True,
        "displayCategories":["TV"],
        "actions": [
            "turnOn",
            "turnOff",
            ],
        "cookie": {}
    },
    ]


def lambda_handler(request, context):
    try:
        logger.info("Request:")
        logger.info(request)

        if request["directive"]["header"]["name"] == "Discover":
            response = handle_discovery(request)
        else:
            response = handle_non_discovery(request)

        logger.info("Response:")
        logger.info(response)

        return response
    except ValueError as error:
        logger.error(error)
        raise

def get_utc_timestamp(seconds=None):
    return time.strftime("%Y-%m-%dT%H:%M:%S.00Z", time.gmtime(seconds))

def get_uuid():
    return str(uuid.uuid4())

def handle_discovery(request):
    endpoints = []
    for appliance in appliances:
        endpoints.append(get_endpoint(appliance))

    response = {
        "event": {
            "header": {
                "namespace": "Alexa.Discovery",
                "name": "Discover.Response",
                "payloadVersion": "3",
                "messageId": get_uuid()
                },
            "payload": {
                "endpoints": endpoints
                }
            }
        }
    return response

def handle_non_discovery(request):
    request_namespace = request["directive"]["header"]["namespace"]
    request_name = request["directive"]["header"]["name"]
    namespace = "Alexa"
    name = "Response"
    properties = []
    
    if request_namespace == "Alexa.PowerController":
        response_name = "powerState"
        if request_name == "TurnOn":
            value = "ON"
            c.quit_app()
            time.sleep(0.1)
            c.start_app('233637DE')
            time.sleep(0.1)
            c.quit_app()
        else:
            value = "OFF"
        properties = [ {
            "namespace": "Alexa.PowerController",
            "name": "powerState",
            "value": value,
            "timeOfSample": get_utc_timestamp(),
            "uncertaintyInMilliseconds": 500
        } ]

    elif request_namespace == "Alexa.PlaybackController":
        if request_name == "Play":
            logger.info('Sending play')
            mc = c.media_controller
            mc.play()
        elif request_name == "Pause":
            mc.pause()
        elif request_name == "FastForward":
            pass
        elif request_name == "Rewind":
            pass
        elif request_name == "Stop":
            c.quit_app()
    return make_response(request, properties, namespace, name)

def make_response(request, properties, namespace, name):       
    response = {
        "context": {
            "properties": properties
        },
        "event": {
            "header": {
                "messageId": get_uuid(),
                "correlationToken": request["directive"]["header"]["correlationToken"],
                "namespace": namespace,
                "name": name,
                "payloadVersion": "3"
            },
            "endpoint": {
                "scope": {
                    "type": "BearerToken",
                    "token": "access-token-from-Amazon"
                },
                "endpointId": request["directive"]["endpoint"]["endpointId"]
            },
            "payload": {
                "cause" : {
                    "type" : "VOICE_INTERACTION"
                },
                "timestamp" : get_utc_timestamp()
            }
        }
    }
    return response

def get_endpoint(appliance):
    endpoint = {
        "endpointId": appliance["applianceId"],
        "manufacturerName": appliance["manufacturerName"],
        "friendlyName": appliance["friendlyName"],
        "description": appliance["description"],
        "displayCategories": appliance["displayCategories"],
        "cookie": appliance["cookie"],
        "capabilities": []
    }
    endpoint["capabilities"] = get_capabilities(appliance)
    return endpoint

def get_capabilities(appliance):
    displayCategories = appliance["displayCategories"]
    if displayCategories == ["TV"]:
        capabilities = [
            {
                "type": "AlexaInterface",
                "interface": "Alexa.PowerController",
                "version": "3",
                "properties": {
                    "supported": [
                        { "name": "powerState" }
                    ],
                    "proactivelyReported": False,
                    "retrievable": False
                }
            },
            {  
                     "type":"AlexaInterface",
                     "interface":"Alexa.PlaybackController",
                     "version":"1.0",
                     "properties":{ },
                     "supportedOperations" : ["Play", "Pause", "Rewind", "FastForward", "Stop"] 
            }
        ]

    # additional capabilities that are required for each endpoint
    endpoint_health_capability = {
        "type": "AlexaInterface",
        "interface": "Alexa.EndpointHealth",
        "version": "3",
        "properties": {
            "supported":[
                { "name":"connectivity" }
            ],
            "proactivelyReported": False,
            "retrievable": False
        }
    }
    alexa_interface_capability = {
        "type": "AlexaInterface",
        "interface": "Alexa",
        "version": "3"
    }
    capabilities.append(endpoint_health_capability)
    capabilities.append(alexa_interface_capability)
    return capabilities

