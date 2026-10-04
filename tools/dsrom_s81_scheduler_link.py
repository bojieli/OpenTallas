#!/usr/bin/env python3
"""Link only existing native archives; never invokes a model build."""
import argparse
import os
import subprocess
from pathlib import Path

PREFIXES = ('Vdie0','Vdie1','Vdie2','Vdie3','Vpq','Vpb','Vrd64','Vattn')


def command(source, owner, verilator_root, includes, archives, output, compiler='c++'):
    source, owner, verilator_root = Path(source), Path(owner), Path(verilator_root)
    includes, archives = list(map(Path,includes)), list(map(Path,archives))
    for prefix in PREFIXES:
        if not any((d/(prefix+'.h')).is_file() for d in includes):
            raise FileNotFoundError('sole native build header not ready: '+prefix)
    for a in archives:
        if not a.is_file():raise FileNotFoundError(a)
    if not archives:raise ValueError('actual native hierarchical archives required')
    runtime = ['verilated.cpp','verilated_dpi.cpp','verilated_threads.cpp']
    runtime = [verilator_root/'include'/name for name in runtime]
    if not all(p.is_file() for p in runtime):raise FileNotFoundError('selected Verilator runtime')
    return [compiler,'-std=c++17','-O1','-pthread','-rdynamic',
            '-DDSROM_C8_LIBRARY=1','-DDSROM_C8_S81=1','-DDSROM_S81_CAPTURE=1','-DV41_L20',
            *[f'-I{d}' for d in [source.parent,*includes,verilator_root/'include',
                               verilator_root/'include/vltstd',owner/'rtl/test/qwen_runtime']],
            str(source),*map(str,runtime),'-Wl,--start-group',*map(str,archives),
            '-Wl,--end-group','-ldl','-o',str(output)]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--owner',type=Path,required=True)
    p.add_argument('--verilator-root',type=Path,required=True)
    p.add_argument('--include',action='append',default=[],required=True)
    p.add_argument('--archive',action='append',default=[],required=True,
                   help='exact existing top and hierarchical child archives from owner build')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--compiler',default=os.environ.get('CXX','c++'))
    p.add_argument('--caller-source',type=Path,
                   help='actual enclosing source scheduler defining dsrom_s81_source_main')
    p.add_argument('--caller-output',type=Path,
                   help='shared caller executable hook; no model objects are rebuilt')
    a=p.parse_args()
    if a.output.exists():raise FileExistsError('preserve existing executable: '+str(a.output))
    cmd=command(a.source,a.owner,a.verilator_root,a.include,a.archive,a.output,a.compiler)
    if bool(a.caller_source) != bool(a.caller_output):
        p.error('--caller-source and --caller-output must be supplied together')
    if a.caller_source:
        if not a.caller_source.is_file():raise FileNotFoundError(a.caller_source)
        if a.caller_output.exists():raise FileExistsError(a.caller_output)
        rc=subprocess.call([a.compiler,'-std=c++17','-O1','-shared','-fPIC',
                            '-DDSROM_C8_S81=1','-DDSROM_S81_CAPTURE=1','-DV41_L20',
                            f'-I{a.source.parent}',str(a.caller_source),'-o',str(a.caller_output)])
        if rc:raise SystemExit(rc)
    raise SystemExit(subprocess.call(cmd))


if __name__ == '__main__':
    main()
