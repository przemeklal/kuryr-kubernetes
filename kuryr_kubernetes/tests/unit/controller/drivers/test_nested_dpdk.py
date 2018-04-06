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

import ddt
import mock

from kuryr_kubernetes.controller.drivers import nested_dpdk_vif
from kuryr_kubernetes.tests import base as test_base
from kuryr_kubernetes.tests.unit import kuryr_fixtures as k_fix

from neutronclient.common import exceptions as ntron_exc
from novaclient import exceptions as nova_exc


@ddt.ddt
class TestNestedDpdkVIFDriver(test_base.TestCase):

    def test_request_vif(self):
        cls = nested_dpdk_vif.NestedDpdkPodVIFDriver
        m_driver = mock.Mock(spec=cls)

        pod = mock.sentinel.pod
        project_id = mock.sentinel.project_id
        subnets = mock.sentinel.subnets
        security_groups = mock.sentinel.security_groups

        vif = mock.Mock()
        m_driver._request_vif.return_value = vif

        self.assertEqual(vif, cls.request_vif(m_driver, pod, project_id,
                                              subnets, security_groups))

        m_driver._request_vif.assert_called_once_with(pod, project_id, subnets,
                                                      security_groups)

    @mock.patch(
        'kuryr_kubernetes.os_vif_util.neutron_to_osvif_vif_dpdk')
    def test_request_vif_local(self, m_to_vif):
        cls = nested_dpdk_vif.NestedDpdkPodVIFDriver
        m_driver = mock.Mock(spec=cls)
        neutron = self.useFixture(k_fix.MockNeutronClient()).client
        nova = self.useFixture(k_fix.MockNovaClient()).client

        pod = mock.sentinel.pod
        project_id = mock.sentinel.project_id
        subnets = mock.sentinel.subnets
        security_groups = mock.sentinel.security_groups
        vm_id = mock.sentinel.parent_port_id
        net_id = mock.sentinel.net_id
        port_id = mock.sentinel.port_id
        port = mock.sentinel.port

        parent_port = mock.MagicMock()
        vif = mock.Mock()
        server = mock.MagicMock()
        result = mock.Mock()

        parent_port.__getitem__.return_value = vm_id
        result.port_id = port_id
        server.interface_attach.return_value = result
        m_to_vif.return_value = vif
        m_driver._get_parent_port.return_value = parent_port
        m_driver._get_network_id.return_value = net_id
        nova.servers.get.return_value = server
        neutron.show_port.return_value.get.return_value = port

        self.assertEqual(vif, cls._request_vif(m_driver, pod, project_id,
                                               subnets, security_groups))

        m_driver._get_parent_port.assert_called_once_with(neutron, pod)
        m_driver._get_network_id.assert_called_once_with(subnets)
        nova.servers.get.assert_called_once_with(vm_id)
        server.interface_attach.assert_called_once_with(
            port_id=None, net_id=net_id, fixed_ip=None)
        neutron.show_port.assert_called_once_with(result.port_id)
        m_to_vif.assert_called_once_with(port, subnets, pod)

    @mock.patch(
        'kuryr_kubernetes.os_vif_util.neutron_to_osvif_vif_dpdk')
    def test_request_vif_parent_not_found(self, m_to_vif):
        cls = nested_dpdk_vif.NestedDpdkPodVIFDriver
        m_driver = mock.Mock(spec=cls)
        neutron = self.useFixture(k_fix.MockNeutronClient()).client
        nova = self.useFixture(k_fix.MockNovaClient()).client

        pod = mock.sentinel.pod
        project_id = mock.sentinel.project_id
        subnets = mock.sentinel.subnets
        security_groups = mock.sentinel.security_groups
        vm_id = mock.sentinel.parent_port_id
        net_id = mock.sentinel.net_id
        port_id = mock.sentinel.port_id
        port = mock.sentinel.port

        parent_port = mock.MagicMock()
        vif = mock.Mock()
        server = mock.MagicMock()
        result = mock.Mock()

        parent_port.__getitem__.return_value = vm_id
        result.port_id = port_id
        server.interface_attach.return_value = result
        m_to_vif.return_value = vif
        m_driver._get_parent_port.side_effect = \
            ntron_exc.NeutronClientException
        m_driver._get_network_id.return_value = net_id
        nova.servers.get.return_value = server
        neutron.show_port.return_value.get.return_value = port

        self.assertRaises(ntron_exc.NeutronClientException, cls._request_vif,
                          m_driver, pod, project_id, subnets, security_groups)

        m_driver._get_parent_port.assert_called_once_with(neutron, pod)
        m_driver._get_network_id.assert_not_called()
        nova.servers.get.assert_not_called()
        server.interface_attach.assert_not_called()
        neutron.show_port.assert_not_called()
        m_to_vif.assert_not_called()

    @mock.patch(
        'kuryr_kubernetes.os_vif_util.neutron_to_osvif_vif_dpdk')
    def test_request_vif_server_not_found(self, m_to_vif):
        cls = nested_dpdk_vif.NestedDpdkPodVIFDriver
        m_driver = mock.Mock(spec=cls)
        neutron = self.useFixture(k_fix.MockNeutronClient()).client
        nova = self.useFixture(k_fix.MockNovaClient()).client

        pod = mock.sentinel.pod
        project_id = mock.sentinel.project_id
        subnets = mock.sentinel.subnets
        security_groups = mock.sentinel.security_groups
        vm_id = mock.sentinel.parent_port_id
        net_id = mock.sentinel.net_id
        port_id = mock.sentinel.port_id
        port = mock.sentinel.port

        parent_port = mock.MagicMock()
        vif = mock.Mock()
        server = mock.MagicMock()
        result = mock.Mock()

        parent_port.__getitem__.return_value = vm_id
        result.port_id = port_id
        server.interface_attach.return_value = result
        m_to_vif.return_value = vif
        m_driver._get_parent_port.return_value = parent_port
        m_driver._get_network_id.return_value = net_id
        # TODO(garyloug) Is this Nova exception OK?
        nova.servers.get.side_effect = nova_exc.ClientException(400)
        neutron.show_port.return_value.get.return_value = port

        self.assertRaises(nova_exc.ClientException, cls._request_vif,
                          m_driver, pod, project_id, subnets, security_groups)

        m_driver._get_parent_port.assert_called_once_with(neutron, pod)
        m_driver._get_network_id.assert_called_once_with(subnets)
        nova.servers.get.assert_called_once_with(vm_id)
        server.interface_attach.assert_not_called()
        neutron.show_port.assert_not_called()
        m_to_vif.assert_not_called()

    @mock.patch(
        'kuryr_kubernetes.os_vif_util.neutron_to_osvif_vif_dpdk')
    def test_request_vif_attach_failed(self, m_to_vif):
        cls = nested_dpdk_vif.NestedDpdkPodVIFDriver
        m_driver = mock.Mock(spec=cls)
        neutron = self.useFixture(k_fix.MockNeutronClient()).client
        nova = self.useFixture(k_fix.MockNovaClient()).client

        pod = mock.sentinel.pod
        project_id = mock.sentinel.project_id
        subnets = mock.sentinel.subnets
        security_groups = mock.sentinel.security_groups
        vm_id = mock.sentinel.parent_port_id
        net_id = mock.sentinel.net_id
        port_id = mock.sentinel.port_id
        port = mock.sentinel.port

        parent_port = mock.MagicMock()
        vif = mock.Mock()
        server = mock.MagicMock()
        result = mock.Mock()

        parent_port.__getitem__.return_value = vm_id
        result.port_id = port_id
        m_to_vif.return_value = vif
        m_driver._get_parent_port.return_value = parent_port
        m_driver._get_network_id.return_value = net_id
        nova.servers.get.return_value = server
        neutron.show_port.return_value.get.return_value = port
        server.interface_attach.side_effect = nova_exc.ClientException(400)

        self.assertRaises(nova_exc.ClientException, cls._request_vif,
                          m_driver, pod, project_id, subnets, security_groups)

        m_driver._get_parent_port.assert_called_once_with(neutron, pod)
        m_driver._get_network_id.assert_called_once_with(subnets)
        nova.servers.get.assert_called_once_with(vm_id)
        server.interface_attach.assert_called_once_with(
            port_id=None, net_id=net_id, fixed_ip=None)
        neutron.show_port.assert_not_called()
        m_to_vif.assert_not_called()

    def test_release_vif(self):
        cls = nested_dpdk_vif.NestedDpdkPodVIFDriver
        m_driver = mock.Mock(spec=cls)
        neutron = self.useFixture(k_fix.MockNeutronClient()).client
        nova = self.useFixture(k_fix.MockNovaClient()).client

        port_id = mock.sentinel.port_id
        pod = mock.sentinel.pod
        vif = mock.Mock()
        vif.id = port_id

        vm_id = mock.sentinel.vm_id
        vm_port = mock.MagicMock()
        vm_port.__getitem__.return_value = vm_id

        server = mock.MagicMock()

        m_driver._get_parent_port.return_value = vm_port
        nova.servers.get.return_value = server

        cls.release_vif(m_driver, pod, vif)

        m_driver._get_parent_port.assert_called_once_with(neutron, pod)
        nova.servers.get.assert_called_once_with(vm_id)
        server.interface_detach.assert_called_once_with(vif.id)
        neutron.delete_port.assert_called_once_with(vif.id)

    def test_release_parent_not_found(self):
        cls = nested_dpdk_vif.NestedDpdkPodVIFDriver
        m_driver = mock.Mock(spec=cls)
        neutron = self.useFixture(k_fix.MockNeutronClient()).client
        nova = self.useFixture(k_fix.MockNovaClient()).client

        pod = mock.sentinel.pod
        vif = mock.Mock()
        vif.id = mock.sentinel.vif_id

        vm_id = mock.sentinel.parent_port_id
        parent_port = mock.MagicMock()
        parent_port.__getitem__.return_value = vm_id

        server = mock.MagicMock()

        m_driver._get_parent_port.side_effect = \
            ntron_exc.NeutronClientException

        self.assertRaises(ntron_exc.NeutronClientException, cls.release_vif,
                          m_driver, pod, vif)

        m_driver._get_parent_port.assert_called_once_with(neutron, pod)
        nova.servers.get.assert_not_called()
        server.interface_detach.assert_not_called()
        neutron.delete_port.assert_not_called()

    def test_release_server_not_found(self):
        cls = nested_dpdk_vif.NestedDpdkPodVIFDriver
        m_driver = mock.Mock(spec=cls)
        neutron = self.useFixture(k_fix.MockNeutronClient()).client
        nova = self.useFixture(k_fix.MockNovaClient()).client

        pod = mock.sentinel.pod
        vif = mock.Mock()
        vif.id = mock.sentinel.vif_id

        vm_id = mock.sentinel.parent_port_id
        parent_port = mock.MagicMock()
        parent_port.__getitem__.return_value = vm_id

        server = mock.MagicMock()

        m_driver._get_parent_port.return_value = parent_port

        nova.servers.get.side_effect = nova_exc.ClientException(400)

        self.assertRaises(nova_exc.ClientException, cls.release_vif,
                          m_driver, pod, vif)

        m_driver._get_parent_port.assert_called_once_with(neutron, pod)
        nova.servers.get.assert_called_once_with(vm_id)
        server.interface_detach.assert_not_called()
        neutron.delete_port.assert_not_called()

    def test_release_detach_failed(self):
        cls = nested_dpdk_vif.NestedDpdkPodVIFDriver
        m_driver = mock.Mock(spec=cls)
        neutron = self.useFixture(k_fix.MockNeutronClient()).client
        nova = self.useFixture(k_fix.MockNovaClient()).client

        pod = mock.sentinel.pod
        vif = mock.Mock()
        vif.id = mock.sentinel.vif_id

        vm_id = mock.sentinel.parent_port_id
        parent_port = mock.MagicMock()
        parent_port.__getitem__.return_value = vm_id

        server = mock.MagicMock()

        server.interface_detach.side_effect = nova_exc.ClientException(400)

        m_driver._get_parent_port.return_value = parent_port
        nova.servers.get.return_value = server

        self.assertRaises(nova_exc.ClientException, cls.release_vif,
                          m_driver, pod, vif)

        m_driver._get_parent_port.assert_called_once_with(neutron, pod)
        nova.servers.get.assert_called_once_with(vm_id)
        server.interface_detach.assert_called_once_with(vif.id)
        neutron.delete_port.assert_not_called()

    def test_release_vif_delete_failed(self):
        cls = nested_dpdk_vif.NestedDpdkPodVIFDriver
        m_driver = mock.Mock(spec=cls)
        neutron = self.useFixture(k_fix.MockNeutronClient()).client
        nova = self.useFixture(k_fix.MockNovaClient()).client

        pod = mock.sentinel.pod
        vif = mock.Mock()
        vif.id = mock.sentinel.vif_id

        vm_id = mock.sentinel.parent_port_id
        parent_port = mock.MagicMock()
        parent_port.__getitem__.return_value = vm_id

        server = mock.MagicMock()
        nova.servers.get.return_value = server

        m_driver._get_parent_port.return_value = parent_port

        neutron.delete_port.side_effect = ntron_exc.PortNotFoundClient

        self.assertRaises(ntron_exc.PortNotFoundClient, cls.release_vif,
                          m_driver, pod, vif)

        m_driver._get_parent_port.assert_called_once_with(neutron, pod)
        nova.servers.get.assert_called_once_with(vm_id)
        server.interface_detach.assert_called_once_with(vif.id)
        neutron.delete_port.assert_called_once_with(vif.id)

    @ddt.data((False), (True))
    def test_activate_vif(self, active_value):
        cls = nested_dpdk_vif.NestedDpdkPodVIFDriver
        m_driver = mock.Mock(spec=cls)
        pod = mock.sentinel.pod
        vif = mock.Mock()
        vif.active = active_value

        cls.activate_vif(m_driver, pod, vif)

        self.assertEqual(vif.active, True)
