#!/usr/bin/env python

# Forked from https://github.com/Meshcloud/concourse-resource-bitbucket
# and used as starting template for bitbucket api usage

import sys
import json
import requests
from requests.auth import HTTPBasicAuth, AuthBase

ERROR_MAP = {
    403: "HTTP 403 Forbidden - Does your bitbucket user have rights to the repo?",
    404: "HTTP 404 Not Found - Does the repo supplied exist?",
    400: "HTTP 401 Unauthorized - Are your bitbucket credentials correct?"}


class BitbucketException(Exception):
    pass


class BitbucketOAuth(AuthBase):
    """ Adds the correct auth token for OAuth access to bitbucket.com
    """

    def __init__(self, access_token):
        self.access_token = access_token

    def __call__(self, r):
        r.headers['Authorization'] = "Bearer {}".format(self.access_token)
        return r


def err(txt):
    """ Convenience method for writing to stderr. Coerces input to a string.
    """
    sys.stderr.write(str(txt) + "\n")


def json_pp(json_object):
    """ Convenience method for pretty-printing JSON
    """

    if isinstance(json_object, dict):
        return json.dumps(json_object,
                          sort_keys=True,
                          indent=4,
                          separators=(',', ':')) + "\n"
    elif isinstance(json_object, str):
        return json.dumps(json.loads(json_object),
                          sort_keys=True,
                          indent=4,
                          separators=(',', ':')) + "\n"
    else:
        raise NameError('Must be a dictionary or json-formatted string')


def get_open_prs(project, repo, access_token, debug, state='OPEN', pr_no='', **kwargs):
    """ Get open pull requests for project/repo
    """

    get_url = (
        "https://api.bitbucket.org/2.0/repositories/"
        "{project}/{repo}/pullrequests/{pr_no}?pagelen=30&state={state}".format(
        project=project, repo=repo, pr_no=pr_no, state=state)
    )
    for k,v in kwargs.items():
        get_url = "{url}?{k}={v}".format(url=get_url,k=k,v=v)

    r = requests.get(
        get_url,
        auth=BitbucketOAuth(access_token)
    )

    if debug:
        err("request result: " + str(r))

    check_status_code(r)

    return r


def check_status_code(request):
    """ Check status code. Bitbucket brakes rest a bit by returning 200 or 201
    depending on it's the first time the status is posted.
    """

    if request.status_code not in [200, 201]:
        try:
            msg = ERROR_MAP[request.status_code]
        except KeyError:
            msg = json_pp(r.json())

        raise BitbucketException(msg)


def request_access_token(client_id, secret, debug):
    """ Request access token from bitbucket instance
    using oauth credentials
    """

    r = requests.post(
        'https://bitbucket.org/site/oauth2/access_token',
        auth=HTTPBasicAuth(client_id, secret),
        data={'grant_type': 'client_credentials'}
    )

    if debug:
        err("Access token result: " + str(r) + str(r.content))

    if r.status_code != 200:
        try:
            msg = ERROR_MAP[r.status_code]
        except KeyError:
            msg = json_pp(r.json())

        raise BitbucketException(msg)

    return r.json()['access_token']   
