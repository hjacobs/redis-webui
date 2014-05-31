#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
from redisconn import Connection, WRITE_COMMANDS, READ_COMMANDS
import cherrypy
import json
import os
import redis
from jinja import loader
from cherrypy import expose


@loader.add_filter
def dummy(s):
    return s

jinja = cherrypy.tools.jinja


class RootController(object):

    @staticmethod
    def parse_cmd(cmd):
        parts = cmd.strip().split()
        return parts[0].upper(), parts[1:]

    @expose
    def autocomplete(self, query):
        return json.dumps({'query': query, 'suggestions': sorted([cmd for cmd in READ_COMMANDS | WRITE_COMMANDS
                          if query.upper() in cmd])})

    def get_connections(self, user):
        for grp in user.groupnames:
            yield Connection.from_group_name(grp)

    def has_access(self, user, conn, cmd):
        if cmd in READ_COMMANDS:
            roles = 'reader', 'writer'
        elif cmd in WRITE_COMMANDS:
            roles = 'writer',
        else:
            raise ValueError('Unsupported Redis command')
        for suff in roles:
            if '{}-{}'.format(conn.group_name_prefix(), suff) in user.groupnames:
                return True
        return False

    @expose
    @jinja(tpl='index.html')
    def index(self, connection=None, cmd=None):

        user = cherrypy.session.get('user')

        if not user:
            raise cherrypy.HTTPError(403, 'No user in session. Probably authentication was not configured.')

        result = None

        connections = list(self.get_connections(user))

        if not connections:
            raise cherrypy.HTTPError(403,
                                     'No Redis database connection is configured for you. Probably you are lacking the right LDAP groups.'
                                     )

        args = None
        if connection and cmd:
            connection = Connection.from_str(connection)

            cmd, args = self.parse_cmd(cmd)

            if cmd not in READ_COMMANDS | WRITE_COMMANDS:
                raise cherrypy.HTTPError(400, 'Unsupported Redis command')

            if not self.has_access(user, connection, cmd):
                raise cherrypy.HTTPError(403,
                                         'You are not allowed to execute the command "{}" on Redis database "{}"'.format(cmd,
                                         connection))

            con = redis.StrictRedis(connection.host, connection.port, connection.db)
            try:
                if cmd not in READ_COMMANDS:
                    raise ValueError('Invalid command')
                result = con.execute_command(cmd, *args)
                result = json.dumps(result, indent=4)
            except Exception, e:
                result = str(e)

        return {
            'result': result,
            'connections': connections,
            'connection': connection,
            'user': user,
            'cmd': cmd,
            'args': args,
        }


current_dir = os.path.dirname(os.path.abspath(__file__))
conf = {'/': {'tools.sessions.on': True}, '/static': {'tools.staticdir.on': True,
        'tools.staticdir.dir': os.path.join(current_dir, 'static')}}
cherrypy.quickstart(RootController(), '/', config=conf)
