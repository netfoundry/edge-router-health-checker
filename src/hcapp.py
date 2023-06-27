"""
NetFoundry Edge Router Health Check
"""
import argparse
import logging
import os
import yaml
import sys
import traceback
import requests
import ipaddress
import socket
from colorama import Fore, Style, init
from datetime import datetime
requests.packages.urllib3.disable_warnings() 


# Requests Options
TIMEOUT = 60
HEADERS = {"content-type": "application/json"}


def get_arguments():
    """
    Create argparser Namespace
    :return: A Namespace containing arguments
    """
    __version__ = '1.0.0'
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--routerConfigFilePath', type=str,
                        help='Specify the edge router config file')
    parser.add_argument('-t', '--switchTimeout', type=int,
                        help='Time to pass to allow for sessions drainage')
    parser.add_argument('-r', '--noTFlagRoutersFilePath', type=str,
                        help='Specify yaml file containing list of router ids that have no-traversable flag set')
    parser.add_argument('-l', '--logLevel', type=str,
                        choices=['INFO', 'ERROR', 'WARNING', 'DEBUG', 'CRITICAL'],
                        help='Set the logging level')
    parser.add_argument('-f', '--logFile', type=str,
                        help='Specify the log file')
    parser.add_argument('-v', '--version',
                        action='version',
                        version=__version__)
    return parser.parse_args()


def setup_logging(logfile, loglevel):
    """
    Set up logging to log messages to both the console and a file.
    :param logfile: The file to log messages to. Defaults to 'program_name.log'.
    :param loglevel: The minimum level of log messages to display. Defaults to logging.INFO.
    """
    class CustomFormatter(logging.Formatter):
        """
        Return a custom color for the message if the level is higher than warning.
        """
        def format(self, record):
            if record.levelno == logging.CRITICAL:
                level_color = Fore.CYAN
            elif record.levelno == logging.DEBUG:
                level_color = Fore.MAGENTA
            elif record.levelno == logging.WARNING:
                level_color = Fore.YELLOW
            elif record.levelno >= logging.ERROR:
                level_color = Fore.RED
            elif record.levelno == logging.INFO:
                level_color = Fore.GREEN
            else:
                level_color = ""

            formatted_msg = super().format(record)
            colored_levelname = f"{level_color}{record.levelname}{Style.RESET_ALL}"
            return formatted_msg.replace(record.levelname, colored_levelname)
    def console_format(record):
        if record.levelno == logging.INFO:
            return console_formatter_info.format(record)
        return console_formatter_warning_error.format(record)

    # Initialize colorama
    init(autoreset=True)

    # Create a logger object
    logger = logging.getLogger()
    logger.setLevel(loglevel)

    # Create a file handler to log messages to a file
    if logfile:
        file_handler = logging.FileHandler(logfile)
        file_handler.setLevel(loglevel)

    # Create a console handler to log messages to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(loglevel)

    # Create formatters with custom date and time format, add them to the appropriate handlers
    file_formatter = CustomFormatter('%(asctime)s-%(levelname)s-%(message)s',
                                    datefmt='%Y-%m-%d-%H:%M:%S')

    if logfile:
        file_handler.setFormatter(file_formatter)

    console_formatter_info = CustomFormatter('%(levelname)s-%(message)s')
    console_formatter_warning_error = CustomFormatter('%(levelname)s-%(message)s')

    console_handler.format = console_format

    if logfile:
        logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def parse_variables(cmdVar, envVar, defaultVar):
    if cmdVar is not None:
        return cmdVar
    else:
        return os.environ.get(envVar,defaultVar)


