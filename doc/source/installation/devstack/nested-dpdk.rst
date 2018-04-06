How to try out nested-pods locally (DPDK)
============================================
Following are the instructions for an all-in-one setup, using the nested DPDK driver.

Configure the VM:

- Install kernel version supporting uio_pci_generic module::

    wget http://kernel.ubuntu.com/~kernel-ppa/mainline/v4.12/linux-headers-4.12.0-041200_4.12.0-041200.201707022031_all.deb
    http://kernel.ubuntu.com/~kernel-ppa/mainline/v4.12/linux-headers-4.12.0-041200-generic_4.12.0-041200.201707022031_amd64.deb
    http://kernel.ubuntu.com/~kernel-ppa/mainline/v4.12/linux-image-4.12.0-041200-generic_4.12.0-041200.201707022031_amd64.deb
    sudo dpkg -i *.deb
    sudo update-grub
    sudo reboot

- Install DPDK. On Ubuntu::

    sudo apt update
    sudo apt install dpdk

- Enable hugepages::

    sudo sysctl -w vm.nr_hugepages=768

- Load DPDK userspace driver::

    sudo modprobe uio_pci_generic

- Clone devstack repository::

    cd ~
    git clone https://git.openstack.org/openstack-dev/devstack

- Edit local.conf::

    [[local|localrc]]

    RECLONE="no"

    enable_plugin kuryr-kubernetes \
    https://git.openstack.org/openstack/kuryr-kubernetes

    OFFLINE="no"
    LOGFILE=devstack.log
    LOG_COLOR=False
    ADMIN_PASSWORD=<undercloud_password>
    DATABASE_PASSWORD=<undercloud_password>
    RABBIT_PASSWORD=<undercloud_password>
    SERVICE_PASSWORD=<undercloud_password>
    SERVICE_TOKEN=<undercloud_password>
    IDENTITY_API_VERSION=3
    ENABLED_SERVICES=""

    HOST_IP=<vm-ip-address>

    SERVICE_HOST=<undercloud-host-ip-address>
    MULTI_HOST=1
    KEYSTONE_SERVICE_HOST=$SERVICE_HOST
    MYSQL_HOST=$SERVICE_HOST
    RABBIT_HOST=$SERVICE_HOST

    KURYR_CONFIGURE_NEUTRON_DEFAULTS=False
    KURYR_CONFIGURE_BAREMETAL_KUBELET_IFACE=False

    enable_service docker
    enable_service etcd3
    enable_service legacy_etcd
    enable_service kubernetes-api
    enable_service kubernetes-controller-manager
    enable_service kubernetes-scheduler
    enable_service kubelet
    enable_service kuryr-kubernetes
    enable_service kuryr-daemon

- Stack::

    cd ~/devstack
    ./stack.sh

- Install CNI plugins::

    wget https://github.com/containernetworking/plugins/releases/download/v0.6.0/cni-plugins-amd64-v0.6.0.tgz
    tar xf cni-plugins-amd64-v0.6.0.tgz -C ~/cni/bin/

- Install Multus CNI using this guide: https://github.com/intel/multus-cni#build
    - *Note: Temporarily using Multus CNI as a solution until Kuryr natively supports multiple VIFs*

- Create Multus CNI configuration file ~/cni/conf/multus-cni.conf::

    {
       "name":"multus-demo-network",
       "type":"multus",
       "delegates":[
          {
             "type":"kuryr-cni",
             "kuryr_conf":"/etc/kuryr/kuryr.conf",
             "debug":true
          },
          {
             "type":"macvlan",
             "master":"ens3",
             "masterplugin":true,
             "ipam":{
                "type":"host-local",
                "subnet":"10.0.0.0/24"
             }
          }
       ]
    }

- Edit Kuryr configuration file /etc/kuryr/kuryr.conf::

    [DEFAULT]
    debug = True
    use_stderr = true
    [binding]
    link_iface = ens3
    [cache_defaults]
    [cni_daemon]
    [cni_health_server]
    cg_path = /system.slice/system-devstack.slice/devstack@kuryr-daemon.service
    [health_server]
    [kubernetes]
    enable_manager = False
    vif_pool_driver = noop
    pod_vif_driver = nested-dpdk
    port_debug = True
    api_root = http://<vm-ip-address>:8080
    [kuryr-kubernetes]
    [neutron]
    memcached_servers = localhost:11211
    signing_dir = /var/cache/kuryr
    cafile = /opt/stack/data/ca-bundle.pem
    project_domain_name = Default
    project_name = service
    user_domain_name = Default
    password = <undercloud_password>
    username = kuryr
    auth_url = http://<undercloud-host-ip-address>/identity
    auth_type = password
    [neutron_defaults]
    project = <project_id>
    pod_subnet = <pod_subnet _id>
    pod_security_groups = <pod_security_group_id>
    service_subnet = <service_subnet_id>
    [node_driver_caching]
    [octavia_defaults]
    [pod_vif_nested]
    worker_nodes_subnet = <worker_nodes_subnet_id>
    [pool_manager]
    [subnet_caching]
    [vif_pool]
    ports_pool_update_frequency = 20
    ports_pool_batch = 10
    ports_pool_max = 0
    ports_pool_min = 5
    [oslo_concurrency]
    lock_path = /opt/stack/data/kuryr-kubernetes

- Reload systemd services::

    sudo systemctl daemon-reload

- Restart systemd services::

    sudo systemctl restart devstack@kubelet.service devstack@kuryr-kubernetes.service devstack@kuryr-daemon.service

- To build and run CMK::

    cd ~
    git clone https://github.com/intel/CPU-Manager-for-Kubernetes.git
    make
    kubectl create -f resources/authorization/.
    kubectl create -f resources/pods/cmk-cluster-init-pod.yaml
