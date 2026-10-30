#!/usr/bin/env python3
"""Attach only exact physical contracts of available SIGNED S81 views."""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

SOURCES = {
    'dsfd_su_t_rxsf': ('rxsf_signed_1029', 'physical/die_plan/s81/cores/views/rxsf_signed_1029'),
    'dsfd_su_t_rxsb': ('dsfd_su_t_rxsb', 'physical/ref_tile/s81su_rxsb_ref/views/dsfd_su_t_rxsb'),
    'dsdv_svc_sx_hrow': ('dsdv_svc_sx_hrow', 'physical/die_plan/s81/cores/views/dsdv_svc_sx_hrow'),
}


def signature(rows):
    return {p.get('name', p.get('bus') if p.get('bit') is None else f"{p['bus']}[{p['bit']}]"):
            (p['layer'], p['x'], p['y']) for p in rows}


def attach(raw, root):
    repo = root.parents[2]
    out, counts = copy.deepcopy(raw), {}
    for mod, (snapshot, lib_dir) in SOURCES.items():
        view = root / 'cores/views' / snapshot
        receipt = json.loads((view / 'signoff.json').read_text())
        if receipt['verdict'] != 'SIGNED':
            raise ValueError(f'{mod}: unsigned view')
        policy = receipt['policy']
        if tuple(policy[k] for k in ('period_ps', 'uncertainty_setup_ps', 'uncertainty_hold_ps')) != (833, 60, 25):
            raise ValueError(f'{mod}: timing policy differs')
        actual = signature(json.loads((view / 'pins.json').read_text()))
        lib = repo / lib_dir / f'{mod}_tt.lib'
        ff = lib.with_name(f'{mod}_ff.lib')
        if not lib.is_file() or not ff.is_file():
            raise ValueError(f'{mod}: actual TT/FF libraries missing')
        manifest_path = view / 'MANIFEST.json'
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
            hashes = manifest.get('view_files', manifest.get('files', {}))
            for path in (lib, ff):
                if hashlib.sha256(path.read_bytes()).hexdigest() != hashes[path.name]:
                    raise ValueError(f'{mod}: published view hash mismatch: {path.name}')
        count = 0
        for tn, typ in out['partition_types'].items():
            for core in typ.get('hard_cores', []):
                if core['module'] != mod:
                    continue
                rows = json.loads((root / core['pins_file']).read_text())['pins']
                if signature(rows) != actual:
                    raise ValueError(f'{tn}: {mod} physical pins differ')
                lef = repo / core['lef']
                if lef.is_file():
                    size = re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)', lef.read_text())
                    if size and [float(x) for x in size.groups()] != core['outline_um']:
                        raise ValueError(f'{tn}: {mod} outline differs')
                core['lib'] = str(lib.relative_to(repo))
                count += 1
        counts[mod] = count
    # The attachment must not change any physical, RTL, clock or reset field.
    stripped = copy.deepcopy(out)
    for tn, typ in stripped['partition_types'].items():
        for i, core in enumerate(typ.get('hard_cores', [])):
            old = raw['partition_types'][tn]['hard_cores'][i]
            if core['module'] in SOURCES:
                if 'lib' in old:
                    core['lib'] = old['lib']
                else:
                    core.pop('lib', None)
    if stripped != raw:
        raise ValueError('attachment changed more than timing-library declarations')
    return out, counts


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan')
    p.add_argument('out')
    a = p.parse_args()
    result, counts = attach(json.loads(Path(a.plan).read_text()), Path(__file__).resolve().parent)
    Path(a.out).write_text(json.dumps(result, separators=(',', ':'))+'\n')
    print('SIGNED_VIEW_ATTACH PASS '+json.dumps(counts))
