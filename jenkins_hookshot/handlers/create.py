import json
import uuid

import tornado.web
from tornado.options import options

import jenkins_hookshot.utils as utils
from jenkins_hookshot.handlers import BaseHandler


class CreateHandler(BaseHandler):
    """Endpoint: /v1/create

    This handler would typically be public (i.e. exposed to the Internet) so
    that GitHub can hit it. Therefore, we should make sure that the payload
    and HTTP headers from the webhook are authentic and properly crafted.
    """

    def get_random_jenkins_master(self):
        """Get a random Jenkins master.

        :return: jenkins_host, jenkins_port
        """
        attempt = 1
        jenkins_host, jenkins_port = None, None
        while attempt <= 3:
            jenkins_host, jenkins_port = utils.get_random_marathon_task(
                options.marathon_app_id)
            if utils.jenkins_healthcheck(jenkins_host, jenkins_port):
                # JENKINS LIVES!
                break
            else:
                attempt += 1

            if attempt == 3:
                raise tornado.web.HTTPError(500, log_message="Error: No available Jenkins masters.")

        return jenkins_host, jenkins_port

    def post(self):
        uniq_id = str(uuid.uuid4())
        request = self.request
        content_type = request.headers['Content-Type']

        # Validation
        if 'X-GitHub-Event' in request.headers:
            event = request.headers['X-GitHub-Event']
        else:
            raise tornado.web.HTTPError(400,
                                        log_message='Error: X-GitHub-Event header not set')

        if content_type != 'application/json':
            raise tornado.web.HTTPError(400,
                                        log_message='Error: Invalid Content-Type {}'.format(
                                            content_type))

        if options.github_hook_secret:
            # In Python 3.3, the string passed to HMAC must be of type 'bytes'.
            # This was fixed in Python 3.4. For now, we need to encode it here
            # ourselves. http://bugs.python.org/issue18240 -- roger, 2014-11-16
            secret = options.github_hook_secret.encode('utf-8')

            if not utils.validate_payload_hash(request, secret):
                raise tornado.web.HTTPError(400,
                                            log_message='Error: Unable to validate payload hash.')

        try:
            payload = json.loads(request.body.decode('utf-8'))
        except:
            raise tornado.web.HTTPError(400, log_message='Error: Unable to load JSON.')

        # Get a random Jenkins instance and ensure it's actually alive
        jenkins_host, jenkins_port = self.get_random_jenkins_master()

        # Actions based on the event type
        if event == 'ping':
            self.finish('pong')
        elif event == 'pull_request':
            # TODO: implement 'pull_request' processor
            raise tornado.web.HTTPError(501,
                                        log_message="pull_request processing not yet implemented.")
        elif event == 'push':
            namespace = payload['repository']['full_name'].split('/')[0]
            repo = payload['repository']['full_name'].split('/')[1]

            if payload['repository']['description'] == '':
                repo_desc = "None"
            else:
                repo_desc = payload['repository']['description']

            # These parameters are pre-baked into 'resources/config.xml'.
            # Adding additional params here requires modifying the template.
            params = {
                'REPO_NAMESPACE': namespace,
                'REPO_NAME': repo,
                'REPO_DESCRIPTION': repo_desc,
                'REPO_URL': payload['repository']['url'],
                'GIT_SHA': payload['after'],
                'UNIQ_ID': uniq_id
            }

            jenkins_job_name = "{}__{}__{}".format(namespace, repo, uniq_id)
            if not utils.jenkins_create_job(jenkins_host, jenkins_port,
                                            jenkins_job_name):
                raise tornado.web.HTTPError(500,
                                            log_message="Error: failed to create Jenkins job {} on Jenkins host {}:{}".format(
                                                jenkins_job_name, jenkins_host,
                                                jenkins_port))
            else:
                self.write(
                    'Success: created Jenkins job {} on Jenkins host {}:{}'.format(
                        jenkins_job_name, jenkins_host, jenkins_port))

            utils.jenkins_build_with_params(jenkins_host, jenkins_port,
                                            jenkins_job_name, params)
            utils.ship_to_redis(namespace, repo, uniq_id, payload)

        else:
            raise tornado.web.HTTPError(501,
                                        log_message="Error: Event type {} is not currently implemented.".format(
                                            event))
