#!/usr/bin/env python3
"""KV-P7: compare the boot compile's PV schedule on a bind (prep/die_ages_bound_padded.json + vport_dq_pads.json) with the
PV entry-pad table's predicted params (RL, FIRST_INPUT_AGE = cfg_fia, per-vport RT / DQ / W request pad).
    pv_check.py BOOT_OUT_DIR pv_entry.json   -> PASS/FAIL lines, exit 1 on any mismatch"""
import json, sys
from pathlib import Path
S = Path(sys.argv[1]); T = json.load(open(sys.argv[2]))['params']
ages = json.loads((S / 'prep/die_ages_bound_padded.json').read_text())
dq = json.loads((S / 'prep/vport_dq_pads.json').read_text())
bad = 0
def chk(name, got, want):
    global bad
    ok = got == want; bad += not ok
    print(f"{'OK ' if ok else 'BAD'} {name}: boot {got} table {want}")
chk('PV RL', ages['pv']['RL'], T['RL'])
chk('PV FIRST_INPUT_AGE (cfg_fia)', ages['pv']['FIRST_INPUT_AGE'], T['cfg_fia'])
for v, b in sorted(T['boot'].items()):
    a = ages['vport'].get(v, {})
    chk(f'{v} RT', a.get('RT'), b['RT'])
    chk(f'{v} DQ', a.get('DQ'), b['DQ'])
    chk(f'{v} extra W pad needed by boot (bind must already carry it)', dq['pad_stages'].get(v), 0)
print('PV_CHECK', 'PASS' if bad == 0 else f'FAIL {bad}')
sys.exit(1 if bad else 0)
