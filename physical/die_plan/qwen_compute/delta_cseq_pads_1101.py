#!/usr/bin/env python3
"""QC MU pair sequencer and driven forwarded-control pads: deterministic one-block plan delta."""
import json
import sys
from pathlib import Path
p = Path(sys.argv[1])
x = json.loads(p.read_text())
t = x['partition_types']['glue']
old = {"u_sys_face.u_ot_pr_core.u_cseq.u_tx_rom", "u_sys_face.u_ot_pr_core.u_cseq.u_rx_rom"}
t['hard_cores'] = [h for h in t['hard_cores'] if h['inst'] not in old]
found = []
for c in t['contents']:
    if c['inst'] in ('u_bump_fwd_epoch', 'u_bump_fwd_lrst'):
        c['module'] = 'qfd_sigbump'
        c['bump_ports'] = [dict(pin='pad_i', dir='input', width=1,
            note='Forwarded QC/KV control signal from the package; driven die input, zero added cycles')]
        found.append(c['inst'])
assert len(found) == 2, found
p.write_text(json.dumps(x) + '\n')
