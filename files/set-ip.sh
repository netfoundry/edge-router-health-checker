#!/bin/bash
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi
INTERFACE="NONE"
IP="NONE"
PREFIX="NONE"
GW="NONE"
DNSSERVERS="NONE"
DNSSUFFIX="NONE"
MTU="NONE"
PROMPT="yes"
for i in "$@"
do
  case $i in
    --type=*|-tp=*)
        TYPE="${i#*=}"
        shift # past argument=value
        ;;  
    --interface=*|-in=*)
        INTERFACE="${i#*=}"
        shift # past argument=value
        ;;
    --ip=*|-ip=*)
        IP="${i#*=}"
        shift # past argument=value
        ;;
    --prefix=*|-pr=*)
        PREFIX="${i#*=}"
        shift # past argument=value
        ;;
    --gw=*|-gw=*)
        GW="${i#*=}"
        shift # past argument=value
        ;;
    --dns-servers=*|-ds=*)
        DNSSERVERS="${i#*=}"
        shift # past argument=value
        ;;
    --dns-suffix=*|-dx=*)
        DNSSUFFIX="${i#*=}"
        shift # past argument=value
        ;;
    --mtu=*|-mtu=*)
        MTU="${i#*=}"
        shift # past argument=value
        ;;
    -f|--force)
    PROMPT="no"
    shift # past argument=value
        ;;
    -h|--help)
        echo ""
        echo "  $0 <options>"
        echo "     --type=<type> | -tp=<type>"
        echo "     --interface=<interface name> | -in=<interface name>"
        echo "     --ip=<ip_address> | -ip=<ip_address>"
        echo "     --prefix=<subnet prefix> | -pr=<subnet prefix>"
        echo "     --gw=<gateway address> | -gw=<gateway address>"
        echo "     --dns-servers=<dns servers> | -ds=<dns servers>"
        echo "     --dns-suffix=<dns search domain> | -dx=<dns search domain>"
        echo "     --mtu=<mtu length> | -dx=<dns search domain>"
        echo ""
        echo "     -h | --help     Display this help"
        echo "     -f | --force    Option to not prompt for input"
        echo ""
        echo "Static examples:"
        echo "example: $0 -tp=static -ip=10.0.0.10 -pr=24 -gw=10.0.0.1 -dn=\"8.8.8.8,8.8.4.4\" -dx=\"nfdomian.io\" -in=\"eno1\" -mtu=\"9000\" -f"
        echo "example: $0 --ip=10.0.0.10 --prefix=24 --gw=10.0.0.1 --dns-servers=\"8.8.8.8,8.8.4.4\" --dns-suffix=\"nfdomian.io\" --interface=\"eno1\" --mtu=\"9000\" -f"
        echo ""
        echo "Dynamic examples:"
        echo "example: $0 -tp=dynamic -in=\"eno1\" -mtu=\"9000\""
        echo "example: $0 --type=dynamic --interface=\"eno1\" --mtu=\"9000\""
        exit
    ;;
    *)
        echo "Unknown Option: $i"
          # unknown option
    ;;
  esac
done
if [[ ${PROMPT} == "yes" ]]; then
    # choose an interface
    INTERFACE=""
    while [ -z $INTERFACE ]; do
        interface_list=$(ls /sys/class/net | grep -v lo)
        echo -e "\nSELECT THE INTERFACE YOU WANT TO MANAGE"
        select selected_interface in $interface_list
        do 
            INTERFACE=$selected_interface
            break
        done
    done
    TYPE=""
    while [ -z $TYPE ]; do
        echo -e "\nSELECT STATIC or DYNAMIC(DHCP)"
        select configuration_type in static dynamic
        do
            TYPE=$configuration_type
            break
        done
    done
    if [[ $TYPE == "static" ]]; then

        while [ ${PROMPT} == "yes" ]; do
            echo ""
            echo "(*)INTERFACE   = ${INTERFACE}"
            echo "(2)IP          = ${IP}"
            echo "(3)PREFIX      = ${PREFIX}"
            echo "(4)GW          = ${GW}"
            echo "(5)DNSSERVERS  = ${DNSSERVERS}"
            echo "(6)DNSSUFFIX   = ${DNSSUFFIX}"
            echo "(7)MTU         = ${MTU}"
            echo " "
            echo "Enter the line number to modify, or \"0\" to finish input >"
            read MODNUMBER
            if [[ ${MODNUMBER} == "0" ]]; then
                if [[ ${INTERFACE} == "NONE" || ${IP} == "NONE" || ${PREFIX} == "NONE" ]]; then
                    echo ""
                    echo "<<ERROR>> Required parameters missing. Requires IP, PREFIX and INTERFACE"
                    echo ""
                elif [[ ! -d /sys/class/net/${INTERFACE} ]]; then
                    echo ""
                    echo "<<ERROR>> Interface: ${INTERFACE} does not exist"
                    echo ""
                else
                    PROMPT="no"
                fi
            else
                case ${MODNUMBER} in
                    2)
                        echo ""
                        echo "Enter IP >"
                        read IP
                        ;;
                    3)
                        echo ""
                        echo "Enter Prefix >"
                        read PREFIX
                        ;;
                    4)
                        echo ""
                        echo "Enter Gateway IP Address >"
                        read GW
                        ;;
                    5)
                        echo ""
                        echo "Enter DNS Servers >"
                        read DNSSERVERS
                        ;;
                    6)
                        echo ""
                        echo "Enter DNS Suffix >"
                        read DNSSUFFIX
                        ;;
                    7)
                        echo ""
                        echo "Enter MTU >"
                        read MTU
                        ;;
                    *)
                        # unknown option
                        ;;
                esac
            fi
        done  
    else
        while [ ${PROMPT} == "yes" ]; do
            echo ""
            echo "(*)INTERFACE   = ${INTERFACE} (DHCP)"
            echo "(1)MTU         = ${MTU}"
            echo " "
            echo "Enter the line number to modify, or \"0\" to finish input >"
            read MODNUMBER
            if [[ ${MODNUMBER} == "0" ]]; then
                PROMPT="no"
            else
                case ${MODNUMBER} in
                    1)
                        echo ""
                        echo "Enter MTU >"
                        read MTU
                        ;;
                    *)
                        # unknown option
                        ;;
                esac
            fi
        done
    fi
