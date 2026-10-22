#!/usr/bin/env python3
"""S81-LINK5B G7: S81-RTLGAP/eng die binding onto the 72-frame bind table (eng_overlay_g7.json), applied AFTER
apply_mu72_overlay.py: adds the dsdv_eng_rr / dsdv_eng_tap / dsdv_eng_tap_w master rows, the s_7N ks.o copy port
(second f_ks sink), status-fault masters and RTL widths.  Usage: apply_eng_overlay_g7.py BIND_TABLE"""
import copy, json, sys
from pathlib import Path
p = Path(sys.argv[1]); t = json.loads(p.read_text())
o = json.loads(Path(__file__).with_name('eng_overlay_g7.json').read_text())
for m, e in o['masters'].items():
    assert m not in t['masters'], m
    t['masters'][m] = copy.deepcopy(e)
for m, pa in o['ports_add'].items():
    row = t['masters'][m]
    for k, v in pa.items():
        assert k not in row['ports'], (m, k)
        row['ports'][k] = v
sf = t.setdefault('status_fault_masters', [])
sf += [m for m in o['status_fault_masters'] if m not in sf]
t.setdefault('rtl_widths', {}).update(o['rtl_widths'])
p.write_text(json.dumps(t, indent=1) + '\n')
print('ENG_OVERLAY_G7', ', '.join(o['masters']), '+ ports', {m: list(v) for m, v in o['ports_add'].items()})
