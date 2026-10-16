#!/usr/bin/env python3
"""S81 die control-plane gate (s81-ctl-1011, ADAPTER_CONTRACT_1011): FAIL on any unbound engine command / done.

Called by the generator (tools/dsrom_s81_fulldie.py --ctrl-adapters) on the finished die model m, or stand-alone on a
recipe.  It checks, for the die's role:

  1. exactly one stage-sequencer instance (a master listed in physical/s81_ctrl/die_ctrl_bindings.json "sequencers");
  2. for every engine the role's stage programs use (results/rtl/s81_ctrl_20261008/programs: the union of the ports
     of the role's stage groups), a die bus from the sequencer's c<e> to a slab endpoint's c_cmd, from that slab's
     c_done to the sequencer's d<e> and from its c_st to the sequencer's s<e> -- all bits, whole ports or slices that
     cover them exactly once -- and the slab's master is one the bindings file allows for that engine;
  3. every engine the role does NOT use is declared role-absent in the bindings file, and no program op is routed to
     it (a declared-absent engine with a program op is a FAIL, not a waiver);
  4. die_port_audit (tools/s81/die_port_audit.py, when present): no unbound / placeholder / width finding on any
     master (a master with no RTL is a FAIL here: the gate is strict).
Nothing is tied off or waived by this tool; it only reports.

    python3 tools/s81_ctrl/die_ctrl_gate.py --recipe layer1kit [--role layer] [--out gate.json]
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BIND = ROOT / 'physical/s81_ctrl/die_ctrl_bindings.json'
PROGS = ROOT / 'results/rtl/s81_ctrl_20261008/programs/index.json'
ENG = dict(fld=0, su=1, hc=2, coll=3, svc=4, sel=5, col=6, hop=7, head=8, emb=9, eng=10, spare=11)
_PSL = re.compile(r'^(.+)\[(\d+):(\d+)\]$')


def _slice(port, bits):
    m = _PSL.match(port)
    return (m.group(1), int(m.group(2)), int(m.group(3))) if m else (port, 0, bits - 1)


def role_engines(role, kinds=None):
    """engines used by the role's stage programs: layer = 'stage' groups, source = 'embed', head = 'head'"""
    kinds = kinds or dict(layer=('stage',), source=('embed',), head=('head',))[role]
    idx = json.loads(PROGS.read_text())
    used = set()
    for s in idx['stages']:
        if s['kind'] in kinds:
            used |= set(s['ports'])
    return used


def _bits_of(m, inst, port):
    """{bit index: [bus id]} driven / received on inst.port by the die buses"""
    got = defaultdict(list)
    for bid, cls, bits, eps in m['buses']:
        for i_, p_ in eps:
            if i_ != inst:
                continue
            base, lo, hi = _slice(p_, bits)
            if base == port:
                for b in range(lo, hi + 1):
                    got[b].append(bid)
    return got


def _peer(m, inst, port, nbits):
    """the (instance, port base) set on the other end of every bus touching inst.port"""
    peers = set()
    for bid, cls, bits, eps in m['buses']:
        if any(i_ == inst and _slice(p_, bits)[0] == port for i_, p_ in eps):
            for i_, p_ in eps:
                if i_ != inst:
                    peers.add((i_, _slice(p_, bits)[0]))
    return peers


def gate(m, role, bindings=None, used=None):
    bindings = bindings or json.loads(BIND.read_text())
    used = role_engines(role) if used is None else used
    by = {it.name: it for it in m['insts']}
    out = dict(role=role, used=sorted(used), findings=[], engines={})
    seqs = [it for it in m['insts'] if it.master in bindings['sequencers']]
    if len(seqs) != 1:
        out['findings'].append('sequencer instances %d (need exactly 1 of %s)' % (len(seqs), bindings['sequencers']))
        return out
    sq = seqs[0].name
    absent = set(bindings['role_absent'].get(role, []))
    for e, k in ENG.items():
        rec = dict(port=k)
        out['engines'][e] = rec
        if e not in used:
            if e not in absent:
                out['findings'].append(f'{e}: not used by {role} programs but not declared role-absent')
            rec['state'] = 'ROLE_ABSENT'
            continue
        if e in absent:
            out['findings'].append(f'{e}: declared role-absent but the {role} programs route ops to it')
        allowed = set(bindings['engines'].get(e, {}).get('masters', []))
        if not allowed:
            out['findings'].append(f'{e}: no slab master qualified for the engine (bindings file) -> UNBOUND')
            rec['state'] = 'UNBOUND'
            continue
        ok = True
        for sp, sport, w in ((f'c{k}', 'c_cmd', 85), (f'd{k}', 'c_done', 9), (f's{k}', 'c_st', 2)):
            got = _bits_of(m, sq, sp)
            if sorted(got) != list(range(w)) or any(len(v) != 1 for v in got.values()):
                out['findings'].append(f'{e}: sequencer {sp} bits bound {len(got)}/{w} (each exactly once)')
                ok = False
            peers = _peer(m, sq, sp, w)
            bad = [p for p in peers if p[1] != sport or by.get(p[0]) is None or by[p[0]].master not in allowed]
            if bad or not peers:
                out['findings'].append(f'{e}: {sp} peers {sorted(peers)} (need {sport} of {sorted(allowed)})')
                ok = False
        rec['state'] = 'BOUND' if ok else 'UNBOUND'
    try:
        sys.path[:0] = [str(ROOT / 'tools/s81')]
        from die_port_audit import audit
    except ImportError:
        out['findings'].append('die_port_audit unavailable (tools/s81/die_port_audit.py): gate cannot pass without it')
    else:
        a = audit(m)
        out['port_audit'] = a
        for ms, f in sorted(a['findings'].items()):
            for k_, v in f.items():
                if v:
                    out['findings'].append(f'port_audit {ms}: {k_} {len(v)} e.g. {v[:3]}')
        for x in a['no_rtl']:
            out['findings'].append(f"port_audit {x['master']}: no RTL ({x['die_pins']} die pins are placeholders)")
    out['verdict'] = 'PASS' if not out['findings'] else 'FAIL'
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--recipe', required=True)
    ap.add_argument('--role', choices=['layer', 'source', 'head'], default='layer')
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/s81')]
    import s81_dies_recipe as RC
    import dsrom_s81_fulldie as F
    m = RC.build(RC.recipes()[a.recipe]['opts'])
    if 'pdir' not in m:
        F.finalize_r8(m)
    res = gate(m, a.role)
    res['recipe'] = a.recipe
    if a.out:
        a.out.write_text(json.dumps(res, indent=1, default=str) + '\n')
    print(f"DIE_CTRL_GATE {a.recipe} ({a.role}): " + ', '.join(f"{e}={r.get('state')}" for e, r in res['engines'].items()))
    for f in res['findings'][:60]:
        print('  ' + f)
    print(f"DIE_CTRL_GATE {res.get('verdict', 'FAIL')} ({len(res['findings'])} findings)")
    return 0 if res.get('verdict') == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
