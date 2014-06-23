#!/usr/bin/env python
#
# error/warn formatting, css, colors etc. stolen from Olof Johansson <olof@lixom.net>
#
import os
import sys
import subprocess

headers = """
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN">
<html>
<head>
  <title>Board: %s</title>
  <style type="text/css">
  body { background-color: black; color: white; }
  pre warn { color: #F88017; }
  pre err { color: red; }
  pre pass { color: green; }
  pre offline { color: darkgray; }
  A:link {text-decoration: none }
  A:visited {text-decoration: none }
  A:active {text-decoration: none }
  A:hover {text-decoration: bold; color: red; }
  </style>
</head>
<body>

"""

log = sys.argv[1]
if not os.path.exists(log):
    print "ERROR: logfile %s doesn't exist." %log
    sys.exit(1)

base,ext = os.path.splitext(log)
html = base + ".html"
base = os.path.basename(log)

log_f = open(log, "r")
html_f = open(html, "w")

html_f.write(headers %base)
html_f.write("<h1>%s</h1>\n" %base)

errors = subprocess.check_output('grep "^\[ERR\]" %s | cat' %log, shell=True).splitlines()
num_errors = len(errors)
warnings = subprocess.check_output('grep "^\[WARN\]" %s | cat' %log, shell=True).splitlines()
num_warnings = len(warnings)

html_f.write("<font size=-2><pre>\n")

html_f.write("<h2>Errors: %d</h2>\n" %num_errors)
if num_errors:
    for e in errors:
        html_f.write("<err>%s</err>\n" %e.rstrip())
    html_f.write("\n")

html_f.write("<h2>Warnings: %d</h2>\n" %num_warnings)
if num_warnings:
    for e in warnings:
        html_f.write("<warn>%s</warn>\n" %e.rstrip())
    html_f.write("\n")

html_f.write("<h2>Full boot log:</h2>\n")
for line in log_f:
    warn = err = False
    if line.startswith("[WARN]"):
        warn = True
        html_f.write("<warn>")
    elif line.startswith("[ERR]"):
        err = True
        html_f.write("<err>")
    html_f.write(line)
    if warn:
        html_f.write("</warn>")
    elif err:
        html_f.write("</err>")

html_f.write("</pre></font></body></html>")

log_f.close()
html_f.close()
