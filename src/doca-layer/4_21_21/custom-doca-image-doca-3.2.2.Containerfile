FROM quay.io/openshift-release-dev/ocp-v4.0-art-dev@sha256:1db750ec3985ae348407fcbaa137b58100fccb43647032abe63cc0df2c719a88

# Add doca repository
RUN <<EOF cat > /etc/yum.repos.d/doca.repo
[doca]
name=DOCA Online Repo
baseurl=https://linux.mellanox.com/public/repo/doca/3.2.2/rhel9/x86_64/
enabled=1
gpgcheck=0
EOF

# Add EPEL repository
RUN  dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm

# Create this directory otherwise the doca will fail halfway through
RUN mkdir -p /var/opt
RUN rpm-ostree override replace libibverbs rdma-core --experimental --from repo='doca'
# Remove the already installed openvswitch package
# Installing the full 'doca-all' meta-package is unnecessary. Installing 'doca-openvswitch' is sufficient,
# as drivers are handled by the network operator. The service will restart automatically to utilize them.

RUN dnf -y remove openvswitch3.5 && \
    dnf -y install doca-openvswitch && \
    rm -rf /etc/yum.repos.d/doca.repo
RUN mkdir -p /etc/modprobe.d/ && echo "blacklist irdma" > /etc/modprobe.d/blacklist-irdma.conf && echo "blacklist ice" > /etc/modprobe.d/blacklist-ice.conf
RUN ostree container commit

