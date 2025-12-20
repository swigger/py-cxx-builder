#!/usr/bin/env python
# coding:utf8 vim:ts=4
"""
py-cxx-builder: Build C++ extensions for Python with cross-platform support.

This module provides utilities for building Python C extensions from C++ source
files, with support for both MSVC (Windows) and GCC (Linux/macOS).
"""

__version__ = "0.1.0"
__all__ = ["CXXBuilder", "ModiGCC", "ModiMSVC"]

import multiprocessing
import subprocess
from setuptools import setup, Extension, Distribution
import os
import sys
import re
import json
from pathlib import Path


class ModiMSVC:
    def init(self, obj):
        _ = self
        obj.macros.extend([('_CRT_SECURE_NO_WARNINGS', 1), ('_CRT_NONSTDC_NO_DEPRECATE', 1), ('UNICODE', 1),
                           ('_UNICODE', 1), ('_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR', 1)])
        obj.extra_compile_args.extend([f'/Fdbuild/{obj.sysver}.pdb', '/FS', '/Zi', '/O2', '/MD', '/EHsc', '/utf-8', '/std:c++20'])
        obj.extra_link_args.extend(['/debug', '/nodefaultlib:LIBCMT', '/opt:ref', '/opt:icf'])
        obj.libs2 = ['gdi32', 'user32', 'advapi32', 'ws2_32', 'ntdll']
        obj.obj_ext = '.obj'
        os.environ['VSLANG'] = '1033'

    def detect(self, blder, hdr, lib, macros):
        pass

    def compile_cmd(self, blder, inputfn, output):
        _ = self
        if re.search(r'\.asm$', inputfn, re.I):
            return f"""ml64 /nologo /c /Fo{output} {inputfn}"""
        opts = []
        for d in blder.include_dirs:
            opts.append("/I\"%s\"" % d)
        for m in blder.macros:
            opts.append("/D%s=%s" % m)
        return f"""cl /nologo /c {" ".join(opts)} /Fo{output} {inputfn} {" ".join(blder.extra_compile_args)}"""

    def lib_cmd(self, blder, name, objs):
        _ = self, blder
        fname = f"build/{name}.lib"
        return f"""lib /nologo /OUT:"{fname}" {" ".join(objs)}""", fname

    def test_cmd(self, _blder, _d, _s):
        return None, None

    def link_args(self, blder, slib):
        _ = self
        arg1 = [f"/WHOLEARCHIVE:{slib}"]
        libs = []
        for lib in blder.libs + blder.libs2:
            if isinstance(lib, tuple):
                libs.append(lib[0])
            else:
                libs.append(lib)
        arg1 += blder.extra_link_args
        return libs, arg1


