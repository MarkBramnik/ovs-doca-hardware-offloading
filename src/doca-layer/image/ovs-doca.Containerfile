FROM $base_image

# Add doca repository
RUN <<EOF cat > /etc/yum.repos.d/doca.repo
[doca]
name=DOCA Online Repo
baseurl=https://linux.mellanox.com/public/repo/doca/$doca_version/rhel$rhel_version/$arch/
enabled=1
gpgcheck=0
EOF

# Add EPEL repository
RUN  dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-$epel_version.noarch.rpm

# Create this directory otherwise the doca will fail halfway through
RUN mkdir -p /var/opt
RUN rpm-ostree override replace libibverbs rdma-core --experimental --from repo='doca'
# Remove the already installed openvswitch package
# Installing the full 'doca-all' meta-package is unnecessary. Installing 'doca-openvswitch' is sufficient,
# as drivers are handled by the network operator. The service will restart automatically to utilize them.
# mft is an optional installation - required only to see that there is a mlxconfig tool available
RUN dnf -y remove openvswitch$openvswitch_version && \
    dnf -y install doca-openvswitch && \
    dnf -y install mft && \
    rm -rf /etc/yum.repos.d/doca.repo
# RUN mkdir -p /etc/modprobe.d/ && echo "blacklist irdma" > /etc/modprobe.d/blacklist-irdma.conf && echo "blacklist ice" > /etc/modprobe.d/blacklist-ice.conf


RUN ostree container commit

