import json
import sys
import random
import string
import logging
import datetime

import robot
from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn

from keystoneauth1.identity import v3
from keystoneauth1 import session as kssession
from keystoneclient.v3 import client as ksclient

from novaclient import client as nvclient
from neutronclient.v2_0 import client as ntclient
from novaclient.exceptions import NotFound

NOVA_API_VERSION=2

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

    def create_servers(self, alias, server_name, image_uuid, flavor, count, security_group, networks, config_drive=True):
        self.builtin.log('Creating servers: %s, count: %s' % (server_name,count), 'DEBUG')
        if count < 2:
            self.builtin.log('server count: %s, but it needs to be larger than 1.' % count, 'ERROR')
            raise Exception
        session = self._cache.switch(alias)
        nova = nvclient.Client(NOVA_API_VERSION, session=session)
        nets = []
        for network in networks:
            nets.append({"net-id":network})
        kwargs = {"max_count": count, "min_count": count, "security_groups": [security_group], "nics": nets, "config_drive": config_drive}
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
        while current_timestamp - start_timestamp < timeout:
            for server in servers:
                if server.status == "ACTIVE":
                    console_log = server.get_console_output()
                    if console in console_log:
                        self.builtin.log('%s is active and booted.' % server.id, 'DEBUG')
                        ready.append(server)
                elif server.status == "ERROR":
                    self.builtin.log('%s is in error state.' % server.id, 'DEBUG')
                    errors.append(server)
                server.update()
            current_timestamp = int(datetime.datetime.now().strftime("%s"))
        failed = False
        if len(errors) + len(servers) > 0:
            self.builtin.log('%s servers are in error state.' % len(errors), 'ERROR')
        if len(errors) + len(ready) < len(servers):
            self.builtin.log('%s servers are timeout.' % (len(servers)-len(errors)-len(ready)), 'ERROR')
        start_timestamp = int(datetime.datetime.now().strftime("%s"))
        current_timestamp = int(datetime.datetime.now().strftime("%s"))
        deleted = []
        while current_timestamp - start_timestamp < timeout*1000:
            for server in servers:
                nova.servers.delete(server)
                try:
                    nova.servers.update(server)
                except NotFound as ex:
                    self.builtin.log('%s is deleted.' % server.id, 'DEBUG')
                    deleted.append(server)
            for server in deleted:
                servers.remove(server)
            current_timestamp = int(datetime.datetime.now().strftime("%s"))
        if failed:
            raise Exception
