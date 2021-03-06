# Copyright 2018 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_log import log as logging

from kuryr_kubernetes import constants as k_const
from kuryr_kubernetes.controller.drivers import base as drivers
from kuryr_kubernetes.handlers import k8s_base

LOG = logging.getLogger(__name__)


class NetworkPolicyHandler(k8s_base.ResourceEventHandler):
    """NetworkPolicyHandler handles k8s Network Policies events"""

    OBJECT_KIND = k_const.K8S_OBJ_POLICY
    OBJECT_WATCH_PATH = k_const.K8S_API_POLICIES

    def __init__(self):
        super(NetworkPolicyHandler, self).__init__()
        self._drv_policy = drivers.NetworkPolicyDriver.get_instance()
        self._drv_project = drivers.NetworkPolicyProjectDriver.get_instance()

    def on_present(self, policy):
        LOG.debug("Created or updated: %s", policy)
        project_id = self._drv_project.get_project(policy)
        self._drv_policy.ensure_network_policy(policy, project_id)

    def on_deleted(self, policy):
        LOG.debug("Deleted network policy: %s", policy)
        project_id = self._drv_project.get_project(policy)
        self._drv_policy.release_network_policy(policy, project_id)
