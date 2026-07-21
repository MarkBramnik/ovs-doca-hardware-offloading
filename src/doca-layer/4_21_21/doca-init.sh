#!/bin/bash
set -euo pipefail
log() {
    echo "[doca-init] $*"
}
# Read current OVS configuration
# hw-offload=true is the kernel TC-flower offload path; doca-init=true 
# is the DOCA-specific datapath. Both need to be set for OVS-DOCA to function. Either could be missing on a fresh OVSDB

HW_OFFLOAD=$(ovs-vsctl get Open_vSwitch . other_config:hw-offload 2>/dev/null | tr -d '"' || echo "false")
DOCA_INIT=$(ovs-vsctl get Open_vSwitch . other_config:doca-init 2>/dev/null | tr -d '"' || echo "false")
if [ "$HW_OFFLOAD" = "true" ] && [ "$DOCA_INIT" = "true" ]; then
    log "Already initialized (hw-offload=true, doca-init=true). Nothing to do."
    exit 0
fi
log "OVS-DOCA not initialized. Configuring..."
ovs-vsctl set Open_vSwitch . other_config:hw-offload=true
ovs-vsctl set Open_vSwitch . other_config:doca-init=true
log "Restarting openvswitch to activate DOCA datapath..."
systemctl restart openvswitch
log "Done."