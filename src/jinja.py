#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cherrypy
import colorsys
import datetime
import jinja2
import os
import string
import sys
import urllib

__all__ = ['jinja_render', 'loader']

dir_path = os.path.abspath(os.path.dirname(sys.argv[0]))

CSRF_TOKEN_CHARS = string.ascii_letters + string.digits + '.-'
# TODO: Remove empty user-agent once cmdb-client is updated on every host. The latest version sets the correct
# user-agent string, while the previous one was often empty.
ALLOWED_USER_AGENTS = ['libwww-perl', 'python-urllib', 'cmdb-client', '']


def jinja_render(tpl, context):
    context.update({'request': cherrypy.request, 'app_url': cherrypy.request.app.script_name,
                   'now': datetime.datetime.now()})
    cherrypy.request.template = tmpl = cherrypy.request.jinja_env.get_template(tpl)
    output = tmpl.render(**context)
    return output


class JinjaHandler(cherrypy.dispatch.LateParamPageHandler):

    """Callable which sets response.body."""

    def __init__(self, env, template_name, next_handler):
        self.env = env
        self.template_name = template_name
        self.next_handler = next_handler

    def __call__(self, *args, **kwargs):
        context = {}
        cherrypy.request.jinja_env = self.env
        r = self.next_handler(*args, **kwargs)
        try:
            context.update(r)
        except ValueError, e:
            cherrypy.log('%s (handler for "%s" returned "%s")\n' % (e, self.template_name, repr(r)), traceback=True)

        # We wait until this point to do any tasks related to template
        # loading or context building, as it may not be necessary if
        # the first handler causes a response and we never render
        # the template. (Minor Optimization)
        if cherrypy.config.get('template.show_errors', False):
            self.env.undefined = jinja2.DebugUndefined

        return jinja_render(self.template_name.replace('%s', context.get('template', '')), context)


class JinjaLoader(object):

    """A CherryPy 3 Tool for loading Jinja templates."""

    def __init__(self):
        self.template_dir_list = []
        self.env = jinja2.Environment(loader=jinja2.ChoiceLoader(self.template_dir_list), line_statement_prefix='#',
                                      line_comment_prefix='##')
        self.add_template_dir(os.path.join(dir_path, 'templates'))

    def __call__(self, tpl):
        cherrypy.request.handler = JinjaHandler(self.env, tpl, cherrypy.request.handler)

    def add_template_dir(self, directory):
        """Used to add a template directory to the jinja source path."""

        ldr = jinja2.FileSystemLoader(directory)
        self.template_dir_list.insert(0, ldr)
        self.env.loader = jinja2.ChoiceLoader(self.template_dir_list)

    def add_filter(self, func):
        """Decorator which adds the given function to jinja's filters."""

        self.env.filters[func.__name__] = func
        return func

    def add_global(self, func):
        """Decorator which adds the given function to jinja's globals."""

        self.env.globals[func.__name__] = func
        return func


def check_csrf():
    if cherrypy.request.method == 'POST':
        if 'csrf_token' not in cherrypy.request.params:
            if not any(ua in cherrypy.request.headers.get('User-Agent', '').lower().strip() for ua in
                       ALLOWED_USER_AGENTS):
                raise cherrypy.HTTPError(400, 'Bad Request')
        else:
            if cherrypy.request.params['csrf_token'] != cherrypy.session['csrf_token']:
                raise cherrypy.HTTPError(400, 'Bad Request')
            else:
                del cherrypy.request.params['csrf_token']


loader = JinjaLoader()
cherrypy.tools.jinja = cherrypy.Tool('on_start_resource', loader)
cherrypy.tools.csrf = cherrypy.Tool('before_handler', check_csrf)


@loader.add_global
def csrf_token():
    '''generate a completely random 32 char token'''

    token = cherrypy.session.get('csrf_token', '')
    if token:
        return token
    for i in range(32):
        token += CSRF_TOKEN_CHARS[ord(os.urandom(1)) % len(CSRF_TOKEN_CHARS)]
    cherrypy.session['csrf_token'] = token
    return token


@loader.add_filter
def durationformat(d):
    if isinstance(d, datetime.timedelta):
        d = d.seconds + d.days * 24 * 3600
    if d > 3600 * 48:
        return '%.0f d' % (d / (3600. * 24), )
    if d > 3600:
        return '%.0f h' % (d / 3600., )
    if d > 60:
        return '%.0f m' % (d / 60., )
    return '%d s' % (d, )


@loader.add_filter
def dtformat(d, longformat=False):
    if d:
        val = (d if hasattr(d, 'strftime') else datetime.datetime.fromtimestamp(int(d)))
        return (val.strftime('%Y-%m-%d %H:%M:%S') if longformat else val.strftime('%Y-%m-%d %H:%M'))
    else:
        return d


@loader.add_filter
def ago(d):
    if not d:
        return d
    d = datetime.datetime.now() - d
    d = d.seconds + d.days * 24 * 3600
    if d > 3600 * 48:
        return '%.0f d ago' % (d / (3600. * 24), )
    if d > 3600:
        return '%.0f h ago' % (d / 3600., )
    if d > 60:
        return '%.0f m ago' % (d / 60., )
    return '%d s ago' % (d, )


@loader.add_filter
def ago_color(d, days=7, error=False):
    if not d:
        return 'ffffff'
    d = datetime.datetime.now() - d
    d = d.seconds + d.days * 24 * 3600
    v = max(0, 1.0 - d / (days * 24. * 3600))
    if error and v <= 0:
        return 'f99'
    r, g, b = colorsys.hsv_to_rgb(0.3, v * 0.5, 0.9)
    return '%02x%02x%02x' % (r * 255, g * 255, b * 255)


@loader.add_filter
def firstword(s):
    return s.split()[0].strip(',')


@loader.add_filter
def url(s):
    if type(s) in (str, unicode):
        u = s
    else:
        u = '/'.join(map(lambda x: urllib.quote_plus(x.encode('utf-8').replace('/', '-.-')), s))
    return cherrypy.url(u)


@loader.add_filter
def n(s):
    return (s if s else '')


@loader.add_filter
def price(p):
    if p < 0:
        # important: integer division truncation works different for negative values!
        p = p * -1
        return '-%d.%02d' % (p / 100, p % 100)
    else:
        return '%d.%02d' % (p / 100, p % 100)
