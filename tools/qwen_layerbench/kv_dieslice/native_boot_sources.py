#!/usr/bin/env python3
"""Refresh an OWN staged native KV vehicle from one selected boot RTL checkout.

Apply before build.sh: all direct and library-search copies are replaced,
so inline partitions and hierarchical libraries consume the same boot window.
This does not regenerate the bind or change its physical interfaces.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

NAMES = ('ot_qkd_static_kv_timing.sv', 'ot_qkd_static_ctrl_pc_emb.sv',
         'qkd_ctrl_pc_nc.sv', 'qkd_ctrl_pc_host_static_core.sv',
         'qkd_kvpc_sram_clones_1019.sv')


def refresh(vehicle, tree):
    vehicle, tree = Path(vehicle).resolve(), Path(tree).resolve()
    source = tree / 'rtl/qwen_sys/static_kv_20261014'
    contents = {n: (source / n).read_bytes() for n in NAMES}
    if b'boot_win' not in contents['qkd_ctrl_pc_nc.sv']:
        raise ValueError('selected source checkout has no qualified boot window')
    targets = {n: sorted((vehicle / 'src').rglob(n)) for n in NAMES}
    missing = [n for n in NAMES[:4] if not targets[n]]
    if missing:
        raise ValueError('staged native source missing: ' + ', '.join(missing))
    records = []
    for name, paths in targets.items():
        for p in paths:
            if p.is_symlink():
                raise ValueError(f'refuse staged source symlink: {p}')
    for name, paths in targets.items():
        for p in paths:
            p.write_bytes(contents[name])
            records.append({'file': str(p.relative_to(vehicle)), 'source': str((source / name).relative_to(tree)),
                            'sha256': hashlib.sha256(contents[name]).hexdigest()})
    return records


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('vehicle', type=Path); ap.add_argument('tree', type=Path)
    ns = ap.parse_args()
    records = refresh(ns.vehicle, ns.tree)
    sha = subprocess.check_output(['git', '-C', str(ns.tree), 'rev-parse', 'HEAD'], text=True).strip()
    (ns.vehicle / 'native_boot_sources.json').write_text(json.dumps({'source_commit': sha, 'files': records}, indent=2) + '\n')
    print(f'NATIVE_BOOT_SOURCES {len(records)} staged files from {sha}')

if __name__ == '__main__': main()
