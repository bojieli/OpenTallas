#!/usr/bin/env python3
"""TOK-DS 10-25: re-target the 16-slice attention-norm XQ/XB all-gather occupancy model (norm_q) from the DV bind9 die
to a physical/die_plan/s81 latency table (plan v4.8 family, e.g. the adopt178 table), then solve the static per-SID
rstd release LUT (norm_quant_schedule) and price it.

Why: norm_q_report.py reads lane ages from results/arch/s81_dv_1016/bind9/die.v.gz (+ p4l plan / land plan), the
replay vehicle.  The plan-v4.8 release die has a different V topology (column 1 is a direct s_1S_C <-> s_1N_C xtier
lane, no BK_COL bridge) and abutted xring line links, and its latency table is what adopt178 changed.

Consumed plan lanes (exactly):
  line  xring__s_<c><T>_C__s_<c+-1><T>_C        (age of one line hop; LINE_STOP=2 added per stop as norm_q)
  V     xtier__<src>__<dst> chained from s_<c><T>_C to s_<c><T'>_C through bridge partitions
        bridges (selected RTL contracts, as norm_q_report): bk_sel 3, seqhost 7, gunit 12, eng 2, bk_col 2
Kept from the DV compile report (NOT re-derived on the plan; a calibration item): per-slice root write-back edges
(root_rel), i.e. the NX snake arrival spread, and Q_AFTER_ROOT.  Plan 'cycles' are taken as pin-to-pin ages.

  norm_q_plan.py <dv fullV report.json> <s81_latency.json> --out DIR [--max-delay 512]
"""
import argparse
import hashlib
import json
from pathlib import Path

import norm_q as Q
import norm_quant_schedule as S

BRIDGES = dict(bk_sel=3, seqhost=7, gunit=12, eng=2, bk_col=2)


def part(inst):
    return inst[2:] + '_C'          # u_s_4S -> s_4S_C


def plan_report(dv, lat):
    L = lat['lanes']
    sl = dv['slices']
    names = sorted(sl, key=lambda n: sl[n]['sid'])
    pos = {i: (sl[i]['sid'] >> 1, sl[i]['sid'] & 1) for i in names}
    byct = {v: k for k, v in pos.items()}
    tier = lambda t: 'N' if t else 'S'   # sid & 1: 0 = S, 1 = N (u_s_0S sid0, u_s_0N sid1)
    for i in names:
        assert i.endswith(tier(pos[i][1])), i
    used = {}
    line_age = {}
    for i in names:
        c, t = pos[i]
        for side, nc in (('e', c + 1), ('w', c - 1)):
            if 0 <= nc < 8:
                lk = f'xring__{part(i)}__{part(byct[(nc, t)])}'
                line_age[f'{i}.{side}'] = L[lk]['cycles']
                used[lk] = L[lk]['cycles']
    vpaths, vasm = {}, {}
    for i in names:
        c, t = pos[i]
        peer = byct[(c, 1 - t)]
        at, prev, total, path = part(i), None, 0, []
        for _ in range(8):
            out = [k for k in L if k.startswith(f'xtier__{at}__') and k.split('__')[2] != prev]
            if len(out) != 1:
                raise ValueError(f'V route from {i}: ambiguous/absent xtier out of {at}: {out}')
            lk = out[0]
            dst = lk.split('__')[2]
            used[lk] = L[lk]['cycles']
            path.append(dict(lane=lk, cycles=L[lk]['cycles']))
            total += L[lk]['cycles']
            if dst == part(peer):
                break
            if dst.startswith('s_'):
                raise ValueError(f'V route from {i} ends at a different slice {dst}')
            if dst not in BRIDGES:
                raise ValueError(f'unmodelled V bridge {dst}')
            path.append(dict(bridge=dst, cycles=BRIDGES[dst]))
            total += BRIDGES[dst]
            prev, at = at, dst
        else:
            raise ValueError(f'V route from {i} too long')
        vpaths[i] = dict(peer=peer, wire_and_bridge_cycles=total, assembled_after_own_line=total + 2, path=path)
        vasm[i] = total + 2
    rep = dict(slices={i: dict(sid=sl[i]['sid'], root_rel=sl[i]['root_rel']) for i in names}, line_age=line_age,
               v_paths=vpaths, v_assembly_age=vasm, v_paths_complete=True, v_bridge_cycles=BRIDGES,
               geometry='plan latency table (xring/xtier lanes); roots from the DV bind9 compile report',
               consumed_lanes=used)
    return rep


def occupancy(rep, q):
    sl = rep['slices']
    names = sorted(sl, key=lambda n: sl[n]['sid'])
    pos = {i: (sl[i]['sid'] >> 1, sl[i]['sid'] & 1) for i in names}
    byct = {v: k for k, v in pos.items()}
    geo = dict(pos=pos, partner={i: byct[(c, 1 - t)] for i, (c, t) in pos.items()},
               age={(i, s): rep['line_age'][f'{i}.{s}'] for i in names for s in 'ew' if f'{i}.{s}' in rep['line_age']})
    Q.V_ASM = {i: rep['v_assembly_age'][i] for i in names}
    occ, cl, oa = Q.allgather(q, geo)
    return dict(last_line_emit_relative=max(e for (_, _, e) in occ),
                last_line_capture_relative=max(e + geo['age'][(i, s)] for (i, s, e) in occ),
                line_collision_edges=len(cl), own_assembled_collision_edges=len(oa))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('dv_report')
    p.add_argument('latency')
    p.add_argument('--out', required=True)
    p.add_argument('--max-delay', type=int, default=512)
    a = p.parse_args()
    dv = json.loads(Path(a.dv_report).read_text())
    raw = Path(a.latency).read_bytes()
    lat = json.loads(raw)
    rep = plan_report(dv, lat)
    rep['latency_table'] = dict(path=a.latency, sha256=hashlib.sha256(raw).hexdigest(), plan_digest=lat.get('plan_digest'))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'report.json').write_text(json.dumps(rep, indent=1) + '\n')
    sol = S.solve_report(rep, a.max_delay)
    (out / 'calendar.json').write_text(json.dumps(sol, indent=1) + '\n')
    price = dict(qualification='MODEL_ONLY (plan lane ages, DV roots); actual RTL cut + physical closure required')
    if sol.get('releases'):
        names = sorted(rep['slices'], key=lambda n: rep['slices'][n]['sid'])
        d = [sol['releases'][i]['delay'] for i in names]
        if max(d) > 255:
            raise ValueError('delay does not fit the 8-bit QDELAYS field')
        lut = sum(v << (8 * k) for k, v in enumerate(d))
        base = occupancy(rep, {i: rep['slices'][i]['root_rel'] for i in names})
        rel = occupancy(rep, {i: sol['releases'][i]['q_rel'] for i in names})
        price.update(per_sid_hold_cycles=d, shared_lut_hex=f"128'h{lut:032x}", maximum_hold_cycles=max(d),
                     occupancy=dict(base=base, release=rel),
                     last_capture_added_cycles=rel['last_line_capture_relative'] - base['last_line_capture_relative'])
    else:
        price.update(verdict=sol['verdict'])
    (out / 'price.json').write_text(json.dumps(price, indent=1) + '\n')
    print(json.dumps(price, indent=1))


if __name__ == '__main__':
    main()
