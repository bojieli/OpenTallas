#!/usr/bin/env python3
"""Make declared bad P6 descriptors, or validate their actual DUT fault logs.

Run each case using the same compiled positive P6 binary with +DIR=OUT/NAME.
A numerical mismatch is insufficient: the real adapter must report a fault
before it retires the invalid record. The normal input/answer images are kept.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

# Record layout: hdr128, A256, B256, C256, O256, nA/nB/nO21.
CHANGES = {'gain_rows': (384 + 68, 20, 2), 'pre_width': (640 + 48, 20, 3),
           'a_extent': (128 + 8, 40, 200000), 'o_extent': (896 + 8, 40, 240000),
           'c_extent': (640 + 8, 40, 262104)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--template', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    lines = (a.template / 'fu_case.mem').read_text().splitlines()
    cases = [[int(x[i:i + 8], 16) for i in range(0, 72, 8)] for x in lines]
    target = max((i for i, c in enumerate(cases) if c[0] == 0), key=lambda i: cases[i][6])
    assert cases[target][2] == 1 and cases[target][6] == 6 * 5120, 'not a single full P6 record'
    recs = (a.template / 'fu_rec.mem').read_text().splitlines()
    ri = cases[target][1]
    original = int(recs[ri], 16)
    assert (original >> 452) & ((1 << 20) - 1) == 1, 'template gain is not broadcast'
    receipt = {}
    for name, (low, width, value) in CHANGES.items():
        out = a.out / name
        if not a.check:
            out.mkdir(parents=True, exist_ok=True)
            for f in a.template.iterdir():
                if f.is_file():
                    shutil.copyfile(f, out / f.name)
            mutated = list(recs)
            mask = ((1 << width) - 1) << low
            mutated[ri] = f'{(original & ~mask) | value << low:0304X}'
            (out / 'fu_rec.mem').write_text('\n'.join(mutated) + '\n')
        info = dict(case=target, record=ri, changed_field_bits=[low, low + width - 1], invalid_value=value,
                    programme_sha256=hashlib.sha256((out / 'fu_rec.mem').read_bytes()).hexdigest())
        if a.check:
            text = (out / 'run.log').read_text()
            assert not re.search(r'file not found|unable to open|cannot open|FATAL|%Error', text, re.I), name + ': invalid run input'
            assert re.search(rf'^ERR case {target}: retired 0 of 1, faults 1$', text, re.M), name + ': missing actual adapter fault'
            assert len(re.findall(r'^HGI_FUSED_UNIT FAIL errors=\d+$', text, re.M)) == 1, name + ': missing deliberate failure'
            assert 'HGI_FUSED_UNIT PASS' not in text, name + ': unsupported descriptor accepted'
            assert 'summary: 3 FUSED data cases through the D1 unit, 56320 VM words exact' in text, name + ': incomplete run'
            info['log_sha256'] = hashlib.sha256(text.encode()).hexdigest()
            info['actual_adapter_fault'] = True
        receipt[name] = info
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / ('fault_receipt.json' if a.check else 'stimulus_manifest.json')).write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
