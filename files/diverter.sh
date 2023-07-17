#!/bin/bash

# Variables
CLOUD_ZITI_HOME="/opt/netfoundry"
OPEN_ZITI_HOME="/opt/openziti"
ZITI_HOME="${CLOUD_ZITI_HOME}/ziti"
ZITI_CLI="${ZITI_HOME}/ziti"
EBPF_BIN="${OPEN_ZITI_HOME}/bin"

# Diverter update function to the latest version
diverter_update() {
  if [[ $(${ZITI_CLI} --version | cut -d"v" -f 2) > "0.27.2" ]]; then
    arch=`uname -m`
    if [ $arch == "x86_64" ]; then
      arch="amd64"
    fi
    browser_download_url=`curl -s https://api.github.com/repos/netfoundry/zfw/releases/latest | jq --arg arch $arch -r '.assets[] | select((.name | test("router")) and (.name | test($arch))).browser_download_url'`
    curl -sL $browser_download_url > /tmp/zfw.deb
    sudo dpkg -i /tmp/zfw.deb
    rm /tmp/zfw.deb
    sudo zfw -Q
    sudo systemctl restart ziti-router
  else
    echo "INFO: ebpf cannot be installed, the installed ziti version is not 0.27.3 or higher."
  fi
}
# Diverter enable function
diverter_enable() {
  status=`dpkg -s zfw-router 2>/dev/null`
  if [[ `echo $status |awk -F'[[:space:]]+|=' '{print $4}'` == "install" ]] && [[ -f $EBPF_BIN/start_ebpf_router.py ]]; then
    sudo $EBPF_BIN/start_ebpf_router.py
    sudo systemctl restart ziti-router
  else 
    echo 'INFO: ebpf not installed, run diverter-update to install it.'
  fi
}
# Health Checker Script update function to the latest version
erhchecker_update() {
  if [[ $(${ZITI_CLI} --version | cut -d"v" -f 2) > "0.28.0" ]]; then
    arch=`uname -m`
    if [ $arch == "x86_64" ]; then
      arch="amd64"
    fi
    browser_download_url=`curl -s https://api.github.com/repos/netfoundry/edge-router-health-checker/releases/latest | jq --arg arch $arch -r '.assets[] | select(.name | test($arch)).browser_download_url'`
    curl -sL $browser_download_url > /tmp/erhchecker.tar.gz
    sudo tar xzf /tmp/erhchecker.tar.gz -C $CLOUD_ZITI_HOME
    rm /tmp/erhchecker.tar.gz
  else
    echo "INFO: erhchecker script cannot be installed, the installed ziti version is not 0.28.1 or higher."
  fi
}

### Main
diverter_update
diverter_enable
erhchecker_update
