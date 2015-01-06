from tornado.web import RequestHandler


class BaseHandler(RequestHandler):
    def initialize(self):
        self.set_header('Content-Type', 'text/plain')

    def write_final(self, message):
        """Writes a message to the client and closes the connection.

        :param message: message (string) to write to the client
        """
        self.write(message)
        self.finish()