#!/usr/bin/env python3
"""QDIE5-HP13 10-22: re-derive CLOCK_OWNERS.json (cf driver proof, consumed by tools/qwen_split/fault_emit.py) on the
regenerated cpub39 netlists: cf must be driven by exactly one DFF whose C is the ck_hr alias net.  usage: ROOT"""
import hashlib, json, re, sys
from pathlib import Path
R = Path(sys.argv[1]).resolve(); P = R / 'results/arch/hp13_corepub39_1021/CLOCK_OWNERS.json'
rows = json.loads(P.read_text())
for r in rows:
    raw = (R / r['rtl']).read_bytes(); t = raw.decode()
    net = re.search(r'^assign cf = (n_\d+);', t, re.M).group(1)
    ck = re.search(r'^assign (n_\d+) = ck_hr;', t, re.M).group(1)
    st = [l for l in t.splitlines() if re.search(r'qfd_bmath_dff_\w+ #\(\.ID\(0\)\) u_\d+\(.*\.Q\(' + net + r'\)', l)]
    assert len(st) == 1, st
    m = re.search(r'(u_\d+)\(\.C\((n_\d+)\)', st[0]); assert m.group(2) == ck
    r['rtl_sha256'] = hashlib.sha256(raw).hexdigest()
    r['cf'].update(net=net, driver=m.group(1), clock_net=ck, clock_port='ck_hr', driver_statement=st[0])
P.write_text(json.dumps(rows, indent=2) + '\n'); print([(r['master'], r['rtl_sha256'][:12], r['cf']['driver']) for r in rows])
