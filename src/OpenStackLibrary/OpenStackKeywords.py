import json
import sys
import random
import string
import logging

import robot
from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn

from keystoneauth1.identity import v3
from keystoneauth1 import session as kssession
from keystoneclient.v3 import client as ksclient

class OpenStackKeywords(object):
    ROBOT_LIBRARY_SCOPE = 'Global'
    
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
        ks.projects.create(project_name, domain)
        
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

    def create_user(self, alias, user_name, project, domain='default', password=None):
        self.builtin.log('Creating user: %s' % user_name, 'DEBUG')
        session = self._cache.switch(alias)
        ks = ksclient.Client(session=session)
        if password is None:
            password=''.join(random.SystemRandom().choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
        ks.users.create(user_name, domain=domain, project=project, password=password)
        return password
    
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