else
    if [[ ! -d /sys/class/net/${INTERFACE} ]]; then
        echo "<<ERROR>> Interface: ${INTERFACE} does not exist"
        exit 1
    fi
fi 
read MAC </sys/class/net/${INTERFACE}/address
if [[ ${TYPE} == "static" ]]; then

    if [[ ${TYPE} == "NONE" || ${INTERFACE} == "NONE" || ${IP} == "NONE" || ${PREFIX} == "NONE" ]]; then
        echo "<<ERROR>> Required parameters missing. Requires TYPE, IP, PREFIX and INTERFACE"
        exit 1
    fi

    # write the static config file (user input)
    NETCFG_FILE="01-netcfg-${INTERFACE}.yaml"
    echo "# This is the network config written by '$0' script" >${NETCFG_FILE}
    echo "network:" >>${NETCFG_FILE}
    echo "  ethernets:" >>${NETCFG_FILE}
    echo "    ${INTERFACE}:" >>${NETCFG_FILE}
    echo "      dhcp4: no" >>${NETCFG_FILE}
    echo "      addresses: [${IP}/${PREFIX}]" >>${NETCFG_FILE}
    echo "      match:" >>${NETCFG_FILE}
    echo "        macaddress: $MAC" >>${NETCFG_FILE}

    if [[ ${GW} == "NONE" ]]; then
        echo "Not writing Gateway Address since it is not supplied by user"
    else
        echo "      routes:" >>${NETCFG_FILE}
        echo "        - to: default" >>${NETCFG_FILE}
        echo "          via: ${GW}" >>${NETCFG_FILE}
    fi

    # write MTU if it is supplied by user
    if [[ ${MTU} != "NONE" ]]; then
        echo "      mtu: ${MTU}" >>${NETCFG_FILE}
    fi

    # only write name servers if one of the dns entries are presented
    if [[ ${DNSSERVERS} != "NONE" || ${DNSSUFFIX} != "NONE" ]]; then
        echo "      nameservers:" >>${NETCFG_FILE}
        if [[ ${DNSSERVERS} != "NONE" ]]; then
            echo "        addresses: [${DNSSERVERS}]" >>${NETCFG_FILE}
        fi

        if [[ ${DNSSUFFIX} != "NONE" ]]; then
            echo "        search: [${DNSSUFFIX}]" >>${NETCFG_FILE}
        fi
    fi
else
    if [[ ${TYPE} == "NONE" || ${INTERFACE} == "NONE" ]]; then
        echo "<<ERROR>> Required parameters missing. Requires TYPE and INTERFACE"
        exit 1
    fi
    # write the static config file (user input)
    NETCFG_FILE="01-netcfg-${INTERFACE}.yaml"
    echo "# This is the network config written by '$0' script" >${NETCFG_FILE}
    echo "network:" >>${NETCFG_FILE}
    echo "  ethernets:" >>${NETCFG_FILE}
    echo "    ${INTERFACE}:" >>${NETCFG_FILE}
    echo "      dhcp4: yes" >>${NETCFG_FILE}
    echo "      match:" >>${NETCFG_FILE}
    echo "        macaddress: $MAC" >>${NETCFG_FILE}
    # write MTU if it is supplied by user
    if [[ ${MTU} != "NONE" ]]; then
        echo "      mtu: ${MTU}" >>${NETCFG_FILE}
    fi
fi    
echo "  version: 2" >>${NETCFG_FILE}
mv ${NETCFG_FILE} /etc/netplan/
echo "network: {config: disabled}" > 99-disable-network-config.cfg
mv 99-disable-network-config.cfg /etc/cloud/cloud.cfg.d/
if [[ ${INTERFACE} != "lo" ]]; then
    case `grep -F "${INTERFACE}" /etc/netplan/*-cloud-init.yaml >/dev/null 2>&1; echo $?` in
    0)
        #interface found, safe to remove cloud init file
        rm /etc/netplan/*-cloud-init.yaml 2>/dev/null
        ;;
    1)
        #in this case, the interface in cloud-init is different
        echo 
        echo "/etc/netplan/*-cloud-init.yaml contains different interface name."
        echo "Please check."
        echo
        ;;
    *)
        #There are no cloud-init files. do nothing
        ;;
    esac
fi 
netplan apply
echo "Complete"
echo "Created file /etc/netplan/01-netcfg-${INTERFACE}.yaml"