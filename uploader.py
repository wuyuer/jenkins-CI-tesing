#!/usr/bin/python

import requests
import urlparse
import json
import argparse
import os
import time
import ConfigParser


def push(method, url, data, headers):
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
            print "OK"
        else:
            time.sleep(10)
            print response.content


def load_json(json_file):
    with open(json_file, 'r') as f:
        return json.load(f)


def main(args):
    # Initialize Variables
    job = None
    kernel = None
    defconfig = None
    arch = None

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
        if 'arch' in boot_json:
            arch = boot_json['arch']

        if all([job, kernel, defconfig, arch]):
                print 'Sending boot result....'
                headers = {
                    'Authorization': token,
                    'Content-Type': 'application/json'
                }
                api_url = urlparse.urljoin(url, '/boot')
                push('POST', api_url, json.dumps(boot_json), headers)
                print 'Uploading text version of boot log...'
                headers = {
                    'Authorization': token
                }
                if os.path.exists(os.path.expanduser(args.txt)):
                    with open(args.txt) as lh:
                        data = lh.read()
                    api_url = urlparse.urljoin(url, '/upload/%s/%s/%s/%s/%s' % (job,
                                                                                kernel,
                                                                                arch + '-' + defconfig,
                                                                                lab,
                                                                                os.path.basename(args.txt)))
                    push('PUT', api_url, data, headers)
                print 'Uploading html version of boot log'
                headers = {
                    'Authorization': token
                }
                if os.path.exists(os.path.expanduser(args.html)):
                    with open(args.html) as lh:
                        data = lh.read()
                    api_url = urlparse.urljoin(url, '/upload/%s/%s/%s/%s/%s' % (job,
                                                                                kernel,
                                                                                arch + '-' + defconfig,
                                                                                lab,
                                                                                os.path.basename(args.html)))
                    push('PUT', api_url, data, headers)
                else:
                    print "ERROR: txt log does not exist"
                    exit(1)
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
    parser.add_argument("--html", required=True, help="path a html log file")
    parser.add_argument("--txt", required=True, help="path a txt log file")
    parser.add_argument("--section", required=True, help="loads this configuration for authentication")
    args = parser.parse_args()
    main(args)