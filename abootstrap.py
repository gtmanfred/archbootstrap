#!/usr/bin/env python

from __future__ import print_function, generators, with_statement
import os
import re
import tarfile
from subprocess import call
from package import Package

try:
    from urllib.request import urlretrieve
except ImportError:
    from urllib import urlretrieve

def check_groups(archive, filename):
    descfile = archive.extractfile(filename);
    retgroups = []
    GROUPS = 1
    for line in descfile:
        thisline = line.decode('utf8').strip('\n')
        if '%GROUPS%' == thisline:
            GROUPS = 0
            break
        else:
            GROUPS = 1
    if GROUPS:
        return []
    else:
        return get_entries(descfile)

def package_depends(thisfile):
    DEPENDS=1
    for line in thisfile:
        thisline = line.decode('utf8').strip('\n')
        if '%DEPENDS%' == thisline:
            DEPENDS = 0
            break
        else:
            DEPENDS = 1
    if DEPENDS:
        return []
    else:
        return get_entries(thisfile)

def find_depends(archive, packages):
    retdepend = set()
    for package in packages:
        thisfile = archive.extractfile('/'.join([package,'depends']))
        depends = package_depends(thisfile)
        retdepend.update([re.findall(r'^[^<>=]*', x)[0] for x in depends])
    return retdepend

def get_entries(thisfile):
    ret = set()
    for line in thisfile:
        thisline = line.decode('utf8').strip('\n')
        if thisline:
            ret.add(thisline)
        else:
            return ret

def depend_version(archive, depends):
    filelist = [ x.strip('/') for x in archive.getnames() if '/' not in x]
    dependvers = set( y for x in depends for y in filelist if x in y )
    return dependvers

def get_groups(archive):
    tmpgroups = []
    packagedict = dict();
    for line in archive.getnames():
        if 'desc' in line[-4::]:
            packagedict[line.split('/')[0]] = check_groups(archive, line)
    return packagedict

def get_packages(package, devel=0):
    packages = set()
    for key,value in package.items():
        if 'base' in value or (devel and 'base-devel' in value):
            packages.add(key)
    return packages

def base_system(mirror, rootpath='/mnt/', devel=0):
    installed_packages = []
    coredb = '/'.join([mirror, 'core', 'os', os.uname()[-1], 'core.db'])
    arch = os.uname()[-1]
    urlretrieve(coredb, '/tmp/coredb')
    archive = tarfile.open('/tmp/coredb')
    packagedict = get_groups(archive)
    packages = get_packages(packagedict)
    depends = find_depends(archive, packages)
    depend_version(archive,depends)
    depends = depend_version(archive, depends) - packages
    cache_location = '/'.join([rootpath, 'var/cache/pacman/pkg/'])
    os.makedirs(cache_location, exist_ok=1)

    for package in packages:
        filename = '{}-{}.pkg.tar.xz'.format(package, arch)
        downloadfile = '/'.join([cache_location, filename])
        url = '/'.join([mirror, 'core', 'os', arch, filename])
        print(url)
        try:
            urlretrieve(url, downloadfile)
        except:
            print("EXCEPT")
            filename = '{}-{}.pkg.tar.xz'.format(package, 'any')
            url = '/'.join([mirror, 'core', 'os', arch, filename])
            downloadfile = '/'.join([cache_location, filename])
            urlretrieve(url, downloadfile)
        thispkg = Package(downloadfile, rootpath)
        thispkg.installpackage()
        installed_packages.append(thispkg)

    for package in depends:
        filename = '{}-{}.pkg.tar.xz'.format(package, arch)
        downloadfile = '/'.join([cache_location, filename])
        url = '/'.join([mirror, 'core', 'os', arch, filename])
        print(url)
        try:
            urlretrieve(url, downloadfile)
        except:
            print("EXCEPT")
            filename = '{}-{}.pkg.tar.xz'.format(package, 'any')
            url = '/'.join([mirror, 'core', 'os', arch, filename])
            downloadfile = '/'.join([cache_location, filename])
            urlretrieve(url, downloadfile)
        thispkg = Package(downloadfile, rootpath)
        thispkg.pkginfo['reason'] = 1
        thispkg.installpackage()
        installed_packages.append(thispkg)

    call(['mount', '-R', '/dev/', '/'.join([rootpath, 'dev/'])])
    call(['mount', '-R', '/sys/', '/'.join([rootpath, 'sys/'])])
    call(['mount', '-R', '/proc/', '/'.join([rootpath, 'proc/'])])
    for package in installed_packages:
        package.post_install_fun()

    archive.close()


if __name__ == '__main__':
    base_system('http://dfw.mirror.rackspace.com/archlinux/')
# vime: set ts=4 ws=4 et
