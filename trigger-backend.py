#!/usr/bin/env python

try:
    import simplejson as json
except ImportError:
    import json

import requests
import urlparse
import os
import sys

AUTHORIZATION_TOKEN = '9e24740a-b978-47a9-a611-4dbf0a17ae3c'
BACKEND_URL = 'http://api.armcloud.us'
JSON_FILE = ''

def usage():
    print "Usage:", os.path.basename(sys.argv[0]), "<JSON file>"

def load_json(json_file):
    with open(json_file, 'r') as f:
        return json.load(f)


def main():
    headers = {
        'Authorization': AUTHORIZATION_TOKEN,
        'Content-Type': 'application/json'
    }

    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    JSON_FILE = sys.argv[1]

    if not os.path.exists(JSON_FILE):
        print "ERROR: JSON file", JSON_FILE, "doesn't exist."
        sys.exit(1)

    payload = load_json(JSON_FILE)

    url = urlparse.urljoin(BACKEND_URL, '/boot')
    response = requests.post(url, data=json.dumps(payload), headers=headers)

    print response.content

if __name__ == '__main__':
    main()
