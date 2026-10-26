#!/usr/bin/env python3
"""Verify reusable source-exact component evidence for physical-only HC boundary repairs.

This does not run simulation or establish mapped/native hardware completeness. It
fails on any bench-source SHA drift and any changed inherited leaf/core body.
"""
import hashlib
import json
import subprocess
from pathlib import Path
import hc_gate as gate

ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / 'results/rtl/s81_layer_tput_1013/norm_tree_1014/native_closure_1014/inherited_boundary/source_reuse.json'

def main():
    record = json.loads(RECORD.read_text())
    checked = 0
    for row in record['exact_receipts']:
        receipt = ROOT / row['path']
        assert hashlib.sha256(receipt.read_bytes()).hexdigest() == row['sha256'], receipt
        run = json.loads(receipt.read_text())
        assert run['status'] == 'pass' and run['pipe'] == 1 and run['ng'] == 256
        for name, expected in run['source_sha256'].items():
            source = ROOT / name
            assert hashlib.sha256(source.read_bytes()).hexdigest() == expected, name
            checked += 1
    for row in record['mutants']:
        old_record = json.loads((ROOT / row['record']).read_text())
        tile = old_record['tiles'][row['cell']]
        path = tile['module_file']
        before = subprocess.check_output(['git', '-C', str(ROOT), 'show', old_record['bench_source'] + ':' + path], text=True)
        current = (ROOT / path).read_text()
        modules = [row['cell']] + (['ot_s81_hc_ctnl', 'ot_s81_hc_ctq'] if 'ctnl' in row['cell'] else [])
        for module in modules:
            a,b = gate.tile_block(before,module)
            c,d = gate.tile_block(current,module)
            assert before[a:b] == current[c:d], module
        assert tile['mutant']['killed']
        assert any(r['err_rows'] > 0 and r['rows'] > 0 for r in tile['mutant']['result']['runs'])
    print(f'SOURCE_REUSE_OK source_hashes={checked} exact_receipts=2 observed_leaf_mutants=3 added_edges=0')
    print('Scope: reusable component numerical evidence; mapped physical/native gates remain independent.')

if __name__ == '__main__':
    main()
