import tornado.web

from jenkins_hookshot.handlers import RootHandler
from jenkins_hookshot.handlers import PingHandler
from jenkins_hookshot.handlers import CreateHandler


class JenkinsHookshotApp(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/', RootHandler),
            (r'/ping', PingHandler),
            (r'/v1/create', CreateHandler)
        ]

        tornado.web.Application.__init__(self, handlers)