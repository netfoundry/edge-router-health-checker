# edge-router-health-checker

This Python script that can be used by high availability processes like keepalived to analyze openziti router health checks and make informed decisions when to best make protection switches/reversions.

Every time this script is run, it will search the openziti router configuration file to find the health checks web endpoint setting, i.e listen port. Once found, it will query the web endpoint and go through analysis of the output it gets. The environment variable to pass the configuration file location is `ROUTER_CONFIG_FILE_PATH`.

## There are four states that decision is made from:

1. case_0 (`True`, `True`)
The is the default state. The `controllerPing` and `link.health` are both True. Return state is 0.
1. case_1 (`False`, `False`)
The `controllerPing` and `link.health` are both False. Return state is 1.
1. case_2 (`True`, `False`)
The `controllerPing` is True and `link.health` is False. Return state is 1.
1. case_3 (`False`, `True`)
The `controllerPing` is False and `link.health` is True. Return state is 1. In this state, a timer (environment variable is `SWITCH_TIMEOUT`) was introduced to delay the return state change to 1 to allow for the current sessions to drain. The default value is 5 minutes. The timer can be adjusted. Additionally, the current session count is checked, if they are equal to 2 or less (assumption is that 2 sessions are related to Management Plane.), it will switch over before the timer expires.

***Important Notes:***

1. To allow the decision algorithm to take non-traversable openziti routers into account, a file with routerIds of these routers needs to be passed in. The environment variable to pass the file location is `NO_T_FLAG_ROUTERS_FILE_PATH`. The yaml schema for this file is as follows:

    ```json
    {
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
    ```

    Example:

    ```yaml
    routerIds:
    - falWSf-KgH
    - UcLWVFsrx
    - wgLwaF-KDH
    ```

1. In CloudZiti networks, a fabric only router is deployed on the controller host to allow for the management channel to flow through to reach the salt master that runs on that host. The link from this router is ignored by the decision algorithm even if it is reported as being healthy. To find this link, the ip address of the controller is compared to the destination ip address of each link reported by the `link.health` check until match is made.

    ***Example Usage***

    Here is the link to the vrrp keepalived setup guide that goes through the configuration set up steps. The section pertaining to configuration steps of the script is at the end of the article, i.e. `Ability to track loss of controller and/or fabric to trigger local switchover`

    [On-Prem HA](https://support.netfoundry.io/hc/en-us/articles/9962679994381-On-Prem-Ingress-High-Availability)

1. ### Cloud Network Load Balancer Use Case

    In public clouds, the network load balancers use http based health checks to detect issues with backend virtual machines /applications. Unfortunately, the decisions to mark particular backends unhealthy are based on the http return codes. Networking Applications like openziti router provide more information about its state or the overlay network data/control planes it is connected to. Although these state changes are not reported by the http error codes, the details are included in the body of the responses. Therefore, the health check algorithm needs ability to process the body of the responses to make more intelligent decisions.
    In light of the above challenges, we created helper scripts to provide such aid. The high level details are as follows:

    1. [Keepalived](https://www.keepalived.org/) is used as a control plane to manage the scripts. The configuration for the master node is [located here](files/keepalived_master.conf). Each openziti router is managed by a separate instance of vrrp master.
    1. [erhchecker.pyz](src/__main__.py) script is used to process the payload of the health check responses and return 0 or 1 state based on the four states described [previously here](#there-are-four-states-that-decision-is-made-from)
    1. [vrrp_notify.sh](files/vrrp_notify.sh) script is notified during failure to close the  access to the health-check endpoint at 8081/tcp on the firewall.
    1. Load Balancer HC Endpoint registers a timeout error and marks the corresponding backend as unhealthy.
    1. Once the error state is cleared and back to 0, the firewall port is opened and LB marks the corresponding backend as healthy.
