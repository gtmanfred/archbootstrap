#!/usr/bin/env python2

from __future__ import print_function
import os, os.path
import sys, time, shutil, hashlib, tarfile, subprocess
import datetime as dt
from collections import defaultdict, deque

name_extract = lambda name, dashes: '-'.join(name.split('-')[:-dashes])
remove_rel = lambda name: name_extract(name, 1)
remove_v_r = lambda name: name_extract(name, 2) 

def ver_clean(n):
    n = n.strip()
    for c in '><:=':
        n = n.partition(c)[0]
    return n

class Repo(object):
    """
    """
    def __init__(self, tar_path):
        self.tree = self.load_repo_tgz(tar_path)
    
    def __getitem__(self, key):
        "smart enough to do partial matches"
        # not that smart, runs in O(n*m)
        if key in self.tree:
            return self.tree[key]
        # check for missing -rel
        for k in self.tree:
            if key == remove_rel(k):
                return self.tree[k]
        # check for missing -ver-rel
        for k in self.tree:
            if key == remove_v_r(k):
                return self.tree[k]
        # check for provides
        for k in self.tree:
            if 'PROVIDES' not in self.tree[k]:
                continue
            if key in [ver_clean(p) for p in self.tree[k]['PROVIDES']]:
                return self.tree[k]

    def __setitem__(self, key, value):
        self.tree[key] = value

    def load_repo_tgz(self, tar_path):
        db = tarfile.open(tar_path)
        tree = {}
        for member in db.getmembers():
            if not member.isfile():
                continue
            path = member.name
            name,sub = os.path.split(path)
            desc = DescParse(db.extractfile(member))
            if name in tree:
                # stack desc and depends
                # (blame Dan why they are not in one file)
                tree[name].info.update(desc.info)
            else:
                tree[name] = desc
        return tree

    def group_members(self, group):
        matches = set()
        for pkg in self.tree:
            if 'GROUPS' not in self.tree[pkg]:
                continue
            if group in self.tree[pkg]['GROUPS']:
                matches.add(pkg)
        return matches

    def depends(self, pkgs):
        "recursive, returns set"
        deps = set(pkgs)
        todo = deque(pkgs)
        while todo:
            pkg = todo.popleft()
            if 'DEPENDS' not in self[pkg]:
                continue
            these_deps = [ver_clean(p) for p in self[pkg]['DEPENDS']]
            these_deps = set(self[p]['NAME'] for p in these_deps)
            todo.extend(these_deps - deps)
            deps.update(these_deps)
        return deps - set(pkgs)

class DescParse(object):
    """
    """

    def __init__(self, desc_file):
        self.info = self.desc_load(desc_file)
        self.info = self.desc_clean(self.info)

    def __repr__(self):
        return repr(self.info)

    def __getitem__(self, key):
        return self.info[key]

    def __setitem__(self, key, value):
        self.info[key] = value

    def __contains__(self, key):
        return key in self.info

    # bunch of stateless/static methods
    # for easier testing and modularity
    def desc_load(self, desc_file):
        "takes a file-like object, returns a messy desc"
        info = defaultdict(list)
        mode = None
        for line in desc_file:
            if type(line) == bytes:
                line = line.decode("utf-8")
            line = line.strip()
            #line = self.clean(line)
            if not line:
                continue
            if line.startswith('%'):
                mode = line.strip('%')
                continue
            info[mode].append(line)
        desc_file.close()
        return info

    def desc_clean(self, info):
        "returns a new dictionary"
        singles = 'NAME VERSION DESC URL ARCH'.split()
        integers = 'SIZE CSIZE ISIZE INSTALLDATE BUILDDATE'.split()
        info2 = {}
        for k in singles + integers:
            if k not in info:
                continue
            info2[k] = info[k][0]
            if k in integers:
                info2[k] = int(info2[k])
        for k,v in info.items():
            if k in info2:
                continue
            info2[k] = v
        return info2

    def serialize(self, keys):
        "returns string"
        s = []
        for k in keys:
            if k not in self.info:
                continue
            v = self.info[k]
            s.append('%{}%'.format(k))
            if type(v) == list:
                s.extend(v)
            else:
                s.append(str(v))
            s.append('')
        return '\n'.join(s)


