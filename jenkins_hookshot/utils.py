import hmac
import json
import os
from datetime import datetime
from dateutil.tz import tzlocal
from hashlib import sha1
from random import randrange

import redis
import requests
from marathon import MarathonClient
from tornado.options import options


def get_random_marathon_task(app_id):
    """Connect to Marathon and return a random task for a given application ID.

    :param app_id: The Marathon application ID.
    :return: tuple of the instance IP or hostname and listening port.
    """
    c = MarathonClient('http://{}'.format(options.marathon_host))
    app = c.get_app(app_id)
    task_host, task_port = None, None
    rand = randrange(0, len(app.tasks))
    task_host = app.tasks[rand].host
    task_port = app.tasks[rand].ports[0]

    return task_host, task_port


def jenkins_build_with_params(host, port, job, params):
    """Trigger a parameterized build of 'job'.

    :param host: hostname or IP address of a Jenkins instance
    :param port: listening port of a Jenkins instance
    :param job: the job name to trigger a build of
    :param params: Python dictionary of parameters to pass to the job
    :return: boolean; true if successful, false otherwise
    """
    p = []
    for k, v in params.items():
        p.append("{}={}".format(k, v))

    r = requests.get('http://{host}:{port}/job/{job}/buildWithParameters?{params}'.format(
        host=host, port=port, job=job, params='&'.join(p)))

    if r.status_code == requests.codes.ok:
        return True
    else:
        return False


def jenkins_create_job(host, port, name):
    """Create a new job on a Jenkins instance by POSTing the pre-baked
    config.xml template in this project.

    :param host: hostname or IP address of a Jenkins instance
    :param port: listening port of a Jenkins instance
    :param name: the name of the job; URI-safe chars only
    :return: boolean; true if successful, false otherwise
    """
    url = 'http://{host}:{port}/createItem?name={name}'.format(
        host=host, port=port, name=name)
    headers = {'Content-Type': 'application/xml'}
    config_xml_path = os.path.join(
        os.path.dirname(__file__), 'resources', 'config.xml')

    with open(config_xml_path, 'rb') as f:
        config_xml = f.read()

    r = requests.post(url, data=config_xml, headers=headers)

    # The API docs for Jenkins 1.580.2 state that HTTP 200 will
    # be returned on success, or 4xx or 5xx on failure.
    if r.status_code == requests.codes.ok:
        return True
    else:
        return False


def jenkins_healthcheck(host, port):
    """Simple service check for Jenkins.

    :param host: hostname or IP address of a Jenkins instance
    :param port: listening port of a Jenkins instance
    :return: boolean; returns true if Jenkins is alive and well
    """
    result = False
    r = requests.get('http://{host}:{port}/'.format(host=host, port=port))

    if 'X-Jenkins' in r.headers:    # The header exists
        if r.headers['X-Jenkins']:  # The header contains data
            result = True

    return result


def ship_to_redis(namespace, repo, uniq_id, payload, jenkins_url,
                  jenkins_seed_job, jenkins_seed_job_url):
    """Ship the original GitHub payload to Redis based on the UUID for this
    build. Track the builds for a given repo (namespace/repo) based on the
    UUID and index of the Redis list.

    :param namespace: GitHub username or organization (e.g. 'puppetlabs')
    :param repo: GitHub repository name (e.g. 'puppet')
    :param uniq_id: UUID; randomly generated on POST event to '/v1/create'
    :param payload: the original webhook payload as a Python object
    :param jenkins_url: the URL to the Jenkins instance the jobs are created on
    :param jenkins_seed_job: the name of the Jenkins Job DSL seed job
    :param jenkins_seed_job_url: the URL to the Jenkins Job DSL seed job
    :return: boolean; True if successful, False otherwise
    """
    r = redis.StrictRedis(host=options.redis_host)

    # Most recent builds (UUIDs) come first in the 'recent' list
    r.lpush('recent', uniq_id)

    # Track UUIDs for individual repos (namespace__repo)
    r.rpush('{}/{}'.format(namespace, repo), uniq_id)

    # Store the original payload as JSON, to be consumed by Logstash
    r.rpush('logstash', json.dumps({
        'id': uniq_id,
        'source': 'jenkins-hookshot',
        'namespace': namespace,
        'repo': repo,
        '@timestamp': datetime.now(tzlocal()).replace(microsecond=0).isoformat(),
        'payload': payload,
        'jenkins_url': jenkins_url,
        'jenkins_seed_job': jenkins_seed_job,
        'jenkins_seed_job_url': jenkins_seed_job_url
    }))

    # TODO: there should be actual error handling here
    return True


def validate_payload_hash(request, secret):
    """Validate the SHA1 hash of a GitHub webhook payload.

    If a webhook secret was set, we expect the 'X-Hub-Signature' header to be
    present. It is a HMAC hex digext of the request body, using the secret as
    the key.

    :param request: the request body (POSTed payload)
    :param secret: the shared webhook secret
    :return: boolean; true if hash sums match, false otherwise
    """
    if 'X-Hub-Signature' in request.headers:
        signature = request.headers['X-Hub-Signature']
    else:
        return False

    try:
        hash_type, hex_digest = signature.split('=')
    except(ValueError, UnboundLocalError):
        return False

    if hash_type == 'sha1':
        # Hash type will (probably) always be SHA1 for API v3:
        # https://developer.github.com/v3/repos/hooks/
        mac = hmac.new(secret, msg=request.body, digestmod=sha1)

        if mac.hexdigest() == hex_digest:
            return True
        else:
            return False
