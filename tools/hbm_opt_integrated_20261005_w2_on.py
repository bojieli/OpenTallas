#!/usr/bin/env python3
"""Enabled minimum parent elaboration, without a token binary or fixture generation.

The installed map/readyless native caller remain real top-level ports. This
checks their connected source hierarchy, not installed bytes, numerical output,
permissions, timing or adoption. Hubble owns the exhaustive byte runtime.
"""
import argparse
import ast
import json
import os
import re
from pathlib import Path
import shutil
import subprocess

OWN = 'rtl/hbm_accel/integrated_20261005/'
OWN_FILES = [OWN + n + '.sv' for n in (
    'ot_ds_hbm_cluster20_integrated', 'ot_hbm_integrated_cp_reset',
    'ot_hbm_integrated_prior_debt', 'ot_hbm_integrated_sm0_borrow',
    'ot_hbm_integrated_gather_bridge', 'ot_hbm_integrated_gather_owner',
    'ot_hbm_integrated_su_cp_bind', 'ot_hbm_integrated_su_cp_association',
    'ot_hbm_integrated_header_decode',
    'ot_hbm_integrated_formatter_provider', 'ot_hbm_integrated_w15_store',
    'ot_hbm_integrated_w2_result_sink')]
PEER_FILES = ['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',
              OWN + 'ot_hbm_integrated_w2_sector_adapter.sv',
              'rtl/hbm_accel/su/ot_hbm_accel_su_parent_exec.sv']
# Exact installed dimensions: original two-die/four-SM parent.
# The collective tag pipeline does not support a one-rank reduction fabric.
PARAMS = dict(ENABLE=1, COMBINED_ENABLE=1, W2_RESULT_ENABLE=1,
              W2_SECTOR_ENABLE=1, SU_ENABLE=1, SU_PROVIDER_ADAPTER=1,
              SU_REGISTERED_OUTPUTS=1, SU_REGISTERED_STATUS=1, SU_REGISTERED_BOUNDARY=1,
              SU_BALANCED_OWNER_BOUNDARY=1, SU_FOUR_COMBINATIONAL_CUTS=1, SU_FAST_OWNER_FRONTIER=1, ND=2, NSM=2, NS=2, NPC=2,
              MEM_WORDS=2097152, VM_AW=21)

def prepare(own, peer, work):
    tree = ast.parse((peer / 'tools/gpu_sys/ds_hbm_cluster_sources.py').read_text())
    lists = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            if n.targets[0].id in ('BASE', 'PRIMITIVES'):
                lists[n.targets[0].id] = ast.literal_eval(n.value)
    files = [(peer, x) for x in PEER_FILES + lists['BASE'] + lists['PRIMITIVES'] + [
        'rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv',
        'rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_simt_sm20.sv',
        'rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cluster20.sv']]
    files += [(own, x) for x in OWN_FILES]
    files += [(own, 'rtl/hbm_accel/integrated_20261006/ot_hbm_integrated_su_provider_adapter.sv')]
    # Parse-time native executor fields are required even with SU disabled.
    includes = ['rtl/test/tb_hdc_v41x_vec_fields.svh']
    missing = [str(root / rel) for root, rel in files if not (root / rel).is_file()]
    missing += [str(peer / rel) for rel in includes if not (peer / rel).is_file()]
    if missing:
        raise FileNotFoundError('\n'.join(missing))
    work.mkdir(parents=True, exist_ok=False)
    ordered = []
    for root, rel in files:
        if rel in ordered:
            continue
        dst = work / 'src' / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / rel, dst)
        ordered.append(rel)
    for rel in includes:
        dst = work / 'src' / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(peer / rel, dst)
    (work / 'sources.json').write_text(json.dumps(ordered, indent=2) + '\n')
    shutil.copyfile(Path(__file__), work / 'run.py')
    print(f'PREPARED enabled parent ND2/NSM2/NS2, {len(ordered)} actual sources; no execution')

def run(work, tool):
    sources = json.loads((work / 'sources.json').read_text())
    os.environ['TMPDIR'] = str(work / 'tmp')
    (work / 'tmp').mkdir(exist_ok=True)
    command = [str(tool), '--lint-only', '--timing', '-Wno-fatal',
               '--top-module', 'ot_ds_hbm_cluster20_integrated',
               '--Mdir', str(work / 'obj'), '-I' + str(work / 'src/rtl/test')]
    command += [f'-G{k}={v}' for k, v in PARAMS.items()]
    command += [str(work / 'src' / p) for p in sources]
    (work / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    with (work / 'elaboration.log').open('w') as log:
        rc = subprocess.run(command, cwd=work, stdout=log, stderr=subprocess.STDOUT).returncode
    (work / 'frontend.exit').write_text(str(rc) + '\n')
    # A permissive frontend exit must not qualify an out-of-range hierarchy.
    dangerous = re.findall(r'%Warning-(LATCH|UNOPTFLAT|SELRANGE|PIN[^:]*|USERERROR):',
                           (work / 'elaboration.log').read_text())
    if not rc and dangerous:
        print('REJECT_ENABLED_PARENT_DIAGNOSTICS ' + ','.join(sorted(set(dangerous))))
        rc = 1
    (work / 'elaboration.exit').write_text(str(rc) + '\n')
    if not rc:
        print('PASS_ENABLED_W2_PARENT_ELABORATION_ONLY')
    return rc

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--own-root', type=Path)
    parser.add_argument('--peer-root', type=Path)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--tool', type=Path, default=Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator')
    args = parser.parse_args()
    if args.prepare:
        if args.own_root is None or args.peer_root is None:
            parser.error('--prepare requires actual --own-root and --peer-root')
        prepare(args.own_root.resolve(), args.peer_root.resolve(), args.work.resolve())
        return 0
    return run(args.work.resolve(), args.tool)

if __name__ == '__main__':
    raise SystemExit(main())
