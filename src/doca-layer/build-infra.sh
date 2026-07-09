function build_common() {

    local CONTAINER_FILE_NAME=$1
    local FULL_IMAGE_PATH=$2
    local is_push=$3
  
    local CURR_USER=mark
    local QUAY_USER=rh-ee-mbramnik

    #local KUBECONFIG=/home/${CURR_USER}/.kube/edge-21-sno.kubeconfig
    local PULL_SECRET=/home/${CURR_USER}/.kube/mark-pull-secret.json
    local QUAY_PASSWORD_FILE=/home/${CURR_USER}/.kube/quay-password.txt
    
    podman build -t ${FULL_IMAGE_PATH} -f ${CONTAINER_FILE_NAME} --authfile ${PULL_SECRET} --platform linux/amd64
    echo "Build Done"  

    if [[ "$is_push" == "true" ]]; then
       echo "Pushing the image:"
       podman login -u ${QUAY_USER} --password-stdin quay.io < ${QUAY_PASSWORD_FILE}
       podman push ${FULL_IMAGE_PATH}

       echo "Push Done, here are the detailes of the image:"
       podman images --no-trunc | grep $FULL_IMAGE_PATH
    fi
}


