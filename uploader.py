#!/usr/bin/python

import requests
import urlparse
import json
import argparse
import os
import time
import ConfigParser

debug = False

def push(method, url, data, headers):
    global debug

    retry = True
    while retry:
        if method == 'POST':
            response = requests.post(url, data=data, headers=headers)
        elif method == 'PUT':
            response = requests.put(url, data=data, headers=headers)
        else:
            print "ERROR: unsupported method"
            exit(1)
        if response.status_code != 500:
            retry = False
            if debug:
                print "OK"
        else:
            time.sleep(10)
            print response.content


def load_json(json_file):
    with open(json_file, 'r') as f:
        return json.load(f)


def main(args):
    global debug

    # Initialize Variables
    job = None
    kernel = None
    defconfig = None
    arch = None
    if args.debug:
        debug = True
    # Parse the configuration for API credentials
    config = ConfigParser.ConfigParser()
    try:
            config.read(os.path.expanduser('~/.uploaderpy.cfg'))
            url = config.get(args.section, 'url')
            token = config.get(args.section, 'token')
            lab = config.get(args.section, 'lab')
    except:
        print "ERROR: unable to load configuration file"
        exit(1)

    # Parse Boot JSON
    if os.path.exists(os.path.expanduser(args.boot)):
        boot_json = load_json(args.boot)
        if 'job' in boot_json:
            job = boot_json['job']
        if 'kernel' in boot_json:
            kernel = boot_json['kernel']
        if 'defconfig' in boot_json:
            defconfig = boot_json['defconfig']
        if 'defconfig_full' in boot_json:
            defconfig = boot_json['defconfig_full']
        if 'arch' in boot_json:
            arch = boot_json['arch']

        if all([job, kernel, defconfig, arch]):
                headers = {
                    'Authorization': token,
                    'Content-Type': 'application/json'
                }
                api_url = urlparse.urljoin(url, '/boot')
                if debug:
                    print 'Sending boot result', args.boot, "to", api_url
                push('POST', api_url, json.dumps(boot_json), headers)
                headers = {
                    'Authorization': token
                }
                if args.txt and os.path.exists(os.path.expanduser(args.txt)):
                    with open(args.txt) as lh:
                        data = lh.read()
                    api_url = urlparse.urljoin(url, '/upload/%s/%s/%s/%s/%s' % (job,
                                                                                kernel,
                                                                                arch + '-' + defconfig,
                                                                                lab,
                                                                                os.path.basename(args.txt)))
                    if debug:
                        print 'Uploading text log to', api_url
                    push('PUT', api_url, data, headers)

                headers = {
                    'Authorization': token
                }
                if args.html and os.path.exists(os.path.expanduser(args.html)):
                    with open(args.html) as lh:
                        data = lh.read()
                    api_url = urlparse.urljoin(url, '/upload/%s/%s/%s/%s/%s' % (job,
                                                                                kernel,
                                                                                arch + '-' + defconfig,
                                                                                lab,
                                                                                os.path.basename(args.html)))
                    if debug:
                        print 'Uploading html log to', api_url
                    push('PUT', api_url, data, headers)

        else:
            print "ERROR: not enough data in boot JSON"
            exit(1)
    else:
        print "ERROR: boot json does not exist"
        exit(1)
    exit(0)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--boot", required=True, help="path your boot JSON")
    parser.add_argument("--html", help="path a html log file")
    parser.add_argument("--txt", help="path a txt log file")
    parser.add_argument("--section", required=True, help="loads this configuration for authentication")
    parser.add_argument("--debug", action='store_true')
    args = parser.parse_args()
    main(args)
