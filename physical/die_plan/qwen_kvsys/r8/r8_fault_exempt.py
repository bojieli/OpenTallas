#!/usr/bin/env python3
"""KV-P5 10-23: R8 input prep for the KV die.  Sticky FAULT / health bits (source pin *fault / *flt, sinks afu / afv / afk /
fault_i / fi) carry no static-schedule term (plan_v32: health flags OR into sticky registers, like resets), so they are
taken out of the R8 landing classes (lane -> 'spine', which r8.py skips as async).  Without this the as-built per-quadrant
fault-vs-request offsets (kreq/afk 33 EN vs 44 WS) union unrelated buses into one class and force per-instance pads.

    r8_fault_exempt.py BIND_DIR/bus_groups.json OUT.json
    python3 tools/die_plan/r8.py pads die_plan.json OUT.json --out r8 --bus leaf --replica type   (PLAN-TOOL3 cc5ebe697)
"""
import json
import re
import sys

RX = re.compile(r'(?i)(^|_)(fault|flt)(_o|_q)?$')
SINKS = ('afu', 'afv', 'afk', 'fault_i', 'fi')
bg = json.load(open(sys.argv[1]))
n = 0
for g in bg['landing']:
    for m in g['members']:
        if RX.search(m['source'].rpartition('.')[2]) or m['sink_port'] in SINKS:
            m['lane'] = 'spine'
            n += 1
json.dump(bg, open(sys.argv[2], 'w'))
print(f'{n} fault/health members exempted')
