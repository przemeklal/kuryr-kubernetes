# Copyright (c) 2016 Mirantis, Inc.
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

from kuryr.lib import config as kuryr_config
from kuryr.lib import utils
from kuryr_kubernetes import config
from kuryr_kubernetes import k8s_client
from neutronclient import client as n_client
from novaclient import client as nova_client
from oslo_config import cfg

_clients = {}
_NOVA_CLIENT = 'nova-client'
_NEUTRON_CLIENT = 'neutron-client'
_LB_CLIENT = 'load-balancer-client'
_KUBERNETES_CLIENT = 'kubernetes-client'


def get_neutron_client():
    return _clients[_NEUTRON_CLIENT]


def get_loadbalancer_client():
    return _clients[_LB_CLIENT]


def get_kubernetes_client():
    return _clients[_KUBERNETES_CLIENT]


def get_nova_client():
    return _clients[_NOVA_CLIENT]


def setup_clients():
    setup_neutron_client()
    setup_loadbalancer_client()
    setup_nova_client()
    setup_kubernetes_client()


def setup_neutron_client():
    _clients[_NEUTRON_CLIENT] = utils.get_neutron_client()


def setup_loadbalancer_client():
    neutron_client = get_neutron_client()
    if any(ext['alias'] == 'lbaasv2' for
           ext in neutron_client.list_extensions()['extensions']):
        _clients[_LB_CLIENT] = neutron_client
        neutron_client.cascading_capable = False
    else:
        # Since Octavia is lbaasv2 API compatible (A superset of it) we'll just
        # wire an extra neutron client instance to point to it
        lbaas_client = utils.get_neutron_client()
        conf_group = utils.kuryr_config.neutron_group.name
        auth_plugin = utils.get_auth_plugin(conf_group)
        octo_httpclient = n_client.construct_http_client(
            session=utils.get_keystone_session(conf_group, auth_plugin),
            service_type='load-balancer')
        lbaas_client.httpclient = octo_httpclient
        _clients[_LB_CLIENT] = lbaas_client
        lbaas_client.cascading_capable = True


def setup_kubernetes_client():
    if config.CONF.kubernetes.api_root:
        api_root = config.CONF.kubernetes.api_root
    else:
        # NOTE(dulek): This is for containerized deployments, i.e. running in
        #              K8s Pods.
        host = os.environ['KUBERNETES_SERVICE_HOST']
        port = os.environ['KUBERNETES_SERVICE_PORT_HTTPS']
        api_root = "https://%s:%s" % (host, port)
    _clients[_KUBERNETES_CLIENT] = k8s_client.K8sClient(api_root)


def setup_nova_client():
    _clients[_NOVA_CLIENT] = _get_nova_client()


# TODO(garyloug): move it elsewhere, e.g. kuryr-lib
def _get_nova_client():
    conf_group = kuryr_config.neutron_group.name
    auth_plugin = utils.get_auth_plugin(conf_group)
    session = utils.get_keystone_session(conf_group, auth_plugin)
    endpoint_type = getattr(getattr(cfg.CONF, conf_group), 'endpoint_type')

    return nova_client.Client("2.1", session=session, auth=auth_plugin,
                              endpoint_type=endpoint_type)