class Package:
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
        self.localpath = '/'.join([rootpath, '/var/lib/pacman/local/', self.localname]) 
        self.installfile = '/'.join([self.localpath, 'install'])
        self.descfile = '/'.join([self.localpath, 'desc'])
        self.filesfile = '/'.join([self.localpath, 'files'])
        self.mtreefile = "/".join([self.localpath, "mtree"])

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


    def descfile_fun(self):
        with open(self.descfile, "w") as descfile:
            descfile.write('%NAME%\n{}\n'.format(self.pkginfo['pkgname']))
            descfile.write('\n%VERSION%\n{}\n'.format(self.pkginfo['pkgver']))
            descfile.write('\n%DESC%\n{}\n'.format(self.pkginfo['pkgdesc']))
            descfile.write('\n%URL%\n{}\n'.format(self.pkginfo['url']))
            descfile.write('\n%ARCH%\n{}\n'.format(self.pkginfo['arch']))
            descfile.write('\n%BUILDDATE%\n{}\n'.format(self.pkginfo['builddate']))
            descfile.write('\n%INSTALLDATE%\n{}\n'.format(int(time.mktime(dt.datetime.now().timetuple()))))
            descfile.write('\n%PACKAGER%\n{}\n'.format(self.pkginfo['packager']))
            descfile.write('\n%SIZE%\n{}\n'.format(self.pkginfo['size']))
            if self.pkginfo['reason']:
                descfile.write('\n%REASON%\n1\n')
            if self.pkginfo['group']:
                descfile.write('\n%GROUPS%\n')
                for group in self.pkginfo['group']:
                    descfile.write("{}\n".format(group))
            descfile.write('\n%LICENSE%\n')
            for license in self.pkginfo['license']:
                descfile.write("{}\n".format(license))
            descfile.write("\n%VALIDATION%\n{}\n".format('gpg'))
            if self.pkginfo['replaces']:
                descfile.write('\n%REPLACES%\n')
                for replace in self.pkginfo['replaces']:
                    descfile.write("{}\n".format(replace))
            if self.pkginfo['depend']:
                descfile.write('\n%DEPENDS%\n')
                for depend in self.pkginfo['depend']:
                    descfile.write("{}\n".format(depend))
            if self.pkginfo['optdepend']:
                descfile.write('\n%OPTDEPENDS%\n')
                for depend in self.pkginfo['optdepend']:
                    descfile.write("{}\n".format(depend))
            if self.pkginfo['conflict']:
                descfile.write('\n%CONFLICTS%\n')
                for conflict in self.pkginfo['conflict']:
                    descfile.write("{}\n".format(conflict))
            if self.pkginfo['provides']:
                descfile.write('\n%PROVIDES%\n')
                for provide in self.pkginfo['provides']:
                    descfile.write("{}\n".format(provide))
            descfile.write('\n')
            os.remove("/".join([self.rootpath, '.PKGINFO']))

    def installfile_fun(self):
        if ".INSTALL" in self.file_list:
            src = "/".join([self.rootpath, ".INSTALL"])
            shutil.move(src, self.installfile)

    def get_md5sum(self, backup_file):
        tmpfile = open("/".join([self.rootpath, backup_file]), 'rb')
        ret = hashlib.md5(tmpfile.read()).hexdigest()
        tmpfile.close()
        return ret


    def filesfile_fun(self):
        ff = open(self.filesfile, 'w')
        ff.write("%FILES%\n")
        for line in self.file_list:
            ff.write('{}\n'.format(line))
        ff.write('\n')
        if self.pkginfo['backup']:
            ff.write("%BACKUP%\n")
            for line in self.pkginfo['backup']:
                ff.write('{}\t{}\n'.format(line, self.get_md5sum(line)))
        ff.write('\n')
        ff.close()

    def mtreefile_fun(self):
        if '.MTREE' in self.file_list:
            src = "/".join([self.rootpath, ".MTREE"])
            shutil.move(src, self.mtreefile)

    def extractfiles(self):
        self.pkg.extractall(path=self.rootpath)
        self.pkg.close()
        
    def post_install_fun(self):
        if os.path.isfile(self.installfile):
            with open(self.installfile, 'r') as  installfile:
                if 'post_install' in installfile.read():
                    os.chroot(self.rootpath)
                    os.putenv('BASH_ENV', self.installfile)
                    subprocess.call(["bash", '-c', 'post_install'])
        

    def installpackage(self):
        os.makedirs(self.localpath, exist_ok=1)
        self.extractfiles()
        self.descfile_fun()
        self.installfile_fun()
        self.filesfile_fun()
        self.mtreefile_fun()

if __name__ == '__main__':
    if os.path.isdir(sys.argv[2]):
        archive = Package(sys.argv[1], sys.argv[2])
        archive.installpackage()

# vim : set ts=4 sw=4 softtabstop=4 et:
