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

import os
import subprocess

from os_vif import objects as obj_vif
from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils

from kuryr_kubernetes import clients
from kuryr_kubernetes.cni.binding import base as b_base
from kuryr_kubernetes import constants
from kuryr_kubernetes.handlers import health

from kuryr.lib._i18n import _


LOG = logging.getLogger(__name__)
CONF = cfg.CONF


# TODO(garyloug) These should probably eventually move to config.py
# TODO(garyloug) Would be nice if dpdk_driver is set as CNI arg
nested_dpdk_opts = [
    cfg.StrOpt('dpdk_devbind',
               help=_('Absolute path to DPDK devbind script used for binding '
                      'and unbinding devices to kernel and userspace drivers'),
               default='/sbin/dpdk-devbind'),
    cfg.StrOpt('dpdk_driver',
               help=_('The DPDK driver that the device will be bound to after '
                      'it is unbound from the kernel driver'),
               default='uio_pci_generic'),
]

CONF.register_opts(nested_dpdk_opts, "nested_dpdk")


class DpdkDriver(health.HealthHandler):

    def __init__(self):
        super(DpdkDriver, self).__init__()

    def connect(self, vif, ifname, netns):
        name = self._get_iface_name_by_mac(vif.address)
        driver, pci_addr = self._get_device_info(name)

        vif.dev_driver = driver
        vif.pci_address = pci_addr
        dpdk_driver = CONF.nested_dpdk.dpdk_driver
        self._change_driver_binding(pci_addr, dpdk_driver)
        self._set_vif(vif)

    def disconnect(self, vif, ifname, netns):
        self._change_driver_binding(vif.pci_address, vif.dev_driver)

    def _get_iface_name_by_mac(self, mac_address):
        ipdb = b_base.get_ipdb()

        for name, data in ipdb.interfaces.items():
            if data['address'] == mac_address:
                return data['ifname']

    def _get_device_info(self, ifname):
        """Get driver and PCI addr by using sysfs"""

        NET_DEV_PATH = "/sys/class/net/{}/device"
        VIRTIO_DEVS_PATH = "/sys/bus/virtio/devices/"
        VIRTIO_PCI_PATH = "/sys/bus/pci/devices/"

        # TODO(garyloug): check the type (virtio)
        dev = os.path.basename(os.readlink(NET_DEV_PATH.format(ifname)))
        pci_link = os.readlink(VIRTIO_DEVS_PATH + dev)

        pci_addr = os.path.basename(os.path.dirname(pci_link))

        pci_driver_link = os.readlink(VIRTIO_PCI_PATH + pci_addr + "/driver")
        pci_driver = os.path.basename(pci_driver_link)

        return pci_driver, pci_addr

    def _change_driver_binding(self, pci_addr, uio_driver):
        LOG.debug("Binding device %s to driver %s", pci_addr, uio_driver)
        devbind = CONF.nested_dpdk.dpdk_devbind
        if not os.path.exists(devbind):
                raise RuntimeError(
                    ("Unable to find dpdk-devbind script: %s") % devbind)
        try:
            # NOTE: using the force flag shouldn't be needed as the interface
            #       should be in the down state
            subprocess.check_call([devbind, "-b", uio_driver, pci_addr])
        except subprocess.CalledProcessError as err:
            LOG.error("Error binding PCI device %s to driver %s", pci_addr,
                      uio_driver)
            raise err

    def _set_vif(self, vif):
        # TODO(ivc): extract annotation interactions
        if vif is None:
            LOG.debug("Removing VIF annotation: %r", vif)
            annotation = None
        else:
            vif.obj_reset_changes(recursive=True)
            LOG.debug("Setting DPDK VIF annotation: %r", vif)
            annotation = jsonutils.dumps(vif.obj_to_primitive(),
                                         sort_keys=True)
        k8s = clients.get_kubernetes_client()
        k8s.annotate(vif.selflink,
                     {constants.K8S_ANNOTATION_VIF: annotation},
                     resource_version=None)

    def _get_vif(self, selflink):
        # TODO(ivc): same as '_set_vif'

        k8s = clients.get_kubernetes_client()
        pod = k8s.get(selflink)

        try:
            annotations = pod['metadata']['annotations']
            vif_annotation = annotations[constants.K8S_ANNOTATION_VIF]
        except KeyError:
            return None
        vif_dict = jsonutils.loads(vif_annotation)
        vif = obj_vif.vif.VIFBase.obj_from_primitive(vif_dict)
        LOG.debug("Got DPDK VIF from annotation: %r", vif)
        return vif
