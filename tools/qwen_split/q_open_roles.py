#!/usr/bin/env python3
"""QKO-QDIE 10-21 (v1) / SQ-QBIND2 10-21 (v2): structural-role contract for open OUTPUT ports of a Qwen compute die (the
compute-die counterpart of tools/qwen_kv_die/kv_open_tail_roles.py / kv_relay_zero_tail.py landing_tie_contract).

The strict bind (tools/die_port_bind.py) fails every undeclared open output.  A declared spare output (DIE_V.pads.json,
per INSTANCE, with a reason) is accepted only for a role-unused face of a hardened-once master.  This tool declares ONLY
outputs whose role is proven unused by the die netlist itself; every other open output stays open and keeps failing the
strict bind (fault / status / functional consumers are owed, never declared here).  Each rule re-checks its proof on the
netlist and refuses (leaves the port open) when the proof does not hold.

v1 rules (QKO-QDIE f7d281b65):
  TIE    tie_hi / tie_lo of a master whose RTL drives that port from a literal TIEHI/TIELO constant (a strap source cell):
         spare on an instance that has no strap bit of that polarity to drive.
  END    a chain face output <x>_eo / <x>_wo (or <x>o) whose mirrored input <x>_ei / <x>_wi (<x>i) on the SAME instance is
         a literal constant in the die netlist: the instance is the chain end on that face.
  FAR    qfd_c_b16_dv bco0..3 / rs_o on an instance whose `far` strap is 1 (far-band cluster: no cluster beyond it).
  REP2   q1 of qfd_rst_rep / qfd_rst_rep_p8 whose q0 is connected: the repeater drives one output group.
v2 rules (SQ-QBIND2, r11bfp strict bind 79 -> classes left by v1):
  FACE   qfd_dv_slice2_e / _w: every output of face F (port suffix _<f>o) on an instance whose EVERY face-F input
         (_<f>i, the l9 pair word excluded) is a die literal: no neighbour exists on that face (E5 west face: cmd / hr /
         return chain / st / sc words toward a slice that is not there).
  HEADDN qfd_dv_slice2 chain head (the ONE slice instance whose cc / ss status face is connected = the slice abutting
         io_collective / tt_ctlm): its down-stream st / sc outputs on the head face.  The head's neighbour on that face
         is the edge (tt_ctlm.tl drives the head's st up-input; qfd_tt_ctlm_dv / io_collective have no stream or scalar
         input -- qfd_dv_slice2 header: chain-end words at W5 'before the edge endpoints answer').  Proof: the face
         inputs of that port pair are driven (through relays) by a non-slice master that has no input of that word.
  REPL   qfd_dv_slice2 cc_o (ccv/ccm/ccw/cct) and st (ss) status faces of every NON-head slice: cc_o is the identical XC
         decode of the broadcast slice command in every slice and the status is read only at the head (tt_ctlm.ss5;
         per-slice faults reach the head through the ag OR chain, the token through the scalar chain).  Proof: exactly
         one slice instance has the face connected and every other slice has all of its bits open.
  L9     l9_eo of a slice A whose l9_wi is driven (through relays) by slice B's l9_eo while B's own l9_wi is a die literal:
         the level-9 pair is one-way B -> A, so A's word would return to an input B ties off.
  TERM   ck_o of a forwarded station qfd_rlyr_* whose b is read ONLY by a landing station qfd_rlyrl_* (captures in the
         destination clock ck; a landing has no ckf input): the last forwarded hop has no forwarded-clock consumer.
  BUMP   rs of a qfd_ckbump (forwarded clock + reset bump model) when EXACTLY ONE other qfd_ckbump instance drives the
         die's forwarded reset (its rs connected): one reset entry per die; the second clock bump (core feed) carries
         its clock only.
  DOMAIN qfd_rstseq rso_s (spine domain release) when no die net carries a spine-domain reset (the DV die has no spine
         domain: SU / VM / slabs / constants live inside the slices on the field reset rso_f).

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

SCHEMA = 'opentallas.q_open_roles.v2'
SLICE = ('qfd_dv_slice2_e', 'qfd_dv_slice2_w')
RELAY = re.compile(r'^(qfd_rly[a-z0-9]*_|qfd_landh0?_)')
STATUS_FACE = re.compile(r'^(ccv|ccm|ccw|cct|ss)_[ew]o$')


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


def face_of(pn):
    m = re.match(r'^\w+_([ew])([io])$', pn)
    return (m.group(1), m.group(2)) if m else (None, None)


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
    insts = [x for x in insts if x[0] != '__assign__']
    by_inst = {inst: (mst, cm) for mst, inst, params, cm in insts}
    # net -> [(inst, port)] for every instance connection that names the net (driver and readers alike)
    users = defaultdict(list)
    for mst, inst, params, cm in insts:
        for pn, e in cm.items():
            b = DPB.expr_bits(e, nets) or []
            for n in {x[0] for x in b if x[0] not in ('CONST', 'Z')}:
                users[n].append((inst, pn))

    def nets_of(cm, port):
        return {x[0] for x in (_bits(cm, port, nets) or []) if x[0] not in ('CONST', 'Z')}

    def source(inst, port, depth=0):
        """(inst, port) driving `port` of `inst`, followed back through die relay / landing stations (a -> b)."""
        mst, cm = by_inst[inst]
        for n in nets_of(cm, port):
            for i2, p2 in users[n]:
                if i2 == inst:
                    continue
                m2, cm2 = by_inst[i2]
                if RELAY.match(m2) and p2 == 'b' and depth < 400:
                    return source(i2, 'a', depth + 1)
                if not RELAY.match(m2) and m2 in mods and mods[m2].ports.get(p2, ('',))[0] == 'output':
                    return (i2, p2)
                if not RELAY.match(m2) and m2 not in mods:
                    return (i2, p2)  # driver outside the open-output masters (port direction from the bind report)
        return None

    def readers(inst, port):
        mst, cm = by_inst[inst]
        return [(i2, p2) for n in nets_of(cm, port) for i2, p2 in users[n] if i2 != inst]

    # REPL / HEADDN proof: exactly one slice instance with its status face connected
    slices = [(mst, inst, cm) for mst, inst, params, cm in insts if mst in SLICE]
    heads = [inst for mst, inst, cm in slices if any(STATUS_FACE.match(p) for p in cm)]
    head = heads[0] if len(heads) == 1 else None

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
            elif mst == 'qfd_ckbump' and pn == 'rs':
                others = [i for m2, i, _, c2 in insts if m2 == 'qfd_ckbump' and i != inst and 'rs' in c2]
                if len(others) == 1 and 'pll_ck' in cm:
                    rule = 'BUMP'
            elif mst == 'qfd_rstseq' and pn == 'rso_s':
                if not any(re.match(r'^n_rst_(spine|s)(_|$)', n) for n in nets) and all(
                        p in cm for p in ('rso_io', 'rso_f', 'rso_ctlm', 'rso_seq')):
                    rule = 'DOMAIN'
            elif mst.startswith('qfd_rlyr_') and pn == 'ck_o':
                rd = readers(inst, 'b')
                if rd and all(by_inst[i][0].startswith('qfd_rlyrl_') and p == 'a' for i, p in rd):
                    rule = 'TERM'
            elif mst in SLICE:
                f, io = face_of(pn)
                if f and io == 'o':
                    fin = [p for p, (dd, _) in mod.ports.items()
                           if dd == 'input' and face_of(p) == (f, 'i') and not p.startswith('l9_')]
                    if fin and all(p in cm and const_conn(cm, p, nets) for p in fin):
                        rule = 'FACE'
                if rule is None and STATUS_FACE.match(pn) and head and inst != head:
                    if not any(STATUS_FACE.match(p) for p in cm):
                        rule = 'REPL'
                if rule is None and inst == head and re.match(r'^(st|sc)_[ew]o$', pn):
                    mi = pn[:-1] + 'i'
                    s = source(inst, mi) if mi in cm else None
                    if s is None and mi in cm and const_conn(cm, mi, nets):
                        rule = 'HEADDN'
                    elif s is not None:
                        sm = by_inst[s[0]][0]
                        word = pn.split('_')[0]
                        sm_mod = mods.get(sm)
                        has_in = sm_mod is not None and any(
                            dd == 'input' and (p == word or p.startswith(word + '_')) for p, (dd, _) in sm_mod.ports.items())
                        if sm not in SLICE and not has_in:
                            rule = 'HEADDN'
                if rule is None and pn == 'l9_eo' and 'l9_wi' in cm and not const_conn(cm, 'l9_wi', nets):
                    s = source(inst, 'l9_wi')
                    if s and by_inst[s[0]][0] in SLICE and s[1] == 'l9_eo':
                        bcm = by_inst[s[0]][1]
                        if const_conn(bcm, 'l9_wi', nets):
                            rule = 'L9'
            if rule is None:
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
               REP2='reset repeater drives one output group (q0); q1 is the unused second group output',
               FACE='slice chain end: every input of this face is a die literal (no slice beyond it on that face)',
               HEADDN='chain-head slice: the down-stream st/sc word leaves toward the edge source (tt_ctlm / '
                      'io_collective), which has no input of that word',
               REPL=f'non-head slice status/collective face (cc_o identical XC decode, status read only at head {head})',
               L9='level-9 pair is one-way: the partner slice that drives l9_wi ties its own l9_wi to a literal',
               BUMP='second forwarded-clock bump (core feed): the die reset enters at the one other ckbump rs',
               DOMAIN='no spine reset domain on this die (no spine-domain reset net); io/field/ctlm/seq roots connected',
               TERM='last forwarded station: b is read only by a landing station (destination clock), no ckf reader')
    for inst, e in out_inst.items():
        rs = sorted({r for r, lst in detail.items() for x in lst if x.split('.')[0] == inst})
        if rs:
            e['reason'] = (e.get('reason', '') + ' ' if e.get('reason') else '') + 'q_open_roles v2: ' + \
                '; '.join(f'{r}: {why[r]}' for r in rs)
    doc['instances'] = out_inst
    doc.setdefault('q_open_roles', {}).update(schema=SCHEMA, die_v=str(Path(a.die_v).resolve()), rules=dict(rules),
                                               head=head, heads_seen=heads,
                                               still_open=sorted(f'{m}.{p} x{n}' for (m, p), n in left.items()))
    Path(a.out).write_text(json.dumps(doc, indent=1, sort_keys=True))
    print('Q_OPEN_ROLES declared', dict(rules), 'head', head, 'still open', len(left), 'master.port:',
          sorted(f'{m}.{p}' for m, p in left)[:60])


if __name__ == '__main__':
    main()
