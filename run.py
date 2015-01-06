#!/usr/bin/env python

import sys

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
import tornado.web
from tornado.options import define, options

from jenkins_hookshot.app import JenkinsHookshotApp


def main():
    # jenkins-hookshot options
    define('listening_port', default='8000', help='Listening port')
    define('marathon_host', default='localhost:8080',
           help='Marathon host or load balancer')
    define('marathon_app_id', default='jenkins',
           help='Marathon application ID for the Jenkins master(s)')
    define('redis_host', default='localhost', help='Redis host')

    # GitHub options
    define('github_hook_secret', default=None,
           help='GitHub webhook shared secret')

    # Jenkins options
    define('jenkins_username', default=None,
           help='Jenkins username (if auth is enabled')
    define('jenkins_password', default=None,
           help='Jenkins API key or password (if auth is enabled)')

    tornado.options.parse_command_line()

    server = HTTPServer(JenkinsHookshotApp())
    port = options.listening_port

    server.bind(port)
    server.start(0)
    IOLoop.instance().start()

if __name__ == '__main__':
    sys.exit(main())
