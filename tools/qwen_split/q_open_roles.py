#!/usr/bin/env python3
"""QKO-QDIE 10-21: structural-role contract for open OUTPUT ports of a Qwen compute die (the compute-die counterpart of
tools/qwen_kv_die/kv_open_tail_roles.py / kv_relay_zero_tail.py landing_tie_contract).

The strict bind (tools/die_port_bind.py) fails every undeclared open output.  A declared spare output (DIE_V.pads.json,
per INSTANCE, with a reason) is accepted only for a role-unused face of a hardened-once master.  This tool declares ONLY
outputs whose role is proven unused by the die netlist itself, by three rules; every other open output stays open and
keeps failing the strict bind (fault / status / functional consumers are owed, never declared here):

  TIE    tie_hi / tie_lo of a master whose RTL drives that port from a literal TIEHI/TIELO constant (a strap source cell):
         spare on an instance that has no strap bit of that polarity to drive.
  END    a chain face output <x>_eo / <x>_wo (or <x>o) whose mirrored input <x>_ei / <x>_wi (<x>i) on the SAME instance is
         a literal constant in the die netlist: the instance is the chain end on that face (dv_case chain-end idle-input
         rule c), so no neighbour exists to read the output.
  FAR    qfd_c_b16_dv bco0..3 / rs_o on an instance whose `far` strap is 1 (far-band cluster: no cluster beyond it;
         Q-CLUSTER header 'far clusters tie rs_i to tie_lo and leave rs_o open', straps_dv2f18mu.json far / rs_i reasons).
  REP2   q1 of qfd_rst_rep / qfd_rst_rep_p8 whose q0 is connected: the repeater drives one output group (reset tree
         builder emits q1 only for a second group).

usage: q_open_roles.py DIE_V --port-bind PORT_BIND_JSON --src SRC_ROOT --out PADS_JSON [--existing PADS_JSON]
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import die_port_bind as DPB  # noqa: E402

SCHEMA = 'opentallas.q_open_roles.v1'


def _bits(cm, port, nets):
    e = cm.get(port)
    return None if e is None else DPB.expr_bits(e, nets)


def const_conn(cm, port, nets):
    b = _bits(cm, port, nets)
    return bool(b) and all(x[0] == 'CONST' for x in b)


def const_val(cm, port, nets):
    b = _bits(cm, port, nets)
    if not b or not all(x[0] == 'CONST' for x in b):
        return None
    v = 0
    for x in b:
        v = (v << 1) | int(x[1])
    return v


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('die_v')
    ap.add_argument('--port-bind', required=True)
    ap.add_argument('--src', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--existing')
    a = ap.parse_args(argv)
    pb = json.load(open(a.port_bind))
    src = Path(a.src)
    mods = {}
    for mst, rec in pb.get('masters', {}).items():
        rtl = rec.get('rtl') if isinstance(rec, dict) else None
        if not rtl or not rec.get('output_open'):
            continue
        p = Path(rtl) if Path(rtl).is_absolute() else src / rtl
        for m in DPB.parse_modules(p.read_text(errors='replace'), str(p)):
            if m.name == mst:
                mods[mst] = m
    nets, tin, tout, insts = DPB.parse_die(a.die_v)
    doc = json.load(open(a.existing)) if a.existing else {}
    out_inst = dict(doc.get('instances', {}))
    rules, left = Counter(), Counter()
    detail = defaultdict(list)
    for mst, inst, params, cm in insts:
        if mst not in mods:
            continue
        mod = mods[mst]
        env = mod.env(params)
        for pn, (d, rng) in mod.ports.items():
            if d != 'output' or pn in cm:
                continue
            w = mod.width(pn, env) or 1
            rule = None
            if pn in ('tie_hi', 'tie_lo') and re.search(r"1'b[01]", mod.body):
                rule = 'TIE'
            elif mst == 'qfd_c_b16_dv' and (pn.startswith('bco') or pn == 'rs_o') and const_val(cm, 'far', nets) == 1:
                rule = 'FAR'
            elif mst in ('qfd_rst_rep', 'qfd_rst_rep_p8') and pn == 'q1' and 'q0' in cm:
                rule = 'REP2'
            else:
                mi = re.sub(r'o$', 'i', pn)
                if mi != pn and mi in mod.ports and mod.ports[mi][0] == 'input' and const_conn(cm, mi, nets):
                    rule = 'END'
            if rule is None:
                left[(mst, pn)] += 1
                continue
            rules[rule] += 1
            e = out_inst.setdefault(inst, dict(master=mst, reason='', ports={}))
            if e.get('master') != mst:
                raise SystemExit(f'{inst}: existing pad master {e.get("master")} != {mst}')
            e['ports'][pn] = [[0, w - 1]]
            detail[rule].append(f'{inst}.{pn}')
    why = dict(TIE='literal strap tie cell output with no strap bit of that polarity on this instance',
               END='chain-end face: the mirrored input on this instance is a die literal (no neighbour on that face)',
               FAR='far-band cluster (far=1): no cluster beyond it reads bco / rs_o',
               REP2='reset repeater drives one output group (q0); q1 is the unused second group output')
    for inst, e in out_inst.items():
        rs = sorted({r for r, lst in detail.items() for x in lst if x.split('.')[0] == inst})
        if rs:
            e['reason'] = (e.get('reason', '') + ' ' if e.get('reason') else '') + 'QKO-QDIE q_open_roles: ' + \
                '; '.join(f'{r}: {why[r]}' for r in rs)
    doc['instances'] = out_inst
    doc.setdefault('q_open_roles', {}).update(schema=SCHEMA, die_v=str(Path(a.die_v).resolve()), rules=dict(rules),
                                               still_open=sorted(f'{m}.{p} x{n}' for (m, p), n in left.items()))
    Path(a.out).write_text(json.dumps(doc, indent=1, sort_keys=True))
    print('Q_OPEN_ROLES declared', dict(rules), 'still open', len(left), 'master.port:',
          sorted(f'{m}.{p}' for m, p in left)[:60])


if __name__ == '__main__':
    main()
