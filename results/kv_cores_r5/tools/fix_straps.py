#!/usr/bin/env python3
"""KV-CORES-R4: name the bind-form ID straps of a kv_core_rtl head core (from the b51 composite) as the plan pins.
b51 (OWNER 10-25 option B, bind straps) feeds frontq .hid and both lane8 .bsel from parent strap ports; on the flat
partition kv_core_rtl sees them as ADDED pins <g_front_n>_u_front__hid / <g_t_k>_u_l8__bsel while the plan pins file
carries strap_hid / strap_bsel (STALE).  Same end state as gen_core_kit_kv --head-strap-master: ports strap_hid[1:0] +
strap_bsel[1:0], class strap, report.straps id entries; the stale duplicates are removed.  usage: fix_straps.py CORE_DIR"""
import json, re, sys
from collections import Counter
from pathlib import Path
d = Path(sys.argv[1]); mod = d.name
sv, cjp = d / f'{mod}.sv', d / f'{mod}_core.json'
text, cj = sv.read_text(), json.load(open(cjp))
hid = [k for k in cj['port_decl'] if re.fullmatch(r'g_front_\d+_u_front__hid', k)]
bsel = [k for k in cj['port_decl'] if re.fullmatch(r'g_t_\d+_u_l8__bsel', k)]
assert len(hid) == 1 and len(bsel) == 1, (hid, bsel)
hid, bsel = hid[0], bsel[0]
for s in ('strap_hid', 'strap_bsel'):
    n = len(re.findall(rf'\b{s}\b', text))
    assert n == 1, f'{s} referenced {n}x (expected the unused stale decl only)'
    text, k = re.subn(rf'\n\s*input wire \[1:0\] {s},', '', text); assert k == 1, s
for old, new in ((hid, 'strap_hid'), (bsel, 'strap_bsel')):
    text, k = re.subn(rf'\b{old}\b', new, text); assert k >= 2, (old, k)
sv.write_text(text)
for old, new in ((hid, 'strap_hid'), (bsel, 'strap_bsel')):
    cj['port_decl'].pop(new, None)
    cj['port_decl'][new] = cj['port_decl'].pop(old)
    for b in (0, 1):
        cj['pin_class'].pop(f'{old}[{b}]'); cj['pin_class'][f'{new}[{b}]'] = 'strap'
r = cj['report']
r['added'] = [a for a in r['added'] if a['pin'] not in (hid, bsel)]
r['stale'] = [s for s in r['stale'] if not s['pin'].startswith(('strap_hid[', 'strap_bsel['))]
r['straps'] = [dict(port="strap_hid", pin="strap_hid", width=2, value=None, was=hid, kind='id_strap'),
               dict(port="strap_bsel", pin="strap_bsel", width=2, value=None, was=bsel + ' (both ot_qkh_lane8)', kind='id_strap')]
r['kv_cores_r4_fix_straps'] = 'b51 bind-form straps -> plan strap_* pins (fix_straps.py); == --head-strap-master end state'
cj['classes'] = dict(Counter(cj['pin_class'].values()))
cjp.write_text(json.dumps(cj, indent=1) + '\n')
print(mod, cj['classes'], 'added', len(r['added']), 'stale', len(r['stale']))
