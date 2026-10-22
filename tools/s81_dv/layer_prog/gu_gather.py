#!/usr/bin/env python3
"""DRIVE-S81-GUPROP (10-20): the gate/up GATHER of a layer -- capture placement (xs_calendar.cap_emit) -> SW consumer.

Producer: the frames of slice g return gate / up row j of an expert; ot_s81sl_cap (cfg_d of cap_emit) writes it as BF16
to (leaf, word) of slice g (amap of cap_emit).  Consumer: lower_vs.shares -- beat leaf G = 5 sid + k (G < 63) runs ONE SW
(vs op 8, 16 groups) on ff [64 j', 64 j' + 64) of slot G // 9 (routed experts in id order, slot 6 = shared), j' = G % 9,
reading row pair (SW_IN + 2 s, SW_IN + 2 s + 1) = (gate quad s, up quad s) (ot_s81sl_vs.sv header, op 8).
Transport: an RD beat (ot_s81sl_xr.sv header: kind 4, [18:16] leaf, [28:19] row, [30:29] pairs - 1, up to 4 row pairs
(row, row + 1, ...) written one pair a cycle) carries ROW PAIRS, from the source leaf's RDOUT row pairs.  So a consumer
group is deliverable by ONE record iff its 4 gate words and 4 up words are one source row pair (same slice, same leaf,
gate row even, up row = gate row + 1, word w of the row = element 4 s + w).

    gu_gather.py --fixtures D --die-src DIE [--layer L0] --out MAP.json     (env: the campaign's OT_XS_* flags)

MAP.json: per expert slot the records {slot, expert, j (first ff element), src sid / leaf / row, dst sid / leaf / row},
RD beats (records packed: same src and dst leaf, src and dst rows +2, <= 4 pairs), refusals (groups that are not one
source row pair, with the reason), per-consumer-leaf and per-source-slice pair counts, local (src slice == dst slice)
records.  Exit 1 on any refusal.  Model of record for the bench vs/gen_guprop_bench.py; the RD path itself (xr send
config, ring / tier reservations, local loopback) is the open transport item (final_ffn_transport.py), not this map.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

FF_RANK = 576
SLOTS = 7
PAIRS_MAX = 4


def consumer(slot, j):
    """(sid, leaf, row) of ff element j (group-aligned) of slot: the SW operand row pair of the beat leaf"""
    import lower_vs as LV
    G = 9 * slot + j // 64
    s = (j % 64) // 4
    return G // 5, G % 5, LV.VS_ROWS['SW_IN'] + 2 * s, G


def records(amap, experts):
    """amap {(expert, gate|up, j): (slice, leaf, word)} -> (records, refusals)"""
    ids = [int(e) for e in experts]
    assert ids == sorted(set(ids)) and len(ids) == SLOTS - 1, ids
    names = [f'exp{e}' for e in ids] + ['shared']
    recs, bad = [], []
    for slot, ex in enumerate(names):
        for j in range(0, FF_RANK, 4):
            g = [amap.get((ex, 'gate', j + w)) for w in range(4)]
            u = [amap.get((ex, 'up', j + w)) for w in range(4)]
            why = None
            if None in g or None in u:
                why = 'missing'
            elif len({x[:2] for x in g + u}) != 1:
                why = 'quad split over source slices / leaves: ' + str(sorted({x[:2] for x in g + u}))
            else:
                w0 = g[0][2]
                if [x[2] for x in g] != [w0 + w for w in range(4)] or [x[2] for x in u] != [w0 + 4 + w for w in range(4)]:
                    why = f'not one (gate row, up row) pair: gate words {[x[2] for x in g]} up words {[x[2] for x in u]}'
                elif w0 % 8:
                    why = f'gate row {w0 // 4} odd (row pair misaligned)'
            if why:
                bad.append(dict(slot=slot, expert=ex, j=j, reason=why))
                continue
            sid, leaf, row, G = consumer(slot, j)
            recs.append(dict(slot=slot, expert=ex, j=j, src_sid=g[0][0], src_leaf=g[0][1], src_row=g[0][2] // 4,
                             dst_sid=sid, dst_leaf=leaf, dst_row=row, G=G))
    return recs, bad


def pack(recs):
    beats = []
    for r in recs:
        if beats:
            p = beats[-1][-1]
            if (len(beats[-1]) < PAIRS_MAX and all(r[k] == p[k] for k in ('src_sid', 'src_leaf', 'dst_sid', 'dst_leaf'))
                    and r['src_row'] == p['src_row'] + 2 and r['dst_row'] == p['dst_row'] + 2):
                beats[-1].append(r)
                continue
        beats.append([r])
    return beats


def check(amap, experts):
    recs, bad = records(amap, experts)
    beats = pack(recs)
    per_dst = Counter((r['dst_sid'], r['dst_leaf']) for r in recs)
    per_src = Counter(r['src_sid'] for r in recs)
    beats_dst = Counter((b[0]['dst_sid'], b[0]['dst_leaf']) for b in beats)
    srcs_per_G = {}
    for r in recs:
        srcs_per_G.setdefault(r['G'], set()).add(r['src_sid'])
    return dict(records=len(recs), refused=len(bad), refusals_first=bad[:8],
                refusal_reasons=dict(Counter(b['reason'].split(':')[0] for b in bad)),
                rd_beats=len(beats), local_records=sum(r['src_sid'] == r['dst_sid'] for r in recs),
                pairs_per_consumer_leaf_max=max(per_dst.values()) if per_dst else 0,
                rd_beats_per_consumer_leaf_max=max(beats_dst.values()) if beats_dst else 0,
                pairs_per_source_slice=dict(sorted(per_src.items())),
                source_slices_per_consumer_max=max((len(v) for v in srcs_per_G.values()), default=0),
                PASS=not bad and len(recs) == SLOTS * FF_RANK // 4), recs, beats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--fixtures', required=True)
    ap.add_argument('--die-src', default=None)
    ap.add_argument('--cols', action='store_true', help='column-reduced inventory (capacity_cols env OT_SVCPLAN_*)')
    ap.add_argument('--layer', default='L0')
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    import xs_place as XP
    import xs_calendar as XCAL
    if a.cols:
        import capacity_cols as CC
        CC.cols(a.die_src)
    elif XP.TP.ENABLED:
        import dv_layer_compile as C
        C.Die(C.die_tree(None, a.die_src))
    fx = XP.Fix(a.fixtures)
    ops = XP.XS_OPS[a.layer]
    rec, amap, slotc = XCAL.cap_emit(XP, fx, ops)
    summ, recs, beats = check(amap, fx.meta['experts'])
    gsl = [c for c in slotc if c['op'] in ('ffn.experts_gu', 'ffn.shared_gu')]
    js = XP.gu_slice_deal(FF_RANK)
    out = dict(schema='opentallas.s81_dv.gu_gather.v1', layer=a.layer, gu_prop=XP.GU_PROP, gu_merge=XP.GU_MERGE,
               topo=XP.TP.describe()['frames_per_slice'], slice_share=[len(x) for x in js],
               slice_first=[x[0] if x else None for x in js], cap_faults=rec['faults'], gu_slot_collisions=len(gsl),
               vp_rows_used=rec['vp_rows_used'], **summ)
    out['PASS'] = summ['PASS'] and rec['faults'] == 0 and not gsl
    prod = [dict(expert=kk[0], kind=kk[1], j=kk[2], sid=v[0], leaf=v[1], word=v[2]) for kk, v in sorted(amap.items())
            if kk[1] in ('gate', 'up')]
    Path(a.out).write_text(json.dumps(dict(out, records=recs, producer=prod,
                                           beats=[[r['j'] for r in b] for b in beats]), indent=1) + '\n')
    print('GU_GATHER', json.dumps({k: v for k, v in out.items() if k not in ('refusals_first',)}))
    return 0 if out['PASS'] else 1


if __name__ == '__main__':
    sys.exit(main())
