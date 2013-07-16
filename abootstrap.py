#!/usr/bin/env python

from __future__ import print_function, generators, with_statement
from time import sleep
import os, re, tarfile
from subprocess import call
from package import *

try:
    from urllib.request import urlretrieve
except ImportError:
    from urllib import urlretrieve

def base_system(mirror, rootpath='/mnt/', devel=0):
    arch = os.uname()[-1]
    if os.path.isfile(mirror):
        db = Repo(mirror)
    else:
        coredb = '/'.join([mirror, 'core', 'os', arch, 'core.db'])
        urlretrieve(coredb, '/tmp/coredb')
        db = Repo('/tmp/coredb')
    base_packages = db.group_members('base')
    base_packages = set(remove_v_r(p) for p in base_packages)
    base_depends = db.depends(base_packages)
    #print(len(base_packages), len(base_depends), len(base_packages | base_depends))
    #print(base_packages)
    #print(base_depends)
    print('\n'.join(base_packages | base_depends))
    return
    
    cache_location = '/'.join([rootpath, 'var/cache/pacman/pkg/'])
    # exist_ok is not in py2
    #os.makedirs(cache_location, exist_ok=1)

    for pkg in base_packages | base_depends:
        filename = '{}-{}-{}.pkg.tar.xz'.format(db[pkg]['NAME'], db[pkg]['VERSION'], db[pkg]['ARCH'])

        downloadfile = '/'.join([cache_location, filename])
        url = '/'.join([mirror, 'core', 'os', arch, filename])
        print(url)
        continue
        urlretrieve(url, downloadfile)
        thispkg = Package(downloadfile, rootpath)
        if pkg in base_depends:
            thispkg.pkginfo['reason'] = 1
        thispkg.installpackage()
        installed_packages.append(thispkg)

    return

    call(['mount', '-R', '/dev/', '/'.join([rootpath, 'dev/'])])
    call(['mount', '-R', '/sys/', '/'.join([rootpath, 'sys/'])])
    call(['mount', '-R', '/proc/', '/'.join([rootpath, 'proc/'])])
    for pkg in installed_packages:
        pkg.post_install_fun()


if __name__ == '__main__':
    #print( base_system('http://dfw.mirror.rackspace.com/archlinux/'))
    #d = DescParse(open('/var/lib/pacman/local/pacman-4.1.2-1/desc'))
    #print(d.info)
    #db = Repo('/var/lib/pacman/sync/core.db')
    #print(db.tree)
    #print(db['pacman-4.1.2-1'].serialize('NAME VERSION DESC URL ARCH BUILDDATE INSTALLDATE PACKAGER SIZE REASON GROUPS LICENSE VALIDATION REPLACES DEPENDS OPTDEPENDS CONFLICTS PROVIDES'.split()))
    #print(db['pacman-4.1.2'])
    #print(db['pacman'])
    #print(db['pacman-contrib'])
    #base_system('/var/lib/pacman/sync/core.db')
    #base_system('http://dfw.mirror.rackspace.com/archlinux/')
    base_system('/tmp/coredb')


# vime: set ts=4 ws=4 et
