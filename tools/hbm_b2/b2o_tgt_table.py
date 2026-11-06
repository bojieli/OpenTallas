#!/usr/bin/env python3
"""HBM-21 (SS39-TOK) item (2): programme-target table of a B2o bound top.

Every programme leaf in a B2o partition takes its 8-bit identity strap from a partition parameter S_<leaf>_tgt
(e.g. hbm_arch_q_hub__q_hub_ne: parameter [7:0] S_u_calendar_Q_q0_tgt = 8'b01100001; leaf .tgt(S_u_calendar_Q_q0_tgt)).
The top instance may override it (#(.S_u_calendar_Q_q0_tgt(8'b...))).  This tool reads one elaborated-source file
(the vehicle's single sel.sv, or any file holding the top and every partition module), applies top overrides to the
module defaults and writes, per top instance and leaf, the effective target id.

  b2o_tgt_table.py <src.sv> <top_module> <out.json>

Output (opentallas.hbm.b2o_tgt_table.v1): rows [{instance, module, leaf, tgt, tgt_hex, overridden}], plus
'shared': target ids written to more than one leaf (one cfg write programmes all of them, e.g. the q0 S-role copies
that take the same id as their q1 N-role twin), and 'calendar_roles': hub VM calendars with role S (u_calendar_Q_q0,
drives vmb_Q<k>_mu1) or N (u_calendar_Q_q1, drives vmb_Q<k>).
"""
import collections
import json
import re
import sys
from pathlib import Path

PARAM = re.compile(r"parameter\s*\[7:0\]\s*(S_\w+_tgt)\s*=\s*8'b([01]{8})")
OVR = re.compile(r"\.(S_\w+_tgt)\(8'b([01]{8})\)")
ROLE = {'u_calendar_Q_q0': 'S', 'u_calendar_Q_q1': 'N'}


def modules(text):
    out = {}
    for m in re.finditer(r'^module\s+(\w+)', text, re.M):
        end = text.find('\nendmodule', m.end())
        out[m.group(1)] = (m.start(), end if end >= 0 else len(text))
    return out


def defaults(text, span):
    a, b = span
    # the strap parameters live in the module header #( ... ) ( ports ); scan up to the first ');'
    hdr_end = text.find(');', a)
    return {n: int(v, 2) for n, v in PARAM.findall(text[a:hdr_end if 0 <= hdr_end < b else b])}


def instances(text, span, mods):
    a, b = span
    body = text[a:b]
    for m in re.finditer(r'^\s*(\w+)\s*#\((.*?)\)\s*(\w+)\s*\(', body, re.M | re.S):
        if m.group(1) in mods:
            yield m.group(1), m.group(3), dict((n, int(v, 2)) for n, v in OVR.findall(m.group(2)))
    for m in re.finditer(r'^\s*(\w+)\s+(\w+)\s*\(', body, re.M):
        if m.group(1) in mods:
            yield m.group(1), m.group(2), {}


def build(text, top):
    mods = modules(text)
    if top not in mods:
        raise ValueError(f'top {top} not found')
    rows = []
    for mod, inst, ovr in instances(text, mods[top], mods):
        d = defaults(text, mods[mod])
        unknown = set(ovr) - set(d)
        if unknown:
            raise ValueError(f'{inst}: override of undeclared {sorted(unknown)}')
        for p, v in sorted(d.items()):
            leaf = p[2:-4]
            v2 = ovr.get(p, v)
            rows.append(dict(instance=inst, module=mod, leaf=leaf, tgt=v2, tgt_hex=f'{v2:02x}', overridden=p in ovr))
    by = collections.defaultdict(list)
    for r in rows:
        by[r['tgt']].append(f"{r['instance']}.{r['leaf']}")
    shared = {f'{t:02x}': sorted(v) for t, v in sorted(by.items()) if len(v) > 1}
    cal = [dict(instance=r['instance'], leaf=r['leaf'], tgt_hex=r['tgt_hex'], role=ROLE[r['leaf']])
           for r in rows if r['leaf'] in ROLE]
    return dict(schema='opentallas.hbm.b2o_tgt_table.v1', top=top, rows=rows, shared=shared, calendar_roles=cal,
                counts=dict(instances=len({r['instance'] for r in rows}), leaves=len(rows), shared_ids=len(shared)))


def main(argv):
    if len(argv) != 4:
        print(__doc__); return 2
    res = build(Path(argv[1]).read_text(errors='replace'), argv[2])
    Path(argv[3]).write_text(json.dumps(res, indent=1) + '\n')
    print(f"B2O_TGT_TABLE instances {res['counts']['instances']} leaves {res['counts']['leaves']} "
          f"shared_ids {res['counts']['shared_ids']} calendars {len(res['calendar_roles'])}")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
