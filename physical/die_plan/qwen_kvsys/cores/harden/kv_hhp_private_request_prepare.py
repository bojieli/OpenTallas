#!/usr/bin/env python3
"""Prepare complete private source DATA bundle only; no GEN/CAD or default activation."""
import argparse
import json
from pathlib import Path
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[5] / 'tools/die_plan'))
import hhp_clock_mesh_role as M


def prepare(capsule, inputs, source_prep, master_receipt, part, out, *, base_native_join=None, enable=False):
    if not enable:
        return {'status': 'DISABLED', 'enabled_by_default': False}
    capsule, inputs, source_prep, master_receipt, out = map(Path, (capsule, inputs, source_prep, master_receipt, out))
    M.require(not out.exists(), 'request bundle must be fresh')
    cert = M.proposal(capsule, inputs, source_prep, part, enable=True, master_receipt_path=master_receipt)
    out.mkdir(parents=True)
    shutil.copytree(capsule, out / 'capsule_r4')
    (out / 'inputs').mkdir()
    for name in M.PINS:
        shutil.copy2(inputs / name, out / 'inputs' / name)
    shutil.copy2(source_prep, out / 'source_prep.json')
    shutil.copy2(master_receipt, out / 'master_receipt.json')
    (out / 'certificate.json').write_text(json.dumps(cert, indent=2) + '\n')
    request = dict(schema=M.REQUEST_SCHEMA, enabled=True, TYPE=M.TYPE, cohort=M.COHORT, part=part,
                   capsule='.private_hhp_clock_mesh/capsule_r4', inputs='.private_hhp_clock_mesh/inputs',
                   source_prep='.private_hhp_clock_mesh/source_prep.json',
                   master_receipt='.private_hhp_clock_mesh/master_receipt.json',
                   certificate='.private_hhp_clock_mesh/certificate.json')
    if base_native_join is not None:
        base_native_join = Path(base_native_join)
        M.require(M.digest(base_native_join.read_bytes()) == M.NATIVE_BASE_RECEIPT_SHA, 'wrong actual BASE native join receipt')
        shutil.copy2(base_native_join, out / 'base_native_join.json')
        request['base_native_join'] = '.private_hhp_clock_mesh/base_native_join.json'
    (out / 'request.json').write_text(json.dumps(request, indent=2) + '\n')
    return {'status': 'PRIVATE_REQUEST_BUNDLE_PREP_NOT_USED', 'qualified': False, 'enabled_by_default': False,
            'part': part, 'GEN': False, 'CAD': False, 'files': len(list(out.rglob('*')))}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('capsule', 'inputs', 'source-prep', 'master-receipt', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--base-native-join', type=Path, help='actual selected PC0355 join/model receipt; required by normal private GEN')
    p.add_argument('--part', choices=('pc_EN_0', 'pc_WN_0'), required=True)
    p.add_argument('--enable', action='store_true')
    a = p.parse_args()
    print(json.dumps(prepare(a.capsule, a.inputs, a.source_prep, a.master_receipt, a.part, a.out, base_native_join=a.base_native_join, enable=a.enable)))
if __name__ == '__main__': main()
