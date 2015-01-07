from jenkins_hookshot.handlers import BaseHandler


class PingHandler(BaseHandler):
    """Endpoint: /ping

    Simple health check to see if the service is alive. Returns "pong".
    """

    def get(self):
        self.finish('pong')
