"""
NetFoundry Edge Router Health Check
"""
import argparse
import logging
import os
import traceback
import ipaddress
import socket
from datetime import datetime
import subprocess
import re
import yaml
import requests
import urllib3
from jsonschema import validate, exceptions as jsonexcept
from colorama import Fore, Style, init
urllib3.disable_warnings(category = urllib3.exceptions.InsecureRequestWarning)

# Global Options
TIMEOUT = 60
HEADERS = {"content-type": "application/json"}
SCHEMA_ROUTERIDS  = {
                        "type": "object",
                        "required": ["routerIds"],
                        "properties": {
                            "routerIds": {
                                "type": "array", 
                                "items": {
                                     "type": "string"
                                }
                            }
                        }
                    }

def get_arguments():
    """
    Create argparser Namespace

    Returns:
        A Namespace containing arguments
    """

    __version__ = '1.1.0'
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--routerConfigFilePath', type=str,
                        help='Specify the edge router config file')
    parser.add_argument('-z', '--zitiBinaryFilePath', type=str,
                        help='Specify the ziti binary file')
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

class CustomFormatter(logging.Formatter):
    """Return a custom color for the message based on the log level."""

    LEVEL_COLORS = {
        logging.CRITICAL: Fore.CYAN,
        logging.ERROR: Fore.RED,
        logging.WARNING: Fore.YELLOW,
        logging.INFO: Fore.GREEN,
        logging.DEBUG: Fore.MAGENTA
    }

    def format(self, record):
        level_color = self.LEVEL_COLORS.get(record.levelno, "")
        colored_levelname = f"{level_color}{record.levelname}{Style.RESET_ALL}"
        formatted_msg = super().format(record)
        return formatted_msg.replace(record.levelname, colored_levelname)

def setup_logging(logfile='program_name.log', loglevel=logging.INFO):
    """
    Set up logging to log messages to both the console and a file.
    Parameters:
    - logfile (string): The file to log messages to. Defaults to 'program_name.log'.
    - loglevel (int or string): The minimum level of log messages to display. Defaults to logging.INFO.
    """
    # Initialize colorama
    init(autoreset=True)

    # Create a logger object
    logger = logging.getLogger()
    logger.setLevel(loglevel)

    # Create a file handler to log messages to a file
    if logfile:
        file_handler = logging.FileHandler(logfile)
        file_handler.setLevel(loglevel)
        file_formatter = CustomFormatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Create a console handler to log messages to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(loglevel)

    console_formatter = CustomFormatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

def parse_variables(cmdVar, envVar, defaultVar):
    """Returns the value of the variable, depending on whether it was passed as a command-line argument or an environment variable.

    Parameters:
    - cmdVar: The command-line argument value.
    - envVar: The environment variable name.
    - defaultVar: The default value.

    Returns:
        The value of the variable.
    """
    if cmdVar is not None:
        return cmdVar
    return os.environ.get(envVar,defaultVar)

