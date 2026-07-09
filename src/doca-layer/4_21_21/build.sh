#!/bin/bash
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

source ${SCRIPT_DIR}/../build-infra.sh

FULL_IMAGE_PATH="quay.io/rh-ee-mbramnik/ecosys-nvidia/custom-coreos-image-doca-3-2-2-os-4-21-21"
BUILD_FILE="custom-doca-image-doca-3.2.2.Containerfile"

build_common $BUILD_FILE ${FULL_IMAGE_PATH} "true"
