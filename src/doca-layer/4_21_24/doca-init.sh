#!/bin/bash
set -euo pipefail
log() {
    echo "[doca-init] $*"
}
# Read current OVS configuration
CONFIGURATION_CHANGED=false

# hw-offload=true is the kernel TC-flower offload path; doca-init=true
HW_OFFLOAD=$(ovs-vsctl get Open_vSwitch . other_config:hw-offload 2>/dev/null | tr -d '"' || echo "false")
DOCA_INIT=$(ovs-vsctl get Open_vSwitch . other_config:doca-init 2>/dev/null | tr -d '"' || echo "false")
# Disable hardware CT offload (free ASIC resources for forwarding)
HW_OFFLOAD_CT_SIZE=$(ovs-vsctl get Open_vSwitch . other_config:hw-offload-ct-size 2>/dev/null | tr -d '"' || echo "")
# Keep offloaded flows alive for 5 minutes (good for long-running AI jobs)
MAX_IDLE=$(ovs-vsctl get Open_vSwitch . other_config:max-idle 2>/dev/null | tr -d '"' || echo "")
# Set eSwitch count to match the number of switchdev PFs - in spectrum-X there are 8 rails => 8 eSwitches
DOCA_ESWITCH_MAX=$(ovs-vsctl get Open_vSwitch . other_config:doca-eswitch-max 2>/dev/null | tr -d '"' || echo "")

log "Checking OVS Configuration"
if [[ "$HW_OFFLOAD" != "true" ]]; then
   log "Setting config hw-offload"
   ovs-vsctl set Open_vSwitch . other_config:hw-offload=true
   CONFIGURATION_CHANGED=true
fi

if [[ "$DOCA_INIT" != "true" ]]; then
   log "Setting config doca-init"
   ovs-vsctl set Open_vSwitch . other_config:doca-init=true
   CONFIGURATION_CHANGED=true
fi

if [[ -z "$HW_OFFLOAD_CT_SIZE" || "$HW_OFFLOAD_CT_SIZE" -ne 0 ]]; then
   log "Setting config hw-offload-ct-size"
   ovs-vsctl set Open_vSwitch . other_config:hw-offload-ct-size=0
   CONFIGURATION_CHANGED=true
fi

if [[ -z "$MAX_IDLE" || "$MAX_IDLE" -ne 300000 ]]; then
   log "Setting config max-idle"
   ovs-vsctl set Open_vSwitch . other_config:max-idle=300000
   CONFIGURATION_CHANGED=true
fi

if [[ -z "$DOCA_ESWITCH_MAX" || "$DOCA_ESWITCH_MAX" -ne 8 ]]; then
   log "Setting doca-eswitch-max"
   ovs-vsctl set Open_vSwitch . other_config:doca-eswitch-max=8
   CONFIGURATION_CHANGED=true
fi

if $CONFIGURATION_CHANGED; then
   log "Configuration change detected - at least one parameter was updated. Restarting openvswitch..."
   systemctl restart openvswitch
fi
log "Done."