#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
import cherrypy
import json
import os
import redis
from cherrypy import expose
from xml.sax.saxutils import escape

READ_COMMANDS = \
    'hexists hlen hget hgetall exists type scan randomkey keys ttl pttl get mget strlen getrange getbit bitcount llen lindex lrange info time dbsize echo ping'.split()


class Root(object):

    @staticmethod
    def parse_cmd(cmd):
        parts = cmd.strip().split()
        return parts[0], parts[1:]

    @expose
    def autocomplete(self, query):
        return json.dumps({'query': query, 'suggestions': [cmd for cmd in READ_COMMANDS if query in cmd]})

    @expose
    def index(self, cmd=None):

        host = 'localhost'
        port = 6379
        yield '<script type="text/javascript" src="static/js/jquery-2.1.1.min.js"></script>'
        yield '<script type="text/javascript" src="static/js/jquery.autocomplete.min.js"></script>'
        yield '<form method="POST">{host}:{port}&gt; <input name="cmd"/><a href="http://redis.io/commands">?</a></form>'.format(host=host,
                port=port)
        if cmd:
            cmd, args = self.parse_cmd(cmd)
            con = redis.StrictRedis(host, port)
            yield '<pre>'
            try:
                if cmd not in READ_COMMANDS:
                    raise ValueError('Invalid command')
                result = con.execute_command(cmd, *args)
                if cmd == 'info':
                    yield escape(result)
                else:
                    yield escape(json.dumps(result))
            except Exception, e:
                yield escape(str(e))

            yield '</pre>'
        yield '''<script>var options, a;
jQuery(function(){
    options = { serviceUrl:'autocomplete' };
    a = $('input').autocomplete(options);
}); </script>'''


current_dir = os.path.dirname(os.path.abspath(__file__))
conf = {'/static': {'tools.staticdir.on': True, 'tools.staticdir.dir': os.path.join(current_dir, 'static')}}
cherrypy.quickstart(Root(), '/', config=conf)
