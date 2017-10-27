import json
import sys
import random
import string
import logging
import datetime
import time

import robot
from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn

from keystoneauth1.identity import v3
from keystoneauth1 import session as kssession
from keystoneclient.v3 import client as ksclient

from novaclient import client as nvclient
from neutronclient.v2_0 import client as ntclient
from novaclient.exceptions import NotFound
from heatclient import client as htclient
from glanceclient import client as gcclient

NOVA_API_VERSION=2
HEAT_API_VERSION='1'
GLANCE_API_VERSION='2'

class OpenStackKeywords(object):
    ROBOT_LIBRARY_SCOPE = 'GLOBAL'
    
    def __init__(self):
        self._cache = robot.utils.ConnectionCache('No sessions created')
        self.builtin = BuiltIn()
        self.debug = 0

    def create_session(self, alias, auth_url, username, password, project_name, domain='default',
                       verify=True):

        """ Create Session: create a session to OpenStack
        `alias` Robot Framework alias to identify the session
        `auth_url` Auth url of the server, e.g. https://my.keystone.com:5000/v3
        `verify` set to CA cert path if the client should verify the certificate
        """

        self.builtin.log('Creating session: %s' % alias, 'DEBUG')
        auth = v3.Password(auth_url=auth_url,
                           username=username,
                           password=password,
                           project_name=project_name,
                           #domain_name=domain,
                           user_domain_name = domain,
                           project_domain_name = domain
                           )
        sess = kssession.Session(auth=auth, verify = verify)
        #self.builtin.log('Created session: %s' % sess.auth.__dict__, 'DEBUG')
        #ks = ksclient.Client(session=sess)
        #users = ks.projects.list()
        #self.builtin.log('Users: %s' % users, 'DEBUG')
        self._cache.register(sess, alias=alias)
        return sess

    def delete_all_sessions(self):
        """Removes all the session objects"""

        self._cache.empty_cache()

    def create_project(self, alias, project_name, domain='default'):
        self.builtin.log('Creating project: %s' % project_name, 'DEBUG')
        session = self._cache.switch(alias)
        ks = ksclient.Client(session=session)
        return ks.projects.create(project_name, domain)
        
    def delete_project(self, alias, project_name):
        self.builtin.log('Deleting project: %s' % project_name, 'DEBUG')
        session = self._cache.switch(alias)
        ks = ksclient.Client(session=session)
        ks.projects.delete(project_name)

    def get_project(self, alias, project_name, domain='default'):
        self.builtin.log('Getting project: %s' % project_name, 'DEBUG')
        session = self._cache.switch(alias)
        ks = ksclient.Client(session=session)
        projects = ks.projects.list(domain=domain)
        for project in projects:
            if project.name == project_name:
                return project
        return None

    def create_user(self, alias, user_name, project, domain='default', password=None, global_var_name=None):
        self.builtin.log('Creating user: %s' % user_name, 'DEBUG')
        session = self._cache.switch(alias)
        ks = ksclient.Client(session=session)
        if password is None:
            password=''.join(random.SystemRandom().choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
        if global_var_name is not None:
            self.builtin.set_global_variable(global_var_name, password)
        return ks.users.create(user_name, domain=domain, project=project, password=password)
    
    def get_user(self, alias, user_name, project_name):
        self.builtin.log('Getting user: %s of project %s' % (user_name, project_name), 'DEBUG')
        session = self._cache.switch(alias)
        ks = ksclient.Client(session=session)
        users = ks.users.list(project=project_name)
        for user in users:
            if user.name == user_name:
                return user
        return None

    def delete_user(self, alias, user_id):
        self.builtin.log('Deleting user: %s' % user_id, 'DEBUG')
        session = self._cache.switch(alias)
        ks = ksclient.Client(session=session)
        ks.users.delete(user_id)
        
    def create_flavor(self, alias, flavor_name, ram=2048, vcpus=1, disk=20):
        self.builtin.log('Creating flavor: %s' % flavor_name, 'DEBUG')
        session = self._cache.switch(alias)
        nova = nvclient.Client(NOVA_API_VERSION, session=session)
        return nova.flavors.create(flavor_name, ram, vcpus, disk)
    
    def delete_flavor(self, alias, flavor_id):
        self.builtin.log('Deleting flavor: %s' % flavor_id, 'DEBUG')
        session = self._cache.switch(alias)
        nova = nvclient.Client(NOVA_API_VERSION, session=session)
        nova.flavors.delete(flavor_id)

    def create_network(self, alias, network_name, physical_network=None, segmentation_id=None):
        self.builtin.log('Creating network: %s' % network_name, 'DEBUG')
        session = self._cache.switch(alias)
        neutron = ntclient.Client(session=session)
        network = {'name': network_name, 'admin_state_up': True}
        if physical_network is not None:
            network['provider:physical_network']=physical_network
        if segmentation_id is not None:
            network['provider:segmentation_id ']=segmentation_id
        return neutron.create_network({'network': network})

    def create_subnet(self, alias, network_id, subnet_name, cidr, ip_version=4, enable_dhcp=True):
        self.builtin.log('Creating subnet: %s' % subnet_name, 'DEBUG')
        session = self._cache.switch(alias)
        neutron = ntclient.Client(session=session)
        subnet = {"network_id": network_id, 'name': subnet_name, 'ip_version': ip_version, 'cidr': cidr, 'enable_dhcp': enable_dhcp}
        return neutron.create_subnet({'subnet': subnet})

    def create_port(self, alias, port_name, network_id):
        self.builtin.log('Creating port: %s' % port_name, 'DEBUG')
        session = self._cache.switch(alias)
        neutron = ntclient.Client(session=session)
        port = {"network_id": network_id, 'name': port_name, 'admin_state_up': True}
        return neutron.create_port({'port': port})

    def list_networks(self, alias, project_id):
        self.builtin.log('Listing networks', 'DEBUG')
        session = self._cache.switch(alias)
        neutron = ntclient.Client(session=session)
        query = {"project_id": project_id}
        return neutron.list_networks(retrieve_all=True, **query)

    def list_subnets(self, alias, project_id):
        self.builtin.log('Listing subnets', 'DEBUG')
        session = self._cache.switch(alias)
        neutron = ntclient.Client(session=session)
        query = {"project_id": project_id}
        return neutron.list_subnets(retrieve_all=True, **query)

    def list_ports(self, alias, project_id):
        self.builtin.log('Listing ports', 'DEBUG')
        session = self._cache.switch(alias)
        neutron = ntclient.Client(session=session)
        query = {"project_id": project_id}
        return neutron.list_ports(retrieve_all=True, **query)

    def list_security_groups(self, alias, project_id):
        self.builtin.log('Listing security groups', 'DEBUG')
        session = self._cache.switch(alias)
        neutron = ntclient.Client(session=session)
        query = {"project_id": project_id}
        return neutron.list_security_groups(retrieve_all=True, **query)

    def list_security_group_rules(self, alias, project_id):
        self.builtin.log('Listing security group rules', 'DEBUG')
        session = self._cache.switch(alias)
        neutron = ntclient.Client(session=session)
        query = {"project_id": project_id}
        return neutron.list_security_group_rules(retrieve_all=True, **query)

    def delete_port(self, alias, port_id):
        self.builtin.log('Deleting port: %s' % port_id, 'DEBUG')
        session = self._cache.switch(alias)
        neutron = ntclient.Client(session=session)
        neutron.delete_port(port_id)

    def delete_subnet(self, alias, subnet_id):
        self.builtin.log('Deleting subnet: %s' % subnet_id, 'DEBUG')
        session = self._cache.switch(alias)
        neutron = ntclient.Client(session=session)
        neutron.delete_subnet(subnet_id)

    def delete_network(self, alias, network_id):
        self.builtin.log('Deleting network: %s' % network_id, 'DEBUG')
        session = self._cache.switch(alias)
        neutron = ntclient.Client(session=session)
        neutron.delete_network(network_id)

    def add_role_to_user(self, alias, role, user, project):
        self.builtin.log('Adding role %s to user %s of project %s' % (role,user,project), 'DEBUG')
        session = self._cache.switch(alias)
        ks = ksclient.Client(session=session)
        ks.roles.grant(role, user=user, project=project)
        
    def get_role(self, alias, role_name):
        self.builtin.log('Getting role: %s' % role_name, 'DEBUG')
        session = self._cache.switch(alias)
        ks = ksclient.Client(session=session)
        roles = ks.roles.list()
        for role in roles:
            if role.name == role_name:
                return role
        return None

    def update_network_quota(self, alias, project_id, networks, subnets, ports, security_group, security_group_rule):
        self.builtin.log('Updating network quota: %s' % project_id, 'DEBUG')
        session = self._cache.switch(alias)
        neutron = ntclient.Client(session=session)
        quota = {"network": networks, "port": ports, "subnet": subnets, "security_group": security_group, "security_group_rule": security_group_rule}
        neutron.update_quota(project_id, {'quota': quota})

    def update_compute_quota(self, alias, project_id, instances, cores, ram):
        self.builtin.log('Updating compute quota: %s' % project_id, 'DEBUG')
        session = self._cache.switch(alias)
        nova = nvclient.Client(NOVA_API_VERSION, session=session)
        nova.quotas.update(project_id, instances=instances, cores=cores, ram=ram)

    def create_server_with_port(self, alias, server_name, image_uuid, flavor, security_group, key_name, port_id, zone='nova', config_drive=True):
        self.builtin.log('Creating servers: %s with port: %s' % (server_name,port_id), 'DEBUG')
        session = self._cache.switch(alias)
        nova = nvclient.Client(NOVA_API_VERSION, session=session)
        nets = []
        nets.append({"port-id":port_id})
        kwargs = {"max_count": 1, "min_count": 1, "key_name": key_name, "security_groups": [security_group], "nics": nets, "config_drive": config_drive, "availability_zone": zone}
        return nova.servers.create(server_name, image_uuid, flavor, **kwargs)

    def create_servers(self, alias, server_name, image_uuid, flavor, count, security_group, networks, zone='nova', config_drive=True):
        self.builtin.log('Creating servers: %s, count: %s' % (server_name,count), 'DEBUG')
        if count < 2:
            self.builtin.log('server count: %s, but it needs to be larger than 1.' % count, 'ERROR')
            raise Exception
        session = self._cache.switch(alias)
        nova = nvclient.Client(NOVA_API_VERSION, session=session)
        nets = []
        for network in networks:
            nets.append({"net-id":network})
        kwargs = {"max_count": count, "min_count": count, "security_groups": [security_group], "nics": nets, "config_drive": config_drive, "availability_zone": zone}
        nova.servers.create(server_name, image_uuid, flavor, **kwargs)

    def check_servers(self, alias, server_name, console, timeout):
        self.builtin.log('Checking servers: %s' % server_name, 'DEBUG')
        session = self._cache.switch(alias)
        nova = nvclient.Client(NOVA_API_VERSION, session=session)
        servers = nova.servers.list(search_opts={"name": server_name + "-*"})
        start_timestamp = int(datetime.datetime.now().strftime("%s"))
        current_timestamp = int(datetime.datetime.now().strftime("%s"))
        ready = []
        errors = []
        while current_timestamp - start_timestamp < timeout and len(servers) > 0:
            for svr in servers:
                server = nova.servers.get(svr.id)
                self.builtin.log('server: %s, status: %s' % (server.id, server.status), 'DEBUG')
                if server.status == "ACTIVE":
                    console_log = server.get_console_output()
                    #self.builtin.log('console log of %s: %s' % (server.id, console_log[-30:]), 'DEBUG')
                    if console in console_log:
                        self.builtin.log('%s is active and booted. time left: %s' % (server.id, current_timestamp - start_timestamp), 'DEBUG')
                        ready.append(server)
                elif server.status == "ERROR" or getattr(server,"OS-EXT-STS:vm_state") == "error":
                    self.builtin.log('%s is in error state. time elapsed: %s' % (server.id, current_timestamp - start_timestamp), 'DEBUG')
                    errors.append(server)
            for server in ready:
                if server in servers:
                    servers.remove(server)
            for server in errors:
                if server in servers:
                    servers.remove(server)
            time.sleep(10)
            current_timestamp = int(datetime.datetime.now().strftime("%s"))
        failed = False
        if len(errors) > 0:
            self.builtin.log('%s servers are in error state.' % len(errors), 'ERROR')
        if len(servers) > 0:
            self.builtin.log('Creation of %s servers has timed out.' % len(servers), 'ERROR')
        if failed:
            raise Exception
        return ready

    def delete_servers(self, alias, server_name, timeout):
        self.builtin.log('Deleting servers: %s' % server_name, 'DEBUG')
        session = self._cache.switch(alias)
        nova = nvclient.Client(NOVA_API_VERSION, session=session)
        servers = nova.servers.list(search_opts={"name": server_name + "-*"})
        start_timestamp = int(datetime.datetime.now().strftime("%s"))
        current_timestamp = int(datetime.datetime.now().strftime("%s"))
        deleted = []
        while current_timestamp - start_timestamp < timeout and len(servers) > 0:
            for server in servers:
                try:
                    self.builtin.log('delete server %s ...' % server.id, 'DEBUG')
                    nova.servers.delete(server)
                except NotFound as ex:
                    self.builtin.log('%s is deleted. time elapsed: %s' % (server.id, current_timestamp - start_timestamp), 'DEBUG')
                    deleted.append(server)
            for server in deleted:
                if server in servers:
                    servers.remove(server)
            time.sleep(10)
            current_timestamp = int(datetime.datetime.now().strftime("%s"))

    def get_compute_usage(self, alias, project_id):
        self.builtin.log('Getting compute usage for project: %s' % project_id, 'DEBUG')
        session = self._cache.switch(alias)
        nova = nvclient.Client(NOVA_API_VERSION, session=session)
        limits = nova.limits.get(tenant_id=project_id)
        rt = {}
        for limit in limits.absolute:
            rt[limit.name] = limit.value
        return rt

    def create_stacks(self, alias, project_id, template, stack_name, num_stacks = 1):
        self.builtin.log('Creating %s stacks' % num_stacks, 'DEBUG')
        session = self._cache.switch(alias)
        heat = htclient.Client(HEAT_API_VERSION, session=session, service_type='orchestration')
        stacks=[]
        for i in range(1,int(num_stacks)+1):
            fields = {'tenant_id': project_id, 'stack_name': stack_name+'-'+str(i), 'template': template}
            stacks.append(heat.stacks.create(**fields))
        return stacks
    
    def check_stacks(self, alias, project_id, stack_name, timeout):
        self.builtin.log('Checking stacks: %s' % stack_name, 'DEBUG')
        session = self._cache.switch(alias)
        heat = htclient.Client(HEAT_API_VERSION, session=session, service_type='orchestration')
        start_timestamp = int(datetime.datetime.now().strftime("%s"))
        current_timestamp = int(datetime.datetime.now().strftime("%s"))
        completed = False
        body = {'tenant_id': project_id}
        while current_timestamp - start_timestamp < timeout and not completed:
            stacks = heat.stacks.list(**body)
            total_stacks = 0
            completed_stacks = 0
            failed_stacks = 0
            for stack in stacks:
                if str(stack.stack_name).startswith(stack_name+'-'):
                    total_stacks += 1
                    if stack.status == "COMPLETE":
                        completed_stacks += 1
                    elif stack.status == "FAILED":
                        failed_stacks += 1
            if total_stacks == completed_stacks:
                completed = True
            elif failed_stacks == total_stacks or total_stacks == failed_stacks+completed_stacks:
                raise Exception
            else:
                time.sleep(5)
                current_timestamp = int(datetime.datetime.now().strftime("%s"))
        if not completed:
            raise Exception
        return completed_stacks
                
    def delete_stacks(self, alias, project_id, stack_name, timeout):
        self.builtin.log('Deleting stacks: %s' % stack_name, 'DEBUG')
        session = self._cache.switch(alias)
        heat = htclient.Client(HEAT_API_VERSION, session=session, service_type='orchestration')
        start_timestamp = int(datetime.datetime.now().strftime("%s"))
        current_timestamp = int(datetime.datetime.now().strftime("%s"))
        completed = False
        body = {'tenant_id': project_id}
        while current_timestamp - start_timestamp < timeout and not completed:
            stacks = heat.stacks.list(**body)
            total_stacks = 0
            for stack in stacks:
                if str(stack.stack_name).startswith(stack_name+'-'):
                    total_stacks += 1
                    stack.delete()
            if total_stacks > 0:
                time.sleep(5)
                current_timestamp = int(datetime.datetime.now().strftime("%s"))
            else:
                completed = True

    def get_hypervisor_statistics(self, alias):
        self.builtin.log('Getting hypervisor statistics', 'DEBUG')
        session = self._cache.switch(alias)
        nova = nvclient.Client(NOVA_API_VERSION, session=session)
        return nova.hypervisors.statistics()

    def create_image(self, alias, image_name, image_path, disk_format='qcow2', container_format='bare'):
        self.builtin.log('Creating image %s' % image_name, 'DEBUG')
        session = self._cache.switch(alias)
        glance = gcclient.Client(GLANCE_API_VERSION, session=session)
        image = glance.images.create(name=image_name, disk_format=disk_format, container_format=container_format)
        glance.images.upload(image.id, open(image_path, 'rb'))
        return image
    
    def delete_image(self, alias, image_id):
        self.builtin.log('Deleting image %s' % image_id, 'DEBUG')
        session = self._cache.switch(alias)
        glance = gcclient.Client(GLANCE_API_VERSION, session=session)
        glance.images.delete(image_id)
