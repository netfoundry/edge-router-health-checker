"""
NetFoundry Edge Router Health Check
"""
import argparse
import logging
import os
import sys
import traceback
import ipaddress
import socket
from datetime import datetime
import requests
import urllib3
import yaml
from colorama import Fore, Style, init
urllib3.disable_warnings(category = urllib3.exceptions.InsecureRequestWarning)

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
    Paramters:
    logfile (string): The file to log messages to. Defaults to 'program_name.log'.
    loglevel (string): The minimum level of log messages to display. Defaults to logging.INFO.
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
    return os.environ.get(envVar,defaultVar)

def parse_yaml_file(file):
    logging.debug("Parsing Yaml File: %s", file)
    try:
        with open(file, mode='r', encoding='utf-8') as newFile:
            return yaml.safe_load(newFile)
    except Exception as err:
        logging.error(err)
        return None

def list_comprehension_return_dict_if(keysValues, key):
    return {k:v for (k,v) in keysValues if k==key}

def list_comprehension_return_list_if(valueList, key, value):
    return [v for v in valueList if v[key]==value]

def nested_list_comprehension_return_list_if(valueList, key, value, inner_key):
    return [list(v[inner_key]) for v in valueList if v[key]==value]

def is_ipv4(string):
    try:
        ipaddress.IPv4Network(string)
        return True
    except ValueError:
        return False

def case_0(**kwargs):
    logging.debug("All healthchecks are healthy and at least one link is active")
    logging.debug("Control Ping is %s", kwargs["controlPingData"]["healthy"])
    logging.debug("Link Ping is %s", kwargs["linkHealthData"]["healthy"])
    return 0
    
def case_1(**kwargs):
    logging.debug("Number of consecutive controller check failures is %d",
                    kwargs["controlPingData"]["consecutiveFailures"])
    logging.info("Failure start time is %s",  kwargs["controlPingData"]["failingSince"].split("+")[0])
    logging.debug("Current time is %s", kwargs["controlPingData"]["lastCheckTime"])
    return 1

def case_2(**kwargs):
    logging.debug("All links are down, details are %s.", kwargs["linkHealthData"]["details"])
    return 1

def case_3(**kwargs):
    # Switch after delay timeout reached to allow long live sessions
    # to drain if only control channel is failed
    delaySwitch = (datetime.strptime(kwargs["controlPingData"]["lastCheckTime"], '%Y-%m-%dT%H:%M:%SZ') - datetime.strptime(
                    kwargs["controlPingData"]["failingSince"],'%Y-%m-%dT%H:%M:%SZ')).total_seconds()
    logging.debug("Time since Controller channel has gone down is over %ds", delaySwitch)
    if delaySwitch > kwargs["switchTimeout"]:
        logging.debug("Switch to slave due to timeout of %ds has been triggered", kwargs["switchTimeout"])
        return 1
    return 0

def main():
    """
    Main Function
    """

    ### Get command line arguments or environment variables
    args = get_arguments()
    routerConfigFilePath = parse_variables(args.routerConfigFilePath, 'ROUTER_CONFIG_FILE_PATH',
                                           '/opt/netfoundry/ziti/ziti-router/config.yml')
    switchTimeout = int(parse_variables(args.switchTimeout, 'SWITCH_TIMEOUT', 600))
    noTFlagRoutersFilePath = parse_variables(args.noTFlagRoutersFilePath,
                                             'NO_T_FLAG_ROUTERS_FILE_PATH', "")
    logFile = parse_variables(args.logFile, 'LOG_FILE', "")
    logLevel = parse_variables(args.logLevel, 'LOG_LEVEL', "INFO")

    ### Set up initial variables' states/values
    setup_logging(logFile, logLevel)
    if config := parse_yaml_file(routerConfigFilePath):
        pass
    else:
        return 0
    if nonTraversableRouters := parse_yaml_file(noTFlagRoutersFilePath):
        nonTraversableRouters = nonTraversableRouters.get("routerIds")
    else:
        nonTraversableRouters = []
    logging.debug("Routers list is %s", nonTraversableRouters)
    try:
        [[hcPort]] = nested_list_comprehension_return_list_if(
                            list_comprehension_return_dict_if(config.items(),"web")["web"],
                            "name","health-check",
                            "bindPoints")
        [[hcPath]] = nested_list_comprehension_return_list_if(
                            list_comprehension_return_dict_if(config.items(),"web")["web"],
                            "name","health-check","apis")
        ctrlAddr = config["ctrl"]["endpoint"].split(":")[1]
        if is_ipv4(ctrlAddr):
            ctrlIp = [ctrlAddr]
        else:
            ctrlIp = [socket.gethostbyname(ctrlAddr)]
        logging.debug("ctrl address is %s", ctrlIp)
    except Exception as err:
        logging.error(err)
        if logLevel == "DEBUG":
            traceback.print_exception(*sys.exc_info())
        return 1
    url = f'https://127.0.0.1:{hcPort["address"].split(":")[1]}/{hcPath["binding"]}'

    # Get Healthcheck data
    try:
        response = requests.get(url, timeout=TIMEOUT, headers=HEADERS, verify=False)
    except Exception as err:
        logging.error(err)
        if logLevel == "DEBUG":
            traceback.print_exception(*sys.exc_info())
        return 1
    hcData = response.json()["data"]
    [controlPingData] = list_comprehension_return_list_if(hcData["checks"],"id","controllerPing")
    [linkHealthData] = list_comprehension_return_list_if(hcData["checks"],"id","link.health")
    logging.debug("HC = %s", hcData)
    logging.debug("Overall Ping is %s", hcData["healthy"])

    # Evaluate all active links and remove links with no-traversal flag
    if linkHealthData.get("details"):
        newLinkDetails = [d for d in linkHealthData["details"] if d["destRouterId"] not in nonTraversableRouters
                        if d["addresses"]["ack"]["remoteAddr"].split(":")[1] not in ctrlIp]
        logging.debug("New link data after filtering %s", newLinkDetails)
        newLinkHealthy = True
        if len(newLinkDetails) == 0:
            newLinkDetails = []
            newLinkHealthy = False
    else:
        newLinkDetails = []
        newLinkHealthy  = False

    # Evaluate the various conditions and execute the corresponding function
    condition = (controlPingData["healthy"], newLinkHealthy)
    # Create a switch table mapping conditions to corresponding functions
    switch_table = {
        (True, True): case_0,
        (False, False): case_1,
        (True, False): case_2,
        (False, True): case_3
    }
    # Default to case 0
    result = switch_table.get(condition, lambda: 0)(controlPingData=controlPingData, 
                                                    linkHealthData=linkHealthData, 
                                                    switchTimeout=switchTimeout)  
    return result
