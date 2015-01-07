from tornado.web import RequestHandler


class BaseHandler(RequestHandler):
    def initialize(self):
        self.set_header('Content-Type', 'text/plain')

    def write_error(self, status_code, **kwargs):
        self.set_status(status_code)
        self.finish("{}: {}".format(status_code, self._reason))
