# Copyright (c) 2015 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function
import time

import fixtures
from glanceclient import client as glance_client
from keystoneauth1.identity import v3 as identity_v3
from keystoneauth1 import session
from neutronclient.neutron import client as neutron_client
from novaclient import client as nova_client
from novaclient import exceptions as nova_exc
from oslo_utils import uuidutils
from saharaclient.api import base as saharaclient_base
from saharaclient import client as sahara_client
from swiftclient import client as swift_client
from swiftclient import exceptions as swift_exc
from tempest.lib import exceptions as exc

from sahara_tests.scenario import timeouts
from sahara_tests.scenario import utils


def get_session(auth_url=None, username=None, password=None,
                project_name=None, verify=True, cert=None):
    auth = identity_v3.Password(auth_url=auth_url.replace('/v2.0', '/v3'),
                                username=username,
                                password=password,
                                project_name=project_name,
                                user_domain_name='default',
                                project_domain_name='default')
    return session.Session(auth=auth, verify=verify, cert=cert)


class Client(object):
    def is_resource_deleted(self, method, *args, **kwargs):
        raise NotImplementedError

    def delete_resource(self, method, *args, **kwargs):
        with fixtures.Timeout(
                timeouts.Defaults.instance.timeout_delete_resource,
                gentle=True):
            while True:
                if self.is_resource_deleted(method, *args, **kwargs):
                    break
                time.sleep(5)


class SaharaClient(Client):
    def __init__(self, *args, **kwargs):
        self.sahara_client = sahara_client.Client('1.1', *args, **kwargs)

    def create_node_group_template(self, *args, **kwargs):
        data = self.sahara_client.node_group_templates.create(*args, **kwargs)
        return data.id

    def delete_node_group_template(self, node_group_template_id):
        return self.delete_resource(
            self.sahara_client.node_group_templates.delete,
            node_group_template_id)

    def create_cluster_template(self, *args, **kwargs):
        data = self.sahara_client.cluster_templates.create(*args, **kwargs)
        return data.id

    def delete_cluster_template(self, cluster_template_id):
        return self.delete_resource(
            self.sahara_client.cluster_templates.delete,
            cluster_template_id)

    def create_cluster(self, *args, **kwargs):
        data = self.sahara_client.clusters.create(*args, **kwargs)
        return data.id

    def delete_cluster(self, cluster_id):
        return self.delete_resource(
            self.sahara_client.clusters.delete,
            cluster_id)

    def scale_cluster(self, cluster_id, body):
        return self.sahara_client.clusters.scale(cluster_id, body)

    def start_cluster_verification(self, cluster_id):
        return self.sahara_client.clusters.verification_update(cluster_id,
                                                               'START')

    def create_datasource(self, *args, **kwargs):
        data = self.sahara_client.data_sources.create(*args, **kwargs)
        return data.id

    def get_datasource(self, *args, **kwargs):
        return self.sahara_client.data_sources.get(*args, **kwargs)

    def delete_datasource(self, datasource_id):
        return self.delete_resource(
            self.sahara_client.data_sources.delete,
            datasource_id)

    def create_job_binary_internal(self, *args, **kwargs):
        data = self.sahara_client.job_binary_internals.create(*args, **kwargs)
        return data.id

    def delete_job_binary_internal(self, job_binary_internal_id):
        return self.delete_resource(
            self.sahara_client.job_binary_internals.delete,
            job_binary_internal_id)

    def create_job_binary(self, *args, **kwargs):
        data = self.sahara_client.job_binaries.create(*args, **kwargs)
        return data.id

    def delete_job_binary(self, job_binary_id):
        return self.delete_resource(
            self.sahara_client.job_binaries.delete,
            job_binary_id)

    def create_job(self, *args, **kwargs):
        data = self.sahara_client.jobs.create(*args, **kwargs)
        return data.id

    def delete_job(self, job_id):
        return self.delete_resource(
            self.sahara_client.jobs.delete,
            job_id)

    def run_job(self, *args, **kwargs):
        data = self.sahara_client.job_executions.create(*args, **kwargs)
        return data.id

    def delete_job_execution(self, job_execution_id):
        return self.delete_resource(
            self.sahara_client.job_executions.delete,
            job_execution_id)

    def get_cluster(self, cluster_id, show_progress=False):
        return self.sahara_client.clusters.get(cluster_id, show_progress)

    def get_cluster_status(self, cluster_id):
        data = self.sahara_client.clusters.get(cluster_id)
        return str(data.status)

    def get_job_status(self, exec_id):
        data = self.sahara_client.job_executions.get(exec_id)
        return str(data.info['status'])

    def get_job_info(self, exec_id):
        job_execution = self.sahara_client.job_executions.get(exec_id)
        return self.sahara_client.jobs.get(job_execution.job_id)

    def get_cluster_id(self, name):
        if uuidutils.is_uuid_like(name):
            return name
        for cluster in self.sahara_client.clusters.list():
            if cluster.name == name:
                return cluster.id

    def get_node_group_template_id(self, name):
        for nodegroup in self.sahara_client.node_group_templates.list():
            if nodegroup.name == name:
                return nodegroup.id

    def register_image(self, image_id, testcase):
        try:
            return self.sahara_client.images.get(image_id)
        except saharaclient_base.APIException:
            print("Image not registered in sahara. Registering and run tests")
            if testcase.get('image_username') is not None:
                self.sahara_client.images.update_image(
                    image_id, testcase.get('image_username'),
                    "Registered by scenario tests")
                self.sahara_client.images.update_tags(
                    image_id, [testcase["plugin_name"],
                               testcase["plugin_version"]])
            else:
                raise exc.InvalidContentType(
                    "Registering of image failed. Please, specify "
                    "'image_username'. For details see README in scenario "
                    "tests.")
        return self.sahara_client.images.get(image_id)

    def is_resource_deleted(self, method, *args, **kwargs):
        try:
            method(*args, **kwargs)
        except saharaclient_base.APIException as ex:
            return ex.error_code == 404

        return False


