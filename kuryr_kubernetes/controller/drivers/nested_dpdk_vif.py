# Copyright (C) 2018 Intel Corporation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from neutronclient.common import exceptions as n_exc
from oslo_log import log as logging

from kuryr_kubernetes import clients
from kuryr_kubernetes.controller.drivers import nested_vif
from kuryr_kubernetes import os_vif_util as ovu

LOG = logging.getLogger(__name__)


class NestedDpdkPodVIFDriver(nested_vif.NestedPodVIFDriver):
    """Manages ports for DPDK based nested-containers to provide VIFs."""

    # TODO(garyloug): maybe log a warning if the vswitch is not ovs-dpdk?

    def __init__(self):
        pass

    def request_vif(self, pod, project_id, subnets, security_groups):
        return self._request_vif(pod, project_id, subnets, security_groups)

    def request_vifs(self, pod, project_id, subnets, security_groups,
                     num_ports):
        # TODO(garyloug): provide an implementation
        raise NotImplementedError()

    def release_vif(self, pod, vif):
        neutron = clients.get_neutron_client()
        nova = clients.get_nova_client()

        vm_id = self._get_parent_port(neutron, pod)['device_id']
        LOG.debug("release_vif for vm_id %s %s", vm_id, vif.id)

        try:
            # TODO(garyloug): check which exceptions can be raised by Nova
            server = nova.servers.get(vm_id)
            server.interface_detach(vif.id)
            neutron.delete_port(vif.id)
        except n_exc.PortNotFoundClient:
            LOG.warning("Unable to release port %s as it no longer exists.",
                        vif.id)
            raise

    def activate_vif(self, pod, vif):
        if vif.active:
            return

        vif.active = True

    def _request_vif(self, pod, project_id, subnets, security_groups):
        neutron = clients.get_neutron_client()
        nova = clients.get_nova_client()

        vm_id = self._get_parent_port(neutron, pod)['device_id']
        net_id = self._get_network_id(subnets)

        # TODO(garyloug): check which exceptions can be raised by Nova
        server = nova.servers.get(vm_id)
        result = server.interface_attach(port_id=None, net_id=net_id,
                                         fixed_ip=None)
        port = neutron.show_port(result.port_id).get('port')
        return ovu.neutron_to_osvif_vif_dpdk(port, subnets, pod)
