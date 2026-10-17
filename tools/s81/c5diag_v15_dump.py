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
    pair = None
    import os
    if os.environ.get('OT_S81_PAIR_GATE', '0') != '0':      # per-pair limits + hold races, exactly as mode `real`
        sys.path.insert(0, str(ROOT / 'tools' / 'hier_contract'))
        import pair_check as PC
        pair = PC.Gate(default_um=lim, buses=[(b_, c_, n_, [(e_[0], G.pslice(e_[1])[0]) for e_ in eps_]) for b_, c_, n_, eps_ in m['buses']])
    hg = HG.gate(m['insts'], m['buses'], texts, G.pslice, limit_um=lim, ss_um=G.SS_REACH_UM, top=100000, pair=pair)
    (work / 'hop_gate_full.json').write_text(json.dumps(hg, indent=1) + '\n')
    pal = None
    if hasattr(G, 'pin_align_gate'):      # owner 2026-10-13 pin alignment gate of `real` (never raises here: reported)
        pal = G.pin_align_gate(m, texts, work / 'pin_align.json', raise_on_fail=False)
    leg = G.legality(m)
    pc = G.pin_clashes(m)
    chk = dict(legality=leg, generated_pin_clashes=len(pc), pin_clash_examples=pc[:20],
               hop_fix=m.get('hop_fix'), relay_progress_fix=m.get('relay_progress_fix'), v15=m.get('v15'),
               hop_gate=dict((k, v) for k, v in hg.items() if k != 'classes'),
               pin_align=None if pal is None else {k_: pal.get(k_) for k_ in ('verdict', 'bundles', 'bits', 'by_verdict', 'jog_max',
                                                                             'jog_over_warn', 'order_not_preserved', 'cut_limit')})
    chk.update(lane_pins=m.get('lane_pins'), rly_face_reach=dict(n=len(m.get('rly_face_reach', [])),
                                                                 examples=m.get('rly_face_reach', [])[:10]))
    (work / 'plan_check.json').write_text(json.dumps(chk, indent=1, default=str) + '\n')
    if os.environ.get('OT_S81_DUMP_GLUE'):      # the glue RTL of this die case (kits of re-built glue masters)
        (work / 'dsfd_glue.sv').write_text(G.glue_rtl(m))
    # stage record for the layer-throughput stream: pin-to-pin register stages per hub bus + the field round trip
    import hub_stage_count as HS
    try:
        rec = G.plan_record_r8(m)
        frt = rec.get('field_round_trip_cycles')
        if frt:
            frt = {k_: v_ for k_, v_ in frt.items() if k_ != 'hop_fix'}
    except Exception as e_:                      # the plan record is a report, never a gate
        frt = dict(error=repr(e_))
    import collections
    rm_ = collections.Counter(it.master for it in m['insts'] if it.kind in ('rly', 'hstn') or it.master.startswith('dsfd_rly_'))
    (work / 'stage_counts.json').write_text(json.dumps(dict(
        tool='tools/s81/c5diag_v15_dump.py', hub_pin_to_pin_stages=dict(sorted(HS.count(m).items())),
        hub_chain_record=m.get('hub_stations'), hop_fix=m.get('hop_fix'), col_relays=m.get('col_relays'),
        lane_pins=m.get('lane_pins'), field_round_trip_cycles=frt, relay_masters=dict(sorted(rm_.items()))),
        indent=1, default=str) + '\n')
    # ROOT RELAY-SCHEMA 10-16: the full per-bus stage table (opentallas.die_relay_stages.v1) next to stage_counts.json
    import relay_stages_export as RSX
    import die_relay_stages as DRS
    DRS.write(work / 'relay_stages.json', RSX.export_model(m, f's81:{work.name}', sources=['tools/s81/c5diag_v15_dump.py']))
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
    print('V15DUMP legality overlaps=%d outside=%d pin_clashes=%d hop_gate %s max %.1f over%g=%d over_ss=%d pin_align %s' % (
        leg['overlaps'], leg['outside'], len(pc), hg['verdict'], hg['max_um'], lim, hg['bits_over_limit'], hg['bits_over_ss'],
        None if pal is None else (pal['verdict'], pal.get('by_verdict'))))


if __name__ == '__main__':
    main()
