#!/usr/bin/env python3
"""Prepare the plain-AR STREAM4 top using the measured W12 hierarchical leaves.

Only the top is generated again: the three unchanged compute leaves, tile and
collective are copied from the measured build. No near-attention or verify core
is selected. This tool prepares commands; the owning remote job executes them.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP = 'ot_qwen_rom_rt_die_w12_stream4_tagged_ar'
HOST = 'tools/runtime/qwen_baseline_ar_stream4/qwen_rom_rt_w12_stream4_fulltoken.cpp'
LEAVES = ('Vot_hdc_fmul', 'Vot_hdc_qadd', 'Vot_hdc_vstream_lane_a')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(measured, native, output, source=ROOT):
    measured, native, output, source = map(Path, (measured, native, output, source))
    top = source / 'rtl/qwen_sys/baseline_ar_stream4' / (TOP + '.sv')
    host = source / HOST
    for path in (top, host, measured/'die/Vdie__hierMkArgs.f'):
        if not path.is_file():
            raise FileNotFoundError(path)
    params = json.loads((measured/'build_params.json').read_text())
    die = {p[2:].split('=', 1)[0]: int(p.split('=', 1)[1]) for p in params['die']}
    required = dict(G=6144, NW=18, SNW=18, D=4, SW=64, SMIN=7,
                    REAL_MEM=1, ENABLE_AR256=1, NSTK=4, WBW=4, HBM_PULLIN=16)
    if any(die.get(k) != v for k, v in required.items()):
        raise ValueError('measured W12 geometry/service parameters differ')
    if any(k in die for k in ('DSPARK', 'VPOS', 'NEAR_HBM', 'ACCEPT_COMMIT')):
        raise ValueError('expected the ordinary measured W12 core')
    for leaf in LEAVES:
        if not list((measured/'die'/leaf).glob('lib*.a')):
            raise FileNotFoundError('completed measured leaf: '+leaf)
    for model in ('coll', 'tile'):
        if not (measured/model/f'V{model}__ALL.a').is_file():
            raise FileNotFoundError('completed measured '+model)
    tagged = native/'rtl/hdc/kv/ot_qwen_hbm_stream4_tagged.sv'
    pc = native/'rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv'
    stack = native/'rtl/model_ready_hbm_r14/ot_hbm_r14_stream_stack.sv'
    for path in (tagged, pc, stack):
        if not path.is_file():
            raise FileNotFoundError(path)
    output.mkdir(exist_ok=False, parents=True)
    reuse = output/'reuse'
    reuse.mkdir()
    shutil.copytree(measured/'gen', reuse/'gen')
    for model in ('coll', 'tile'):
        # Copy completed products; these makefiles are never invoked.
        shutil.copytree(measured/model, reuse/model)
    build = output/'die'
    build.mkdir()
    for leaf in LEAVES:
        shutil.copytree(measured/'die'/leaf, build/leaf)
    text = (measured/'die/Vdie__hierMkArgs.f').read_text()
    lines = text.splitlines()
    original_top = next(p for p in lines if p.endswith('/ot_qwen_rom_rt_die_w12_stream4.sv'))
    original_ack = next(p for p in lines if p.endswith('/ot_qwen_hbm_stream4_ack.sv'))
    lines.remove(original_ack)
    text = '\n'.join(lines)+'\n'
    text = text.replace(original_top, str(top))
    for path in (pc, stack):
        old = next(p for p in lines if p.endswith('/'+path.name))
        text = text.replace(old, str(path))
    text = str(tagged)+'\n'+text
    text = text.replace('--top-module ot_qwen_rom_rt_die_w12_stream4', '--top-module '+TOP)
    text = text.replace('-Mdir '+str(measured/'die'), '-Mdir '+str(build))
    text = text.replace(str(measured/'gen'), str(reuse/'gen'))
    old = f'-GHBM_LAYERS={die["HBM_LAYERS"]}'
    if text.count(old) != 1:
        raise ValueError('HBM extent argument is missing or ambiguous')
    text = text.replace(old, '-GHBM_LAYERS=36')
    (output/'top.args.f').write_text(text)
    params['die'] = [p if not p.startswith('-GHBM_LAYERS=') else '-GHBM_LAYERS=36'
                     for p in params['die']]
    pins = {str(p): sha(p) for p in (top, host, tagged, pc, stack,
            measured/'die/Vdie__hierMkArgs.f', measured/'build_params.json')}
    for leaf in LEAVES:
        for path in (build/leaf).glob('*.sv'):
            pins[str(path)] = sha(path)
        for path in (build/leaf).glob('lib*.a'):
            pins[str(path)] = sha(path)
    book = dict(top=TOP, source_root=str(source), measured=str(measured),
                native=str(native), parameters=params, source_sha256=pins,
                workload=dict(position=8191, token=24, layers=36, head=True,
                              near_attention=False, dspark=False, accept=False),
                reused_leaves=list(LEAVES), scope='Unmeasured full36 plain-AR native STREAM4 successor')
    (output/'selection.json').write_text(json.dumps(book, indent=2)+'\n')
    return book


def access(output):
    output = Path(output)
    book = json.loads((output/'selection.json').read_text())
    command = [sys.executable, str(Path(book['source_root'])/'tools/qwen_rom_rt_baseline_ar_stream4_access.py'),
                '--die-header', str(output/'die/Vdie___024root.h'),
                '--tile-header', str(output/'reuse/tile/Vtile___024root.h'),
                '--nport', '48', '--scale-banks', '13', '--code-banks', '5',
                '--crom-words', '1048576', '--hbm-layers', '36', '--kv-ideal', '0',
                '--embed-rom', '1', '--out', str(output/'reuse/gen/rm_access.hpp')]
    subprocess.run(command, check=True)


def link(output, verilator_root, cxx):
    output, verilator_root = Path(output), Path(verilator_root)
    book = json.loads((output/'selection.json').read_text())
    for path, digest in book['source_sha256'].items():
        if sha(path) != digest:
            raise ValueError('selected source/archive changed: '+path)
    source = Path(book['source_root'])
    includes = {verilator_root/'include', verilator_root/'include/vltstd',
                source/'rtl/test/qwen_runtime', source/'rtl/test/qwen_rom_runtime',
                output/'reuse/gen'}
    archives = []
    for model in (output/'die', output/'reuse/coll', output/'reuse/tile'):
        includes.add(model)
        includes.update(p.parent for p in model.rglob('V*.h'))
        archives.extend(sorted(model.rglob('*.a')))
    if not (output/'die/Vdie__ALL.a').is_file():
        raise FileNotFoundError('completed selected top archive')
    command = [cxx, '-std=c++20', '-O2', '-pthread', '-DGROUPS=6144', '-DCOUNTWIDTH=18',
               '-DSWIDTH=64', '-DSMAXB=11', '-DTCUTL=7', '-DNWSD=5', '-DXVMD=1',
               '-DTPD=4', '-DCBANKS=5', '-DSMINV=7',
               *('-I'+str(p) for p in sorted(includes)), str(source/HOST),
               '-Wl,--start-group', *map(str, archives), '-Wl,--end-group',
               *(str(verilator_root/'include'/p) for p in
                 ('verilated.cpp', 'verilated_threads.cpp', 'verilated_dpi.cpp')),
               '-o', str(output/'qwen_plain_ar_stream4')]
    (output/'link.command.json').write_text(json.dumps(command, indent=2)+'\n')
    subprocess.run(command, check=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase', choices=('prepare', 'access', 'link'))
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--measured', type=Path)
    p.add_argument('--native', type=Path)
    p.add_argument('--verilator-root', type=Path)
    p.add_argument('--cxx', default='g++-15')
    a = p.parse_args()
    if a.phase == 'prepare':
        if a.measured is None or a.native is None:
            p.error('prepare requires --measured and --native')
        print(json.dumps(prepare(a.measured, a.native, a.output), indent=2))
    elif a.phase == 'access':
        access(a.output)
    else:
        if a.verilator_root is None:
            p.error('link requires --verilator-root')
        link(a.output, a.verilator_root, a.cxx)
