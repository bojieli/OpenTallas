#!/usr/bin/env python3
"""S81-RTLGAP/RG-L20 (10-21, MU.S81.L20.RTL): L20 split binding onto the 72-frame bind table, applied AFTER
tools/s81_dv/recovery_idx4_1021/apply_overlay.py (it edits the IDX4 masters in place):
  * bk_sel master dsfd_bk_selector_vm -> module dsdv_bk_sel_vmtx (dsdv_bk_sel_vm + tree transmitter dsdv_idx_tx_n32):
    + die port bk_sel_tl_o[275:0] (output: the rank-tree lane to the parent die = the parent's bk_sel_ca / bk_sel_cb)
    + die port bk_sel_tx_st[15:0] (output: TX status -> die status collector, like irg_*_st / iqf_st)
  * iqf uid: strap 8'h5B -> die port iqf_uid[7:0] (input: the die's rank-tree uid from the rank manifest; one die type
    serves every tree position, so the uid that picks the die's spec entry from the tree frame is a die input).
usage: apply_overlay.py <bind_table.json>"""
import json, sys
from pathlib import Path
p = Path(sys.argv[1]); t = json.loads(p.read_text())
o = json.loads(Path(__file__).with_name('overlay.json').read_text())
M = t['masters']
for name, ch in o['masters'].items():
    assert name in M, f'{name}: apply recovery_idx4_1021/apply_overlay.py first'
    m = M[name]
    for k in ch.get('drop_straps', []):
        m['straps'] = [s for s in m.get('straps', []) if s != k]
        m.get('strap_values', {}).pop(k, None)
    for k, v in ch.get('set', {}).items():
        m[k] = v
    tp = m.setdefault('top_ports', [])
    for x in ch.get('add_top_ports', []):
        if all(y['port'] != x['port'] for y in tp):
            tp.append(x)
t.setdefault('rtl_widths', {}).update(o['rtl_widths'])
p.write_text(json.dumps(t, indent=1) + '\n')
print('L20SPLIT_OVERLAY_OK', ', '.join(o['masters']))
