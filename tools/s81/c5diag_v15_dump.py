#!/usr/bin/env python3
"""S81 die v15 plan dump (no OpenROAD): build the die exactly as `dsrom_s81_fulldie.py real` does, write the LEFs,
run the hop gate on every class, the python legality screen and the generated pin-clash check, and dump the plan.

usage: c5diag_v15_dump.py <work dir> <generator args as for mode real, without --work>
writes <work>/{elements.lef,...,hop_gate_full.json,plan_check.json,plan.json.gz}
plan.json.gz: insts [name, master, x, y, w, h, orient, kind, region], hops [bus, cls, bits, drv, dport, load, lport,
[xa, ya, xb, yb] of the first and of the last bit, min um, max um] for every bus with pins on both ends."""
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools' / 's81'))
import dsrom_s81_fulldie as G   # noqa: E402
import die_hop_gate as HG       # noqa: E402


def main():
    work = Path(sys.argv[1]).resolve()
    work.mkdir(parents=True, exist_ok=True)
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('mode')
    ap.add_argument('--k', type=int, default=16)
    G.die_options(ap)
    a = ap.parse_args(sys.argv[2:])
    G.apply_options(a)
    m = G.build()
    G.finalize_r8(m)
    G.write_lefs(m, 1, work / 'elements.lef')
    G._init_real()
    texts = [(work / 'elements.lef').read_text()]
    for rel in (G.Q_LEF, G.CFG_LEF, G.PHY_LEF, G.SERDES_LEF, G.UCIE_LEF):
        texts.append(G._lef_text(rel))
    if m.get('bound_views'):
        bv = G.bound_views()
        texts.append('\n'.join(bv[n]['text'] for n in sorted(m['bound_views'])))
    lim = G.HOP_GATE_UM or 500.0
    hg = HG.gate(m['insts'], m['buses'], texts, G.pslice, limit_um=lim, ss_um=G.SS_REACH_UM, top=100000)
    (work / 'hop_gate_full.json').write_text(json.dumps(hg, indent=1) + '\n')
    leg = G.legality(m)
    pc = G.pin_clashes(m)
    chk = dict(legality=leg, generated_pin_clashes=len(pc), pin_clash_examples=pc[:20],
               hop_fix=m.get('hop_fix'), relay_progress_fix=m.get('relay_progress_fix'), v15=m.get('v15'),
               hop_gate=dict((k, v) for k, v in hg.items() if k != 'classes'))
    (work / 'plan_check.json').write_text(json.dumps(chk, indent=1, default=str) + '\n')
    pins = HG.read_pins(texts)
    by = {it.name: it for it in m['insts']}
    hops = []
    for bid, cls, bits, eps in m['buses']:
        ie = [(i, p) for i, p in eps if i in by]
        if len(ie) < 2:
            continue
        (da, dp), loads = ie[0], ie[1:]
        db, dlo, _ = G.pslice(dp)
        for li, lp in loads:
            lb, llo, _ = G.pslice(lp)
            Ls, first, last = [], None, None
            for b in range(bits):
                pa = HG._loc(by[da], pins, f'{db}[{(dlo or 0) + b}]')
                pb = HG._loc(by[li], pins, f'{lb}[{(llo or 0) + b}]')
                if pa is None or pb is None:
                    continue
                q = [round(v, 2) for v in pa + pb]
                first = first or q
                last = q
                Ls.append(abs(pa[0] - pb[0]) + abs(pa[1] - pb[1]))
            hops.append([bid, cls, bits, da, dp, li, lp, first, last, round(min(Ls), 1) if Ls else None,
                         round(max(Ls), 1) if Ls else None])
    with gzip.open(work / 'plan.json.gz', 'wt') as f:
        json.dump(dict(die=list(G.DIE), insts=[[it.name, it.master, round(it.x, 3), round(it.y, 3), round(it.w, 3),
                                                round(it.h, 3), it.orient, it.kind, it.region] for it in m['insts']],
                       hops=hops, corridors={k: list(v) for k, v in G._corridors(m).items()},
                       regions=[dict(r) for r in m['regions']]), f, default=str)
    print('V15DUMP legality overlaps=%d outside=%d pin_clashes=%d hop_gate %s max %.1f over%g=%d over_ss=%d' % (
        leg['overlaps'], leg['outside'], len(pc), hg['verdict'], hg['max_um'], lim, hg['bits_over_limit'], hg['bits_over_ss']))


if __name__ == '__main__':
    main()
