#!/usr/bin/env python2

import os
import sys
import tarfile
import time
import datetime as dt
import hashlib
import shutil

class package:
    '''
    parse information from a pacman package
   
    member variables:
    file (string) - name of package file
    file_list (array) - list of files in the package archive
    pkginfo (dict) - package information parsed from .PKGINFO
    pkg (TarFile) -  the tarball
    '''


    def __init__ (self, file, rootpath):
        self.file = file

        if not os.path.exists(file):
            raise IOError('{} does not exist'.format(file))

        if not tarfile.is_tarfile(file):
            raise TypeError('{} is not a tar file'.format(file))

        self.pkg = tarfile.open(file)

        self.file_list = self.pkg.getnames()
        self.file_list.sort()
        if not ".PKGINFO" in self.file_list:
            raise TypeError('{} is not a package file'.format(file))

        self.__parse_pkginfo()
        self.rootpath = rootpath
        self.localname="-".join([self.pkginfo['pkgname'], self.pkginfo['pkgver']])
        self.localpath = "".join([rootpath, '/var/lib/pacman/local/', self.localname]) 

    def __parse_pkginfo(self):
        self.pkginfo = {}
        self.pkginfo['pkgname'] = ""
        self.pkginfo['pkgbase'] = ""
        self.pkginfo['pkgver'] = ""
        self.pkginfo['pkgdesc'] = ""
        self.pkginfo['url'] = ""
        self.pkginfo['builddate'] = ""
        self.pkginfo['installdate'] = ""
        self.pkginfo['packager'] = ""
        self.pkginfo['size'] = ""
        self.pkginfo['arch'] = ""
        self.pkginfo['force'] = ""
        self.pkginfo['validation'] = ""
        self.pkginfo['reason'] = ""
        self.pkginfo['license'] = []
        self.pkginfo['replaces'] = []
        self.pkginfo['group'] = []
        self.pkginfo['depend'] = []
        self.pkginfo['optdepend'] = []
        self.pkginfo['conflict'] = []
        self.pkginfo['provides'] = []
        self.pkginfo['backup'] = []
        self.pkginfo['makepkgopt'] = []   

        arrays = ['license', 'replaces', 'group', 'depend', 'optdepend',
                  'conflict', 'provides', 'backup', 'makepkgopt']
       
        pkginfo = self.pkg.extractfile(".PKGINFO")
        for line in pkginfo:
            if (line[0] == '#'.encode('utf-8')[0]):
                continue
            (key, value) = line.decode('utf-8').split(" = ")

            if key in arrays:
                self.pkginfo[key].append(value.strip())
            else:
                self.pkginfo[key] = value.strip()

        pkginfo.close()


    def descfile(self):
        with open(''.join([self.localpath,'/desc']), "w") as descfile:
            print('%NAME%\n{}'.format(self.pkginfo['pkgname']), file=descfile)
            print('\n%VERSION%\n{}'.format(self.pkginfo['pkgver']), file=descfile)
            print('\n%DESC%\n{}'.format(self.pkginfo['pkgdesc']), file=descfile)
            print('\n%URL%\n{}'.format(self.pkginfo['url']), file=descfile)
            print('\n%ARCH%\n{}'.format(self.pkginfo['arch']), file=descfile)
            print('\n%BUILDDATE%\n{}'.format(self.pkginfo['builddate']), file=descfile)
            print('\n%INSTALLDATE%\n{}'.format(int(time.mktime(dt.datetime.now().timetuple()))), file=descfile)
            print('\n%PACKAGER%\n{}'.format(self.pkginfo['packager']), file=descfile)
            print('\n%SIZE%\n{}'.format(self.pkginfo['size']), file=descfile)
            if self.pkginfo['reason']:
                print('\n%REASON%\n1', file=descfile)
            if self.pkginfo['group']:
                print('\n%GROUPS%', file=descfile)
                for group in self.pkginfo['group']:
                    print("{}".format(group), file=descfile)
            print('\n%LICENSE%', file=descfile)
            for license in self.pkginfo['license']:
                print("{}".format(license), file=descfile)
            print("\n%VALIDATION%\n{}".format('gpg'), file=descfile)
            if self.pkginfo['replaces']:
                print('\n%REPLACES%', file=descfile)
                for replace in self.pkginfo['replaces']:
                    print("{}".format(replace), file=descfile)
            if self.pkginfo['depend']:
                print('\n%DEPENDS%', file=descfile)
                for depend in self.pkginfo['depend']:
                    print("{}".format(depend), file=descfile)
            if self.pkginfo['optdepend']:
                print('\n%OPTDEPENDS%', file=descfile)
                for depend in self.pkginfo['optdepend']:
                    print("{}".format(depend), file=descfile)
            if self.pkginfo['conflict']:
                print('\n%CONFLICTS%', file=descfile)
                for conflict in self.pkginfo['conflict']:
                    print("{}".format(conflict), file=descfile)
            if self.pkginfo['provides']:
                print('\n%PROVIDES%', file=descfile)
                for provide in self.pkginfo['provides']:
                    print("{}".format(provide), file=descfile)
            print(file=descfile)
            os.remove("/".join([self.rootpath, '.PKGINFO']))

    def installfile(self):
        if ".INSTALL" in self.file_list:
            instfile = open("/".join([self.rootpath, '.INSTALL']))
            installfile = open("/".join([self.localpath, 'install']), 'w')
            for line in instfile:
                print(line, file=installfile, end='')
            instfile.close()
            installfile.close()
            os.remove("/".join([self.rootpath, '.INSTALL']))

    def get_md5sum(self, backup_file):
        tmpfile = open("/".join([self.rootpath, backup_file]), 'rb')
        ret = hashlib.md5(tmpfile.read()).hexdigest()
        tmpfile.close()
        return ret


    def filesfile(self):
        filesfile = open("/".join([self.localpath, 'files']), 'w')
        print("%FILES%", file=filesfile)
        for line in self.file_list:
            print(line, file=filesfile)
        print(file=filesfile)
        if self.pkginfo['backup']:
            print("%BACKUP%", file=filesfile)
            for line in self.pkginfo['backup']:
                print(line, self.get_md5sum(line), file=filesfile, sep='\t')
        print(file=filesfile)
        filesfile.close()

    def mtreefile(self):
        src = "/".join([self.rootpath, ".MTREE"])
        dest = "/".join([self.localpath, "mtree"])
        shutil.move(src, dest)

    def extractfiles(self):
        self.pkg.extractall(path=self.rootpath)
        self.pkg.close()
        

    def installpackage(self):
        os.makedirs(self.localpath, exist_ok=1)
        self.extractfiles()
        self.descfile()
        self.installfile()
        self.filesfile()
        self.mtreefile()

if __name__ == '__main__':
    if os.path.isdir(sys.argv[2]):
        archive = package(sys.argv[1], sys.argv[2])
        archive.installpackage()

# vim : set ts=4 sw=4 softtabstop=4 et:
