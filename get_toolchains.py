#!/usr/bin/env python

import os
import ftplib

gcc_ver='4.6.3'
ftp = ftplib.FTP('www.kernel.org')
ftp.login()
ftp.cwd('pub/tools/crosstool/files/bin/x86_64/%s' %gcc_ver)
files = ftp.nlst()
for f in files: 
    if f[-3:] == '.xz':
        if os.path.exists(f):
            print "Already exists:", f
            continue

        print "Retrieving", f
        ftp.retrbinary('RETR %s' %f, open(f, 'wb').write)

ftp.quit()
