#!/usr/bin/env python3
"""Compute-die contract tables from one build (compute-die lead r2, 2026-10-14): the master list the die instantiates
(instances, outline, real view bound or assigned pin file) and the port-bind (no stubs) table.

    python3 tools/qwen_split/contract_tables.py OUT_DIR BIND_JSON PORT_BIND_JSON > tables.md
OUT_DIR = the build's out/ (pins/INDEX.json, pins/<master>.json, rom_tp8b.json); BIND_JSON = bind_real.py output
(may be '-'); PORT_BIND_JSON = die_port_bind.py output.
"""
import json, sys
from pathlib import Path

out, bind_p, pb_p = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
idx = json.loads((out / 'pins' / 'INDEX.json').read_text())
bind = json.loads(Path(bind_p).read_text()) if bind_p != '-' else {}
bound = {m for m, r in (bind.get('masters_detail') or {}).items() if r.get('bound')}
pb = json.loads(Path(pb_p).read_text())['masters']
print('| master | inst | outline um | view | pins | RTL (die name) | port-bind |')
print('|---|---|---|---|---|---|---|')
for m in sorted(set(idx) | set(pb)):
    if m.startswith(('qfd_rly', 'qfd_rlyp', 'qfd_rst_rep')):
        continue
    pf = out / 'pins' / f'{m}.json'
    rec = json.loads(pf.read_text()) if pf.exists() else {}
    ol = rec.get('outline') or {}
    r = pb.get(m, {})
    issues = []
    for k, lab in (('die_ports_not_in_rtl', 'die-only'), ('rtl_inputs_unconnected', 'in-open'),
                   ('rtl_outputs_unconnected', 'out-unread')):
        if r.get(k):
            issues.append(f"{lab}: {', '.join(r[k][:6])}{' ...' if len(r[k]) > 6 else ''}")
    if r.get('width_mismatch'):
        issues.append('width: ' + ', '.join(f"{w['port']} {w['die']}/{w['rtl']}" for w in r['width_mismatch'][:5]))
    rtl = r.get('rtl') or 'NONE (release blocker)'
    print(f"| {m} | {rec.get('instances', r.get('n_instances', ''))} | "
          f"{round(ol.get('w', 0), 2)} x {round(ol.get('h', 0), 2)} | {'REAL' if m in bound else 'assigned'} | "
          f"{'pins/' + m + '.json' if pf.exists() else '-'} | {rtl} | {'; '.join(issues) or 'CLEAN'} |")