class NovaClient(Client):
    def __init__(self, *args, **kwargs):
        self.nova_client = nova_client.Client('2', *args, **kwargs)

    def get_flavor_id(self, flavor_name):
        if (uuidutils.is_uuid_like(flavor_name) or
                (isinstance(flavor_name, str) and flavor_name.isdigit())):
            return flavor_name
        for flavor in self.nova_client.flavors.list():
            if flavor.name == flavor_name:
                return flavor.id

        raise exc.NotFound(flavor_name)

    def create_flavor(self, flavor_object):
        return self.nova_client.flavors.create(
            flavor_object.get('name', utils.rand_name('scenario')),
            flavor_object.get('ram', 1),
            flavor_object.get('vcpus', 1),
            flavor_object.get('root_disk', 0),
            ephemeral=flavor_object.get('ephemeral_disk', 0),
            swap=flavor_object.get('swap_disk', 0),
            flavorid=flavor_object.get('id', 'auto'))

    def delete_flavor(self, flavor_id):
        return self.delete_resource(self.nova_client.flavors.delete, flavor_id)

    def delete_keypair(self, key_name):
        return self.delete_resource(
            self.nova_client.keypairs.delete, key_name)

    def is_resource_deleted(self, method, *args, **kwargs):
        try:
            method(*args, **kwargs)
        except nova_exc.NotFound as ex:
            return ex.code == 404

        return False


class NeutronClient(Client):
    def __init__(self, *args, **kwargs):
        self.neutron_client = neutron_client.Client('2.0', *args, **kwargs)

    def get_network_id(self, network_name):
        if uuidutils.is_uuid_like(network_name):
            return network_name
        networks = self.neutron_client.list_networks(name=network_name)
        networks = networks['networks']
        if len(networks) < 1:
            raise exc.NotFound(network_name)
        return networks[0]['id']

    def create_security_group_for_neutron(self, sg_name):
        security_group = self.neutron_client.create_security_group({
            "security_group":
                {
                    "name": sg_name,
                    "description": "Just for test"
                }
        })
        return security_group['security_group']['id']

    def get_security_group_id(self, sg_name):
        for sg in (self.neutron_client.list_security_groups()
                   ["security_groups"]):
            if sg['name'] == sg_name:
                return sg['id']

        raise exc.NotFound(sg_name)

    def add_security_group_rule_for_neutron(self, sg_id):
        return self.neutron_client.create_security_group_rule({
            "security_group_rules": [
                {
                    "direction": "ingress",
                    "ethertype": "IPv4",
                    "port_range_max": 65535,
                    "port_range_min": 1,
                    "protocol": "TCP",
                    "remote_group_id": None,
                    "remote_ip_prefix": None,
                    "security_group_id": sg_id
                },
                {
                    "direction": "egress",
                    "ethertype": "IPv4",
                    "port_range_max": 65535,
                    "port_range_min": 1,
                    "protocol": "TCP",
                    "remote_group_id": None,
                    "remote_ip_prefix": None,
                    "security_group_id": sg_id
                }
            ]
        })

    def delete_security_group_for_neutron(self, sg_id):
        return self.neutron_client.delete_security_group(sg_id)


class SwiftClient(Client):
    def __init__(self, *args, **kwargs):
        self.swift_client = swift_client.Connection(*args, **kwargs)

    def create_container(self, container_name):
        return self.swift_client.put_container(container_name)

    def delete_container(self, container_name):
        objects = self._get_objects(container_name)
        for obj in objects:
            self.delete_object(container_name, obj)
        return self.delete_resource(
            self.swift_client.delete_container, container_name)

    def _get_objects(self, container_name):
        metadata = self.swift_client.get_container(container_name)
        objects = []
        for obj in metadata[1]:
            objects.append(obj['name'])
        return objects[::-1]

    def upload_data(self, container_name, object_name, data):
        return self.swift_client.put_object(container_name, object_name, data)

    def delete_object(self, container_name, object_name):
        return self.delete_resource(
            self.swift_client.delete_object,
            container_name,
            object_name)

    def is_resource_deleted(self, method, *args, **kwargs):
        try:
            method(*args, **kwargs)
        except swift_exc.ClientException as ex:
            return ex.http_status == 404

        return False


class GlanceClient(Client):
    def __init__(self, *args, **kwargs):
        self.glance_client = glance_client.Client('2', *args, **kwargs)

    def get_image_id(self, image_name):
        if uuidutils.is_uuid_like(image_name):
            return image_name
        for image in self.glance_client.images.list():
            if image.name == image_name:
                return image.id
        raise exc.NotFound(image_name)