class ModiGCC:
    def __init__(self):
        self.libdir1 = []
        gcc_machine = subprocess.check_output(['gcc', '-dumpmachine'], universal_newlines=True).strip()
        m1 = re.sub("-pc-", "-", gcc_machine)
        for p in {gcc_machine, m1}:
            if os.path.isdir(f'/usr/lib/{p}'):
                self.libdir1.append(f'/usr/lib/{p}')

    def init(self, obj):
        _ = self
        obj.macros = []
        obj.extra_compile_args = re.split(r'\s+', """-g -O2 -fpic -Wno-unknown-pragmas -Wno-unused-result
        -Wno-sign-compare -std=c++20 -ffunction-sections -fdata-sections""")
        osname = os.uname().sysname
        if osname == "Darwin":
            obj.extra_link_args.extend(['-lc++', '-g', '-Wl,-dead_strip', '-framework', 'Security'])
        else:
            deffile = f"/tmp/{obj.name}.def"
            with open(deffile, 'w') as f:
                f.write(f"{{\n global: PyInit_{obj.name};\n local: *;\n}};")
            obj.extra_link_args.extend(['-l:libstdc++.a', '-g', '-Wl,-gc-sections', f'-Wl,--version-script={deffile}'])

    def detect(self, blder, hdr, lib, macros):
        found = False
        for d in blder.include_dirs:
            if os.path.isfile(f"{d}/{hdr}"):
                found = True
                break
        if found:
            if lib:
                blder.libs.append(lib)
            if macros:
                blder.macros.extend(macros)

    def pref_static(self, libname):
        dirs = ["/usr/lib", *self.libdir1, "/usr/local/lib"]
        for d in dirs:
            fn = "%s/lib%s.a" % (d, libname)
            if os.path.isfile(fn):
                return fn
        return "-l" + libname

    def compile_cmd(self, blder, inputfn, output):
        _ = self
        opts = []
        for d in blder.include_dirs:
            opts.append("-I%s" % d)
        for m in blder.macros:
            opts.append("-D%s=%s" % m)
        opts += blder.extra_compile_args
        return "gcc -c %s -o %s %s" % (" ".join(opts), output, inputfn)

    def lib_cmd(self, blder, name, objs):
        _ = self, blder
        fname = f"build/lib{name}.a"
        return f"""ar rcs "{fname}" {" ".join(sorted(objs))}""", fname

    def test_cmd(self, blder, dest, libfn):
        if not blder._need_test_link:
            return None, None
        import sysconfig
        libpython = sysconfig.get_config_var('LDLIBRARY')
        libdir = sysconfig.get_config_var('LIBDIR')
        cmd = ""
        for d in blder.include_dirs:
            cmd += "-I%s " % d
        for m in blder.macros:
            cmd += "-D%s=%s " % m
        cmd += " ".join(blder.extra_compile_args)
        cmd += f" -DTEST_LINKER=1 {blder.mainsrc} -L{libdir} -l:{libpython} "
        cmd += "".join(["-L%s " % x for x in blder.libdirs])
        cmd += " ".join(self.link_args(blder, libfn)[1])
        cmd = f"""gcc -o {dest} {cmd}"""
        return cmd, dest

    def link_args(self, blder, slib):
        arg1 = [f"-Wl,--whole-archive", slib, f"-Wl,--no-whole-archive"]
        for lib in blder.libs+blder.libs2:
            if isinstance(lib, tuple):
                if lib[1]:
                    arg1.append(self.pref_static(lib[0]))
                    continue
                lib = lib[0]
            arg1.append("-l" + lib)
        arg1 += blder.extra_link_args
        return [], arg1