def parse_yaml_file(filePath, logString):
    """Parses a YAML file and returns the parsed data.

    Parameters:
    - filePath: The path to the YAML file.
    - logString: The string to use for logging.

    Returns:
        The parsed YAML data, or None if the file could not be parsed.
    """
    logging.debug("Parsing YAML File: %s", filePath)

    if not filePath:
        logging.warning("No File Path given for '%s' file", logString)
        return None
    
    if os.path.getsize(filePath) == 0:
        logging.warning("File has no content: %s", logString)
        return None
    
    try:
        with open(filePath, mode='r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except (yaml.YAMLError, IOError):
        logging.warning(traceback.format_exc(0))
        logging.debug(traceback.format_exc())

    return None

def list_comprehension_return_dict_if(keysValues, key):
    """Returns a dictionary of the keys and values, where the keys match the given key.

    Parameter:
    - keysValues: The list of keys and values.
    - key: The key to match.

    Returns:
        A dictionary of the keys and values that match the given key.
    """

    return {k: v for k, v in keysValues if k == key}

def list_comprehension_return_list_if(valueList, key, value):
    """Returns a list of the values from the list, where the values match the given key and value.

    Parameters:
    - valueList: The list of values.
    - key: The key to match.
    - value: The value to match.

    Returns:
        A list of the values from the list that match the given key and value.
    """

    return [v for v in valueList if v[key] == value]

def nested_list_comprehension_return_list_if(valueList, key, value, innerKey):
    """Returns a list of the inner keys and values from the list, where the inner keys match the given key and value.

    Parameters:
    - valueList: The list of values.
    - key: The key to match.
    - value: The value to match.
    - inner_key: The inner key to return the values for.

    Returns:
        A list of the inner keys and values from the list that match the given key and value.
    """

    return [list(v[innerKey]) for v in valueList if v[key] == value]

def is_ipv4(string):
    """Returns True if the string is a valid IPv4 address, False otherwise."""

    try:
        ipaddress.IPv4Network(string)
        return True
    except ValueError:
        return False

def are_circuits_active(zitiBinaryFilePath):
    """Returns True if there are active circuits, False otherwise."""

    try:
        circuitsData = subprocess.run(
            [zitiBinaryFilePath, "agent", "router", "dump-routes", "--app-type", "router"],
            check=True,
            capture_output=True,
            text=True,
            timeout=15).stdout
        logging.debug(circuitsData)
    except subprocess.CalledProcessError:
        logging.warning(traceback.format_exc(0))
        return False

    searchPattern = r"\bcircuits\b(\s+\(([^()]+)\))?"
    match = re.search(searchPattern, circuitsData)
    if match and int(match.group(2)) > 2:
        logging.info("Number of active circuits is %s", match.group(2))
        return True
    return False

def case_0(**kwargs):
    """Returns 0 when all health-checks are healthy and at least one link is active."""

    logging.debug("All health-checks are healthy and at least one link is active")
    logging.debug("Control Ping is %s", kwargs["controlPingData"]["healthy"])
    logging.debug("Link Ping is %s", kwargs["linkHealthData"]["healthy"])
    return 0
    
def case_1(**kwargs):
    """Returns 1 when all health-checks are not healthy."""

    logging.debug("Number of consecutive controller check failures is %d",
                    kwargs["controlPingData"]["consecutiveFailures"])
    logging.info("Failure start time is %s",  kwargs["controlPingData"]["failingSince"].split("+")[0])
    logging.debug("Current time is %s", kwargs["controlPingData"]["lastCheckTime"])
    return 1

def case_2(**kwargs):
    """Returns 1 when all links are down"""

    logging.debug("All links are down, details are %s.", kwargs["linkHealthData"]["details"])
    return 1

def case_3(**kwargs):
    """
    Returns 
            1 when controllerPing is not healthy and the delay switch timeout has been reached or no circuits are active, 
            0 otherwise.
    """

    delaySwitchReading = (datetime.strptime(kwargs["controlPingData"]["lastCheckTime"], '%Y-%m-%dT%H:%M:%SZ') - datetime.strptime(
                    kwargs["controlPingData"]["failingSince"],'%Y-%m-%dT%H:%M:%SZ')).total_seconds()
    logging.debug("Time since Controller channel has gone down is over %ds", delaySwitchReading)
    if not are_circuits_active(kwargs["zitiBinaryFilePath"]):
        logging.debug("Switch to slave, since they are no active circuits")
        return 1
    if delaySwitchReading > kwargs["switchTimeout"]:
        logging.debug("Switch to slave due to timeout of %ds has been triggered", kwargs["switchTimeout"])
        return 1
    return 0

def main():
    """
    Main Function
    """

    # Get command line arguments or environment variables
    args = get_arguments()
    routerConfigFilePath   = parse_variables(args.routerConfigFilePath, 'ROUTER_CONFIG_FILE_PATH',
                                           '/opt/netfoundry/ziti/ziti-router/config.yml')
    zitiBinaryFilePath     = parse_variables(args.zitiBinaryFilePath, 'ZITI_BINARY_FILE_PATH',
                                           '/opt/netfoundry/ziti/ziti')
    switchTimeout          = int(parse_variables(args.switchTimeout, 'SWITCH_TIMEOUT', 600))
    noTFlagRoutersFilePath = parse_variables(args.noTFlagRoutersFilePath,
                                             'NO_T_FLAG_ROUTERS_FILE_PATH', "")
    logFile                = parse_variables(args.logFile, 'LOG_FILE', "")
    logLevel               = parse_variables(args.logLevel, 'LOG_LEVEL', "INFO")

    # Set up initial variables' states/values
    setup_logging(logFile, logLevel)
    if config := parse_yaml_file(routerConfigFilePath, "router config"):
        pass
    else:
        return 0
    nonTraversableRouters = []
    if ids := parse_yaml_file(noTFlagRoutersFilePath, "router ids"):
        try:
            validate(instance=ids, schema=SCHEMA_ROUTERIDS)
            nonTraversableRouters = ids.get("routerIds")
        except jsonexcept.ValidationError:
            logging.warning(traceback.format_exc(0))
            nonTraversableRouters = []
    logging.debug("Routers list is %s", nonTraversableRouters)

    # Get HC Url from config file
    try:
        web_config = list_comprehension_return_dict_if(config.items(), "web")["web"]
        [[hcPort]] = nested_list_comprehension_return_list_if(web_config, "name", "health-check", "bindPoints")
        [[hcPath]] = nested_list_comprehension_return_list_if(web_config, "name", "health-check", "apis")
        url = f'https://127.0.0.1:{hcPort["address"].split(":")[1]}/{hcPath["binding"]}'
        ctrlAddr = config["ctrl"]["endpoint"].split(":")[1]
    except (KeyError, ValueError):
        logging.warning(traceback.format_exc(0))
        logging.debug(traceback.format_exc())
        return 0
    
    # Resolve ctrl dns name if needed
    try:
        ctrlIp = [ctrlAddr] if is_ipv4(ctrlAddr) else [socket.gethostbyname(ctrlAddr)]   
        logging.debug("ctrl address is %s", ctrlIp)
    except (socket.gaierror, socket.herror, OSError):
        logging.warning(traceback.format_exc(0))
        logging.debug(traceback.format_exc())
        return 0

    # Get Healthcheck data
    try:
        response = requests.get(url, timeout=TIMEOUT, headers=HEADERS, verify=False)
        hcData = response.json()["data"]
    except (requests.RequestException, ValueError, KeyError, TypeError):
        logging.error(traceback.format_exc(0))
        logging.debug(traceback.format_exc())
        return 1
    [controlPingData] = list_comprehension_return_list_if(hcData["checks"],"id","controllerPing")
    [linkHealthData] = list_comprehension_return_list_if(hcData["checks"],"id","link.health")
    logging.debug("HC = %s", hcData)
    logging.debug("Overall Ping is %s", hcData["healthy"])

    # Evaluate all active links and remove links with no-traversal flag
    newLinkDetails = []
    newLinkHealthy = False

    if linkHealthData.get("details"):
        newLinkDetails = [
            d for d in linkHealthData["details"]
            if d["destRouterId"] not in nonTraversableRouters
            if d["addresses"]["ack"]["remoteAddr"].split(":")[1] not in ctrlIp
        ]
        logging.debug("New link data after filtering %s", newLinkDetails)

        if len(newLinkDetails) > 0:
            newLinkHealthy = True

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
                                                    switchTimeout=switchTimeout,
                                                    zitiBinaryFilePath=zitiBinaryFilePath)
    return result
