#!/usr/bin/env python

# Forked from https://github.com/Meshcloud/concourse-resource-bitbucket
# and used as starting template for bitbucket api usage

import sys
import json
import requests
import time
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


def get_prs(project, repo, access_token, debug, pr_no='', next_page=False, pages=3, **kwargs):
    """ Get open pull requests for project/repo
    """

    get_url = (
        "https://api.bitbucket.org/2.0/repositories/"
        "{project}/{repo}/pullrequests/{pr_no}".format(
        project=project, repo=repo, pr_no=pr_no)
    )
    for i, (k,v) in enumerate(kwargs.items()):
        fill = '&' if i else '?'
        get_url = "{url}{fill}{k}={v}".format(url=get_url, fill=fill, k=k, v=v)

    r = requests.get(
        get_url,
        auth=BitbucketOAuth(access_token)
    )
    request_count = 1

    if debug:
        err('Response: {}\nRequests:{}'.format(r, request_count))

    check_status_code(r)

    # Return only the json object is pr_no was specified
    # since `r.json()['values']` will not exist
    if pr_no:
        return r.json(), request_count
    # Return the list of results associated with `values`
    # and iterate over the full set of pages if `next`
    # has been specified as True
    else:
        result = r.json()['values']
        if next_page:
            # While there is a next page and we have not gone
            # over the page limit, continue requesting pages
            while r.json().get('next') and (request_count - 1) < pages:
                next_url = r.json().get('next')
                r = requests.get(
                    next_url,
                    auth=BitbucketOAuth(access_token)
                )
                result += r.json()['values']
                request_count += 1
                if debug:
                    err('Response: {}\nRequests:{}'.format(r, request_count))
                check_status_code(r)
                time.sleep(2)

    return result, request_count


def get_diff(project, repo, access_token, pr_no):
    """ Returns diff of specified pull request
    """

    get_url = (
        "https://api.bitbucket.org/2.0/repositories/"
        "{project}/{repo}/pullrequests/{pr_no}/diff".format(
        project=project, repo=repo, pr_no=pr_no)
    )
    err('Getting diff for {}'.format(pr_no))

    r = requests.get(
        get_url,
        auth=BitbucketOAuth(access_token)
    )

    if r.status_code == 555:
        # Implement an loop to retry
        for i in xrange(1, 3):
            err('Request hit {}, retrying {}th time'.format(r.status_code, i))
            time.sleep(5)
            r = requests.get(
                get_url,
                auth=BitbucketOAuth(access_token)
            )

    check_status_code(r)

    # If the PR contains no diff, then the string
    # referenced in content will be empty
    return r.content

def check_status_code(request):
    """ Check status code. Bitbucket brakes rest a bit by returning 200 or 201
    depending on it's the first time the status is posted.
    """

    if request.status_code not in [200, 201, 555]:
        try:
            msg = ERROR_MAP[request.status_code]
        except KeyError:
            msg = json_pp(request.json())

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
