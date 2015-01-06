from jenkins_hookshot.handlers import BaseHandler
from jenkins_hookshot import __proj_name__, __proj_version__, __proj_url__


class RootHandler(BaseHandler):
    """Endpoint: /

    This is the default root handler. If someone (or something) GETs this
    handler, print out some basic info about the app.
    """

    def get(self):
        self.write_final('{} v{} ({})'.format(
            __proj_name__, __proj_version__, __proj_url__
        ))
