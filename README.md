# edge-router-health-checker

This Python script that can be used by high avaibility processes like keepalived to analyze openziti router health checks and make informed decisions when to best make protection switches/reversions.

Everytime this script is run, it will search the openziti router configuration file to find the health checks web endpoint setting, i.e listen port. Once found, it will query the web endpoint and go through analysis of the output it gets. The environment variable to pass the configuration file location is `ROUTER_CONFIG_FILE_PATH`.

There are four states that decision is made from:

1. case_0 (`True`, `True`)
The is the default state. The `controllerPing` and `link.health` are both True. Return state is 0.
1. case_1 (`False`, `False`)
The `controllerPing` and `link.health` are both False. Return state is 1.
1. case_2 (`True`, `False`)
The `controllerPing` is True and `link.health` is False. Return state is 1.
1. case_3 (`False`, `True`)
The `controllerPing` is False and `link.health` is True. Return state is 1. In this state, a timer (environment variable is `SWITCH_TIMEOUT`) was introduced to delay the return state change to 1 to allow for the current sessions to drain. The default value is 5 minutes. The timer can be adjusted.

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

1. In CloudZiti networks, there is a fabric only router deployed on the controller to allow for the managment channel to flow through to reach the salt master that is configured on the controller. The link from this router is ignored by the decision alrgorithm even if it is reported as being healthy. To find this link, the ip address of the controller is compared to the destination ip address of each link reported by the `link.health` check until match is made.

***Example Usage***

Here is the link to the vrrp keepalived setup guide that goes through the configration set up steps. The section pertaining to configuration steps of the script is at the end of the article, i.e. `Ability to track loss of controller and/or fabric to trigger local switchover`

[On-Prem HA](https://support.netfoundry.io/hc/en-us/articles/9962679994381-On-Prem-Ingress-High-Availability)
