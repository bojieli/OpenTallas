#!/usr/bin/env python3
"""Extract the opt-in Q3 body with the physical VM face round-trip contract.

Run through ot-run. The one-way select remains VM_RT=81; VM_FACE_RT=2
accounts for direct checker returns; VM_ASM_FACE_RT=2 adds the VM-to-body
assembly face pair. Metadata and assembled-valid move four cycles in total.
The generated body keeps every canonical cut port and the original wrapper.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
BASE = 'ot_hfd_coll_q3_body_core'
CANON = 'rtl/hbm_accel/cores_split/ot_hfd_coll_q3_hard_v8x/' + BASE + '.sv'
FILELIST = 'tools/hbm_b2/q3sync/q3b.files'
TOP = 'ot_hfd_coll_q3_hard_v8x_s'
KEEP = ['ot_hgi_coll_ring_ag', 'ot_hgi_coll_reduce_static_pr', 'ot_hgi_coll_link_e',
        'ot_hgi_coll_link_e_pr', 'ot_hgi_coll_argmax_m_tp192', 'ot_hgi_coll_argmax_m_tp192_pr',
        'ot_hgi_coll_vmasm_sliced_v7',
        'ot_hgi_coll_static_vmwrite_roots_v6_physical']
EXCLUDE = ['c:u_body.u_ring', 'c:u_body.u_reduce', 'c:u_body.g_link*', 'c:*u_arg',
           'c:u_body.u_vmasm', 'c:u_body.u_writer']


def module(text, name):
    m = re.search(r'(?ms)^module\s+\\?' + re.escape(name) + r'\b.*?^endmodule\s*$', text)
    if not m:
        raise ValueError('empty or missing extracted module: ' + name)
    return m.group(0)


def ports(text):
    return sorted((d, int(a) - int(b) + 1 if a else 1, n.lstrip('\\'))
                  for d, a, b, n in re.findall(
                      r'(?m)^  (input|output|inout)\s+(?:signed\s+)?(?:\[(\d+):(\d+)\]\s*)?(\S+)\s*;', text))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', required=True, type=Path)
    args = ap.parse_args()
    out = args.out.resolve()
    if out.exists() and any(out.iterdir()):
        ap.error('output must be empty or new; prior extraction evidence is retained')
    out.mkdir(parents=True, exist_ok=True)
    lines = [s.strip() for s in (ROOT / FILELIST).read_text().splitlines()
             if s.strip() and not s.lstrip().startswith('#')]
    files = [s for s in lines if not s.startswith('macro:')]
    macros = ['physical/asap7_memory_macros_v2/' + s[6:] + '/' + s[6:] + '_bb.v'
              for s in lines if s.startswith('macro:')]
    cmds = [f'read_verilog -lib {p}' for p in macros]
    cmds += [f'read_verilog -sv -DSYNTHESIS -DOT_COLL_ISSUER256_NATIVE32 {p}' for p in files]
    params = dict(NLINK=3, TP=192, AR_ITER=1, ROWS=256, VM_RT=81, VM_FACE_RT=2, VM_ASM_FACE_RT=2)
    cmds += [f'chparam -set {k} {v} {TOP}' for k, v in params.items()]
    cmds += [f'hierarchy -check -top {TOP}', 'rename -top elab_top', 'proc', 'opt_clean']
    cmds += [f'setattr -mod -set keep_hierarchy 1 {m} $paramod*\\\\{m}*' for m in KEEP]
    cmds += ['flatten', 'opt_clean', 'splitnets', 'opt_clean', 'memory_map elab_top', 'cd elab_top',
             'select -set ex ' + ' '.join(EXCLUDE), 'tee -o /out/excluded.txt select -list @ex',
             f'submod -name {BASE}_x c:* @ex %d', 'cd ..', f'select {BASE}_x',
             'write_verilog -selected -noattr /out/body_extract.v']
    (out / 'extract.ys').write_text('\n'.join(cmds) + '\n')
    subprocess.run(['docker', 'run', '--rm', '-v', f'{ROOT}:/src:ro', '-v', f'{out}:/out', '-w', '/src',
                    'openroad/orfs:asap7lock', 'bash', '-lc',
                    'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -q -l /out/extract.log -s /out/extract.ys'], check=True)
    original = (ROOT / CANON).read_text()
    new = module((out / 'body_extract.v').read_text(), BASE + '_x')
    old = module(original, BASE + '_x')
    if ports(new) != ports(old):
        (out / 'port_difference.json').write_text(json.dumps(
            dict(added=sorted(set(ports(new))-set(ports(old))), removed=sorted(set(ports(old))-set(ports(new)))), indent=2))
        raise SystemExit('Q3_VMF_BODY_FAIL: canonical raw cut ports changed; revise the source before adoption')
    result = out / (BASE + '.sv')
    result.write_text('// GENERATED opt-in VM_FACE_RT=2 VM_ASM_FACE_RT=2 by tools/hbm_b2/q3sync/build_vmface_body.py; '
                      'VM_RT=81 one-way select unchanged; canonical cut/wrapper unchanged.\n'
                      '`timescale 1ns/1ps\n' + new + '\n\n' + module(original, BASE) + '\n')
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    receipt = dict(source_commit=commit, params=params, defines=['SYNTHESIS', 'OT_COLL_ISSUER256_NATIVE32'],
                   source_inputs={p: h(ROOT / p) for p in [FILELIST, CANON, *files, *macros]},
                   output=result.name, output_sha256=h(result), canonical_cut_ports=len(ports(new)),
                   exported_select_added_cycles=0, checker_added_cycles=2, metadata_added_cycles=4,
                   assembled_valid_added_cycles=4, additional_control_metadata_flops=600,
                   physical_qualification='NOT_BUILT')
    (out / 'source_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('Q3_VMF_BODY_PASS', len(ports(new)), 'canonical cut ports;', result)


if __name__ == '__main__':
    main()
