#!/bin/bash
# First check if the edge router config file exists
CLOUD_ZITI_HOME="/opt/netfoundry"
router_config_file="$CLOUD_ZITI_HOME/ziti/ziti-router/config.yml"
# Is router config file present?
if [ $# -ne 2 ];then
    echo "Two arguments required, i.e. [resolverip] [dnsResolverIpRange]"
    exit 0
fi
if [ -f "$router_config_file" ]; then
    # Look up tunnel edge binding
    TUNNEL=$(cat $CLOUD_ZITI_HOME/ziti/ziti-router/config.yml |yq '.listeners[] | select(.binding == "tunnel")')
    if [ "$TUNNEL" ]; then
        # Get Tunnel Mode
        TMODE=$(cat $CLOUD_ZITI_HOME/ziti/ziti-router/config.yml |yq '.listeners[] | select(.binding == "tunnel").options.mode')
        # If tproxy is set and initial set flag is set, both true?
        if [ "$TMODE" == null ] || [ "$TMODE" == "tproxy" ]; then
            echo "INFO: Updating resolver in the edge router config file"
            export var=$1
            yq -i '(.listeners[] | select(.binding == "tunnel").options | .resolver) = "udp://"+strenv(var)+":53"' $router_config_file
            export var=$2
            yq -i '(.listeners[] | select(.binding == "tunnel").options | .dnsSvcIpRange) = strenv(var)' $router_config_file
            unset var
            echo "INFO: Done"
        else 
            echo "INFO: trpoxy mode not configured, nothing to do"
        fi
    else 
        echo "INFO: tunnel mode not configured, nothing to do"
    fi
else
    echo "INFO: router config file not found, perhaps it is expected!?"
fi
