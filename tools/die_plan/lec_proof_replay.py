#!/usr/bin/env python3
"""Recheck a frozen LEC AIG pair with untrusted correspondence proposals.

Every proposal is proved in the complete simultaneous induction miter, then
again with every design compare point. No proposal is accepted as a waiver.
Unnamed AIG latches become side-specific FF keys with their actual next-state
expressions; X/anyseq primary inputs retain lec.py's existing semantics.

WORK contains gold.aig/map, gate.aig/map, hyp.json (previous proposals), and
proposals.json (supplemental proposals). All inputs and tool files are hashed
in the typed receipt. This is a replay of frozen frontends, not a new frontend
or a replacement for physical signoff. Originals are never overwritten.
"""
import argparse
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def replay(work, out, tool, negative=False):
    work, out, tool = Path(work).resolve(), Path(out).resolve(), Path(tool).resolve()
    out.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location('lec_replay_engine', tool)
    t = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = t
    spec.loader.exec_module(t)
    files = ('gold.aig', 'gold.map', 'gate.aig', 'gate.map', 'hyp.json', 'proposals.json')
    rec = dict(schema='opentallas.lec.replay.v1', verdict='UNPROVEN',
               negative_control=negative, inputs={f: digest(work/f) for f in files},
               engine_sha256=digest(tool), driver_sha256=digest(__file__))
    log = []
    try:
        L = t.Lec(t.read_aig(work/'gold.aig'), t.read_map(work/'gold.map'),
                  t.read_aig(work/'gate.aig'), t.read_map(work/'gate.map'))
        for f in ('hyp.json', 'proposals.json'):
            for side, k, h in json.loads((work/f).read_text()):
                assert side in ('gold', 'gate', 'both') and k.startswith('ff:')
                keys = L.gp if side in ('gold', 'both') else L.tp
                assert k in keys, (side, k)
                if side == 'both':
                    assert k in L.tp
                assert h[0] in ('eq', 'const')
                if h[0] == 'eq':
                    assert h[1] in ('gold', 'gate') and h[3] in (0, 1)
                    assert h[2].startswith('ff:') and h[2] in (L.gp if h[1]=='gold' else L.tp)
                else:
                    assert h[1] in (0, 1)
                L.hyp[(side, k)] = tuple(h)
        anonymous = []
        for side, original in (('gold', list(L.ganon)), ('gate', list(L.tanon))):
            points, compare, only = (L.gp, L.gc, L.gonly) if side=='gold' else (L.tp, L.tc, L.tonly)
            for lit, nxt in original:
                k = f'ff:__{side}_anonymous_{lit//2}'
                assert k not in points
                points[k], compare[k] = lit, nxt
                only.append(k)
                anonymous.append((side, k))
        L.ganon, L.tanon = [], []
        m, _ = L.build(with_compare=False, with_hyp=False)
        val, mask = m.simulate(32, seed=20261025)
        sv = lambda sd,k: t.lit_val(val, mask, L.dlit[(sd,k)])
        proposals = []
        for side, k in anonymous:
            hits = []
            for sd, keys in (('gold', L.gp), ('gate', L.tp)):
                for c in keys:
                    if (sd,c)==(side,k) or not c.startswith('ff:') or (sd,c) in L.hyp:
                        continue
                    if sv(side,k) in (sv(sd,c), sv(sd,c)^mask):
                        hits.append((sd,c,int(sv(side,k)!=sv(sd,c))))
            # A matched key is one shared state variable, regardless of side.
            hits = list({(c,inv):(sd,c,inv) for sd,c,inv in reversed(hits)}.values())
            if len(hits)==1:
                sd,c,inv = hits[0]
                L.hyp[(side,k)] = ('eq',sd,c,inv)
                proposals.append([side,k,list(L.hyp[(side,k)])])
        rec['anonymous_latches'] = len(anonymous)
        rec['anonymous_proposals'] = proposals
        if negative:
            assert anonymous, 'negative control requires an actual anonymous latch'
            side,k = anonymous[0]
            (L.gc if side=='gold' else L.tc)[k] ^= 1
        m,_ = L.build(with_compare=False, with_hyp=True)
        st = t.prove(m,out,1000,log,tag='induction')
        rec['induction'] = dict(collections.Counter(st.values()))
        (out/'induction.json').write_text(json.dumps(st))
        if not all(s=='proved' for s in st.values()):
            rec['reason'] = 'correspondence induction failed; no assumptions accepted'
        else:
            (out/'proved_hyp.json').write_text(json.dumps([[sd,k,list(h)] for (sd,k),h in L.hyp.items()]))
            m,_ = L.build(with_compare=True, with_hyp=True)
            st = t.prove(m,out,1000,log,tag='compare')
            rec['compare'] = dict(collections.Counter(st.values()))
            (out/'compare.json').write_text(json.dumps(st))
            if st and all(s=='proved' for s in st.values()):
                rec['verdict'] = 'EQUIVALENT'
            else:
                rec['reason'] = 'design compare points remain unproved'
    finally:
        (out/'replay.log').write_text('\n'.join(log))
        (out/'replay.json').write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps(rec))
    return 0 if rec['verdict']=='EQUIVALENT' else 1


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',required=True)
    p.add_argument('--out',required=True)
    p.add_argument('--lec-tool',required=True)
    p.add_argument('--negative-control',action='store_true')
    a=p.parse_args()
    raise SystemExit(replay(a.work,a.out,a.lec_tool,a.negative_control))