class CXXBuilder:
    @staticmethod
    def verbose_build(cmd):
        print(cmd)
        sys.stdout.flush()
        return os.system(cmd)

    @staticmethod
    def load_toml(path) -> dict:
        path = Path(path)
        try:
            # Python 3.11+
            import tomllib
        except ModuleNotFoundError:
            # Python 3.10
            import tomli as tomllib
        with path.open("rb") as f:
            return tomllib.load(f)

    def __init__(self, nt_hooker=None, posix_hooker=None):
        self.is_win = os.name == "nt"
        self.include_dirs = []
        self.libdirs = []
        self.macros = []
        self.libs = []
        self.libs2 = []  # low priority libs, dlls
        self.extra_compile_args = []
        self.extra_link_args = []
        self.files = dict()
        self.mainsrc = None
        self._need_test_link = False
        self.sysver = f"{sys.version_info[0]}.{sys.version_info[1]}"
        self.obj_ext = '.o'
        self.bld_func = os.system
        proj_desc = self.load_toml('pyproject.toml')
        self.name = proj_desc['project']['name']
        self.version = proj_desc['project'].get('version', '0.1.0')
        if self.is_win:
            self.modi = ModiMSVC()
            self.modi.init(self)
            if callable(nt_hooker):
                nt_hooker(self)
        else:
            self.modi = ModiGCC()
            self.modi.init(self)
            if callable(posix_hooker):
                posix_hooker(self)

    def detect(self, hdr, lib, macros=None):
        return self.modi.detect(self, hdr, lib, macros)

    def add_macro(self, key, value=None):
        if value is None:
            self.macros.append((key, 1))
        else:
            self.macros.append((key, value))

    def add_files(self, files, directory=None, kind=None):
        for fn in files:
            if not fn:
                continue
            objn = f"build/objs{self.sysver}/" + re.sub(r"^.*[\\/].[\\/]", "", fn) + self.obj_ext
            objn = os.path.normpath(objn)
            fullfn = fn if directory is None else os.path.join(directory, fn)
            fullfn = os.path.abspath(fullfn)
            self.files[fullfn] = [objn, kind]

    def remove_files(self, files, directory=None):
        for fn in files:
            if not fn:
                continue
            fullfn = fn if directory is None else directory + "/" + fn
            fullfn = os.path.abspath(fullfn)
            if fullfn in self.files:
                del self.files[fullfn]

    def set_main_file(self, fn, directory=None):
        fullfn = fn if directory is None else directory + "/" + fn
        self.mainsrc = fullfn
        with open(self.mainsrc, 'rb') as f:
            self._need_test_link = b'TEST_LINKER' in f.read()
        fullfn = os.path.abspath(fullfn)
        if fullfn in self.files:
            del self.files[fullfn]

    def compile_cmd(self, inputfn, output, kind=None):
        if kind == 'embed':
            return f"""{sys.executable} -m py_cxx_builder embed {inputfn} {output}"""
        return self.modi.compile_cmd(self, inputfn, output)

    def build(self, nprocess=None):
        major_version, minor_version, patch_version = tuple([int(x) for x in self.version.split('.')])
        self.add_macro('PROJ_MAJOR_VERSION', major_version)
        self.add_macro('PROJ_MINOR_VERSION', minor_version)
        self.add_macro('PROJ_PATCH_VERSION', patch_version)
        assert self.mainsrc is not None
        self.include_dirs = self._get_include_dirs()
        self.libdirs = self._get_lib_dirs()
        dirs = dict()
        for _, v in self.files.items():
            dirs[re.sub(r"[\\/][^\\/]+$", '', v[0])] = True
        for d in sorted(dirs.keys()):
            if not os.path.isdir(d):
                os.makedirs(d, exist_ok=True)
        o_cmds = []
        cmds = []
        objs = []
        for k, v in self.files.items():
            kind = v[1]
            cmd = self.compile_cmd(k, v[0], kind)
            o_cmds.append({"directory": os.getcwd(), "command": cmd, "file": k, "output": v[0]})
            objs.append(v[0])
            if self._need_compile(k, v[0], kind):
                cmds.append(cmd)
        libcmd, libfn = self.modi.lib_cmd(self, f'objs-static{self.sysver}', objs)
        testcmd, testfn = self.modi.test_cmd(self, 'test_compile.exe', libfn)
        if nprocess is None:
            nprocess = os.cpu_count()
        nprocess = min(len(cmds), nprocess)
        if nprocess > 1:
            with multiprocessing.Pool(processes=nprocess) as pool:
                ress = [pool.apply_async(self.bld_func, (cmd,)) for cmd in cmds]
                codes = [res.get() for res in ress]
                if any(c != 0 for c in codes):
                    raise Exception("compile error")
        elif nprocess == 1:
            for cmd in cmds:
                print(cmd, file=sys.stderr, flush=True)
                if os.system(cmd) != 0:
                    raise Exception("compile error")
        if nprocess > 0 or not os.path.isfile(libfn):
            with open('compile_commands.json', 'w') as f:
                json.dump(o_cmds, f, indent=4, ensure_ascii=False)
            print(libcmd, file=sys.stderr, flush=True)
            if os.system(libcmd) != 0:
                raise Exception("link error")
            os.utime(self.mainsrc, None)
        if testfn and self._need_compile(libfn, testfn):
            print(testcmd, file=sys.stderr, flush=True)
            if os.system(testcmd) != 0:
                raise Exception('link error')

        setup(ext_modules=[self._ext_module(self.name, libfn)])

    def _need_compile(self, src, dst, kind=None):
        _ = self
        try:
            dstt = os.stat(dst)
        except FileNotFoundError:
            return True
        srct = os.stat(src)
        if dstt.st_mtime < srct.st_mtime:
            return True
        if kind and kind == 'embed':
            return False
        srct2 = os.stat(os.path.dirname(src) or '.')
        return dstt.st_mtime < srct2.st_mtime

    def _ext_module(self, name, slib):
        libs, linkargs = self.modi.link_args(self, slib)
        ext = Extension(name, sources=[self.mainsrc],
                        include_dirs=self.include_dirs,
                        define_macros=self.macros,
                        libraries=libs,
                        library_dirs=self.libdirs,
                        extra_compile_args=self.extra_compile_args,
                        extra_link_args=linkargs)
        return ext

    def _get_include_dirs(self):
        """ a hacker way to get the current python include dirs """
        dist = Distribution(dict(name='dummy', version='1.0', description='dummy', ext_modules=[
            Extension('dummy', sources=['dummy.c'])
        ]))
        co = dist.get_command_obj('build_ext')
        co.ensure_finalized()
        seen = {''}
        seq = getattr(co, 'include_dirs', []) + self.include_dirs
        return [x for x in seq if not (x in seen or seen.add(x))]

    def _get_lib_dirs(self):
        """ collect all lib dirs """
        seen = {''}
        seq = [x for x in self.libdirs if not (x in seen or seen.add(x))]
        return [x for x in seq if os.path.isdir(x)]
