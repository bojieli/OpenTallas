#!/usr/bin/env python3
"""Near-HBM attention on the REAL_MEM service at long context: build the bench and run one layer / a layer chain.

Successor of tools/qwen_nearhbm_realmem_gate.py (pinned to context 129).  The near-HBM subsystem is the replay
system bench (rtl/test/qwen_sys/ot_qwen_nearhbm_sys_tb_replay.sv) built with the timing successors hub_p + stack_p
(rtl/test/nearhbm/hubp_swap.sh, NHB_SWAP=hub,stack), R = 8, LAYER_START_FENCE = 1.  The memory component is
rtl/test/qwen_sys/realmem/ot_qwen_nearhbm_realmem_ctx_tb.sv over ot_qwen_nearhbm_realmem_service_nt with
NEAR_TAIL = 0 (the adapter as built: full-window tile fill) or NEAR_TAIL = 1 (open K tile only).

    python3 tools/qwen_nearhbm_realmem_ctx_gate.py build --work W [--verilator V] [--jobs 16]
    python3 tools/qwen_nearhbm_realmem_ctx_gate.py run --work W --tail 0|1 --gate kvok|drained \
        --schedule T_V,GAP_K1,GAP_K2,SUFFIX --out RESULT.json VECDIR...
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEM_FILES = ['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv', 'rtl/hdc/kv/ot_qwen_rt_kv_fill_service_nt.sv',
             'rtl/hdc/kv/ot_qwen_hbm_model_ack.sv', 'rtl/hdc/nearhbm/ot_qwen_nearhbm_row_sectors.sv',
             'rtl/hdc/nearhbm/ot_qwen_nearhbm_realmem_service_nt.sv',
             'rtl/test/qwen_sys/realmem/ot_qwen_nearhbm_realmem_ctx_tb.sv',
             'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']
NEAR_FILES = ['rtl/test/qwen_sys/build_nearhbm_sys_replay.sh', 'rtl/test/nearhbm/hubp_swap.sh',
              'rtl/test/qwen_sys/ot_qwen_nearhbm_sys_tb_replay.sv', 'rtl/test/qwen_sys/tb_qwen_nearhbm_sys.cpp',
              'rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_p.sv', 'rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_p.sv',
              'rtl/test/nearhbm/ot_qwen_nearhbm_attn_hub_shim_p.sv', 'rtl/test/nearhbm/ot_qwen_nearhbm_attn_stack_shim_p.sv',
              'rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv', 'rtl/hdc/nearhbm/ot_qwen_nearhbm_sfu_p.sv',
              'rtl/qwen_sys/ot_qwen_d2d_link.sv', 'rtl/test/qwen_sys/ot_qwen_d2d_chan.sv']
DRIVER = ['rtl/test/qwen_sys/realmem/qwen_nearhbm_realmem_ctx.cpp', 'tools/runtime/qwen_combined/fullshape_context.hpp']
VL = os.path.expanduser('~/.local/opentallas-tools/verilator-5.050/bin/verilator')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pins():
    return {p: sha(ROOT / p) for p in MEM_FILES + NEAR_FILES + DRIVER + ['tools/qwen_nearhbm_realmem_ctx_gate.py']}


def step(w, name, cmd, env=None, resume=False):
    if resume and (w / f'{name}.exit').is_file() and (w / f'{name}.exit').read_text().strip() == '0':
        return 'reused'
    t = time.monotonic()
    with (w / f'{name}.log').open('w') as log:
        r = subprocess.run(list(map(str, cmd)), cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, env=env)
    (w / f'{name}.exit').write_text(f'{r.returncode}\n')
    if r.returncode:
        raise SystemExit(f'{name} failed ({r.returncode}); log {w / (name + ".log")}')
    return round(time.monotonic() - t, 1)


def build(a):
    w = a.work.resolve()
    if w.exists() and not a.resume:
        raise SystemExit('immutable work path already exists (--resume reuses its completed near/mem steps)')
    w.mkdir(parents=True, exist_ok=True)
    rec = {'schema': 'opentallas.qwen-nearhbm-realmem-ctx-build.v1', 'source_sha256': pins(), 'steps': {}}
    env = dict(os.environ, NHB_SWAP='hub,stack', VL=a.verilator, VJOBS=str(a.jobs))
    near = w / 'near'
    if a.near_from:
        near = a.near_from.resolve() / 'near'
        rec['near_from'] = {'work': str(a.near_from.resolve()), 'build_json_sha256': sha(a.near_from.resolve() / 'build.json')}
        old = json.loads((a.near_from.resolve() / 'build.json').read_text())['source_sha256']
        if any(old.get(f) != rec['source_sha256'][f] for f in NEAR_FILES):
            raise SystemExit('--near-from build was made from different near-HBM sources')
    else:
        rec['steps']['near'] = step(w, 'near', ['bash', 'rtl/test/nearhbm/hubp_swap.sh', 'rtl/test/qwen_sys/build_nearhbm_sys_replay.sh',
                                                near, 128, 8, 'dpi', '-GLAYER_START_FENCE=1'], env, a.resume)
    arch = near / 'Vot_qwen_nearhbm_sys_tb__ALL.a'
    dpi = [near / 'sim_nhb_fp_lat_dpi.o', near / 'sim_hdc_v41x_fastfp_dpi.o']
    for p in [arch, *dpi]:
        if not p.is_file():
            raise SystemExit(f'missing near build product {p}')
    vr = re.search(r'VERILATOR_ROOT\s*=\s*(\S+)', subprocess.check_output([a.verilator, '-V'], text=True)).group(1)
    rec['mem_generics'] = a.mem_g
    for tail in a.tails:
        obj = w / f'obj_mem_t{tail}'
        obj.mkdir(exist_ok=True)
        pub = w / 'public.vlt'
        pub.write_text('`verilator_config\npublic_flat_rw -module "ot_qwen_hbm_model_ack" -var "mem"\n')
        rec['steps'][f'mem_t{tail}'] = step(w, f'mem_t{tail}', [a.verilator, '--cc', '--build', '-j', a.jobs, '-O2', '-Wno-fatal', '-Wno-lint',
                                                                '-Wno-style', '-Wno-MULTIDRIVEN', '-Wno-TIMESCALEMOD', f'-GNEAR_TAIL={tail}', *(f'-G{g}' for g in a.mem_g),
                                                                '--top-module', 'ot_qwen_nearhbm_realmem_ctx_tb', '--prefix', 'Vmem', '--Mdir', obj,
                                                                pub, *(ROOT / p for p in MEM_FILES)], resume=a.resume)
        hdr = (obj / 'Vmem___024root.h').read_text()
        names = []
        for s in range(4):
            found = set(re.findall(r'\b(\w*g_hbm__BRA__' + str(s) + r'__KET__\w*__DOT__mem)\b', hdr))
            if len(found) != 1:
                raise SystemExit(f'missing or ambiguous HBM array {s}')
            names.append(found.pop())
        (obj / 'mem_access.hpp').write_text('#pragma once\n#include <cstdlib>\nstatic uint32_t& mem_word(Vmem& m,int s,int a,int w){switch(s){\n' +
                                            ''.join(f'case {s}:return m.rootp->{n}[a][w];\n' for s, n in enumerate(names)) + 'default:std::abort();}}\n')
        exe = w / f'connected_ctx_t{tail}'
        incs = [f'-I{x}' for x in [obj, near, ROOT / 'tools/runtime/qwen_combined', Path(vr) / 'include', Path(vr) / 'include/vltstd']]
        rec['steps'][f'link_t{tail}'] = step(w, f'link_t{tail}', ['g++', '-std=c++20', '-O1', '-pthread', *incs, ROOT / DRIVER[0],
                                                                  '-Wl,--start-group', obj / 'Vmem__ALL.a', arch, *dpi, '-Wl,--end-group',
                                                                  Path(vr) / 'include/verilated.cpp', Path(vr) / 'include/verilated_dpi.cpp',
                                                                  Path(vr) / 'include/verilated_threads.cpp', '-o', exe])
        rec[f'binary_t{tail}_sha256'] = sha(exe)
    rec['source_stable'] = rec['source_sha256'] == pins()
    (w / 'build.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({k: rec[k] for k in rec if k != 'source_sha256'}))


def run(a):
    w = a.work.resolve()
    b = json.loads((w / 'build.json').read_text())
    exe = w / f'connected_ctx_t{a.tail}'
    if sha(exe) != b[f'binary_t{a.tail}_sha256']:
        raise SystemExit('binary differs from its build record')
    sched = [int(x) for x in a.schedule.split(',')]
    t = time.monotonic()
    r = subprocess.run([str(exe), a.gate, *map(str, sched), *map(str, a.vectors)], capture_output=True, text=True)
    out = {'schema': 'opentallas.qwen-nearhbm-realmem-ctx-run.v1', 'near_tail': a.tail, 'gate': a.gate,
           'vectors': {str(v): {f: sha(Path(v) / f) for f in ('q.hex', 'kv.hex', 'gold.hex', 'meta.json')} for v in a.vectors},
           'binary_sha256': b[f'binary_t{a.tail}_sha256'], 'build_record_sha256': sha(w / 'build.json'),
           'returncode': r.returncode, 'wall_s': round(time.monotonic() - t, 1), 'stderr_tail': r.stderr[-2000:]}
    try:
        out['measurement'] = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        out['measurement'] = None
        out['stdout_tail'] = r.stdout[-2000:]
    out['status'] = 'pass' if r.returncode == 0 and out['measurement'] and out['measurement']['status'] == 'pass' else 'fail'
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({'status': out['status'], 'out': str(a.out)}))
    return 0 if out['status'] == 'pass' else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build')
    b.add_argument('--work', type=Path, required=True)
    b.add_argument('--verilator', default=VL)
    b.add_argument('--jobs', type=int, default=16)
    b.add_argument('--resume', action='store_true', help='reuse completed near/mem compile steps (relink the driver)')
    b.add_argument('--near-from', type=Path, help='reuse the near archive of a completed build (its NEAR_FILES pins must match)')
    b.add_argument('--tails', type=int, nargs='+', default=[0, 1], choices=(0, 1))
    b.add_argument('--mem-g', action='append', default=[], help='extra memory-bench generic NAME=VALUE (e.g. REFI_PS=2000000000)')
    r = sub.add_parser('run')
    r.add_argument('--work', type=Path, required=True)
    r.add_argument('--tail', type=int, choices=(0, 1), required=True)
    r.add_argument('--gate', choices=('kvok', 'drained'), required=True)
    r.add_argument('--schedule', required=True)
    r.add_argument('--out', type=Path, required=True)
    r.add_argument('vectors', type=Path, nargs='+')
    a = ap.parse_args()
    if a.cmd == 'build':
        build(a)
        return 0
    return run(a)


if __name__ == '__main__':
    raise SystemExit(main())