def parse_yaml_file(file):
    logging.debug("Parsing Yaml File: %s", file)
    try: 
        with open(file, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.error(e)
        return 0


def list_comprehension_return_dict_if(dict,key):
    return {k:v for (k,v) in dict if k==key}


def list_comprehension_return_list_if(list,key,value):
    return [v for v in list if v[key]==value]


def nested_list_comprehension_return_list_if(list,key,value,inner_key):
    return [[v2 for v2 in v[inner_key]] for v in list if v[key]==value]


def is_ipv4(string):
        try:
            ipaddress.IPv4Network(string)
            return True
        except ValueError:
            return False


def main():
    """
    Main Function
    """

    ### Get command line arguments or environment variables
    args = get_arguments()
    routerConfigFilePath = parse_variables(args.routerConfigFilePath, 'ROUTER_CONFIG_FILE_PATH', '/opt/netfoundry/ziti/ziti-router/config.yml')
    switchTimeout = int(parse_variables(args.switchTimeout, 'SWITCH_TIMEOUT', 600))
    noTFlagRoutersFilePath = parse_variables(args.noTFlagRoutersFilePath, 'NO_T_FLAG_ROUTERS_FILE_PATH', "")
    logFile = parse_variables(args.logFile, 'LOG_FILE', "")
    logLevel = parse_variables(args.logLevel, 'LOG_LEVEL', "INFO")
    
    ###
    setup_logging(logFile, logLevel)
    config = parse_yaml_file(routerConfigFilePath)
    if noTFlagRoutersFilePath:
        try:
            nonTraversableRouters = parse_yaml_file(noTFlagRoutersFilePath)["routerIds"]
        except Exception as e:
            logging.error(e)
            if logLevel == "DEBUG":
                traceback.print_exception(*sys.exc_info())
            nonTraversableRouters = [] 
        if not nonTraversableRouters:
            nonTraversableRouters = []
    else:
        nonTraversableRouters = []
    logging.debug("Routers list is %s", nonTraversableRouters)
    try:
        [[hcPort]] = nested_list_comprehension_return_list_if(list_comprehension_return_dict_if(config.items(),"web")["web"],"name","health-check","bindPoints")
        [[hcPath]] = nested_list_comprehension_return_list_if(list_comprehension_return_dict_if(config.items(),"web")["web"],"name","health-check","apis")
        ctrlAddr = (config["ctrl"]["endpoint"].split(":")[1])
        if is_ipv4(ctrlAddr):
            ctrlIp = [ctrlAddr]
        else:
            ctrlIp = [socket.gethostbyname(ctrlAddr)]
        logging.debug("ctrl address is %s", ctrlIp)
    except Exception as e:
        logging.error(e)
        if logLevel == "DEBUG":
            traceback.print_exception(*sys.exc_info())
        return 1    
    url = 'https://127.0.0.1:{}/{}'.format(hcPort["address"].split(":")[1],
                                           hcPath["binding"])
    
    # Get Healthcheck data
    try:
        response = requests.get(url, timeout=TIMEOUT, headers=HEADERS, verify=False)
    except Exception as e:
        logging.error(e)
        if logLevel == "DEBUG":
            traceback.print_exception(*sys.exc_info())
        return 1  
    hcData = response.json()["data"]
    [controlPingData] = list_comprehension_return_list_if(hcData["checks"],"id","controllerPing")
    [linkHealthData] = list_comprehension_return_list_if(hcData["checks"],"id","link.health")
    logging.debug("HC = %s", hcData)
    logging.debug("Control Ping is %s", controlPingData["healthy"])
    logging.debug("Link Ping is %s", linkHealthData["healthy"])
    logging.debug("Overall Ping is %s", hcData["healthy"])

    # Evaluate all active links and remove links with no-traversal flag
    if linkHealthData.get("details"):
        newLinkDetails=[d for d in linkHealthData["details"] if d["destRouterId"] not in nonTraversableRouters if d["addresses"]["ack"]["remoteAddr"].split(":")[1] not in ctrlIp]
        logging.debug("New link data after filtering %s", newLinkDetails)
        newLinkHealthy=True
        if len(newLinkDetails) == 0:
            newLinkDetails = []
            newLinkHealthy=False
    else:
        newLinkDetails = []
        newLinkHealthy=False
    # Decision making logic
    if hcData["healthy"] == True and newLinkDetails:
        logging.debug("Healthchecks are healthy and more links than one are active")
        return 0
    else:
        # If both are false, then switch
        if controlPingData["healthy"] == False and newLinkHealthy == False:
            logging.debug("Number of consecutive controller check failures is %d", controlPingData["consecutiveFailures"])
            logging.info("Failure start time is %s",  controlPingData["failingSince"].split("+")[0])
            logging.debug("Current time is %s", controlPingData["lastCheckTime"])
            return 1
        # If any of them is true, then analyze bit furthur
        else:   
            if controlPingData["healthy"] == True and newLinkHealthy == False:  
                logging.debug("All links are down, details are %s.", linkHealthData["details"])
                return 1
            elif controlPingData["healthy"] == False and newLinkHealthy == True:
                # Switch after delay timeout reached to allow long live sessions to drain if only control channel is failed
                delaySwitch = (datetime.strptime(controlPingData["lastCheckTime"] , '%Y-%m-%dT%H:%M:%SZ') - datetime.strptime(controlPingData["failingSince"] , '%Y-%m-%dT%H:%M:%SZ')).total_seconds()
                logging.debug("Time since Controller channel has gone down is over %ds", delaySwitch)
                if delaySwitch > switchTimeout:
                    logging.debug("Switch due to timeout of %ds has been triggered", switchTimeout )
                    return 1
                else:
                    return 0
            else:
                return 0
   