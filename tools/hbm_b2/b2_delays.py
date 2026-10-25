#!/usr/bin/env python3
"""HBM-BIND (2026-10-24): table-driven B2 transport delays.  The r18h5 as-built delay params (VM_RT, VM_RT_EXTRA,
BANK_RT, VMX, CR_RT, ACK, SEL_LAT, ...) are placeholders on the B2 die; this tool re-derives them from a die plan's
lane latency table (die_plan.json latency.lanes) and the B2 die top (tools/hbm_b2/b2_top.py output), so a new plan
(B2m -> B2n ...) regenerates them with one command:

    python3 tools/hbm_b2/b2_delays.py --die die_b2.v --plan die_plan.json --census-map census_map.json \
        [--census hbm_census.json.gz] --out b2_delays.json

1. Every kept leaf -> leaf connection is placed on the plan: instance -> partition (census_map parts, or the groups of
   its rules = the nearest member pair with a lane), connection -> the plan lanes src part -> dst part of its census kind
   (r18h5 census, SW names mapped to NE; default data); lane latency = latency.lanes[id].cycles (max over the matching
   lanes: the binder pads the shorter ones).  Traffic per (src part, dst part, kind) (unique source bits) is compared
   with the plan lane widths: LANE_CAPACITY rows (plan change when need > lanes).
2. Bank-latency class (tools/hbm_die_v16/d4g_bank_latency.py check(), unchanged rules): the B2 die is written as a d4g
   contract in which every cross-partition connection carries `cycles` registered stations (hbfd_rly), so every VM
   bank client's / share's round-trip param is derived exactly as on the d4g die.  want != have -> params[inst][param].
3. Rules outside the bank class (derived here, each with its formula in `derivations`):
   SEL_LAT (rootctl_am) = 4 + lane(sel_op) + lane(selected_v)   [as built 40 = 4 + 18 + 18 on r18h5]
   CR_RT (rootctl_am) / ACK (argmax r2) = hub echo: 1 (hub tile pin) + lane(cq) + lane(cr) + remote, remote = 0 when the
   hub owns the client's sector, else 16 + LINK(out) + LINK(back) (two-stop ring PREQ->PRSP: tb_vms_ring2_static
   schedules a local cr at cq + BL + 2 and a remote one at cq + 18 + 2 LINK + BL); ACK = 13 + CR_RT.
   score chain (compiler --score-chain): lane(score -> xq_N) + 2 (xq node) + lane(xq_N -> selector).
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'hbm_die_v16'))
import b2_top as T  # noqa: E402
import d4g_bank_latency as BL  # noqa: E402

PRM = re.compile(r"\.(\w+)\(([^()]*)\)")


def parse_params(s):
    out = {}
    for k, v in PRM.findall(s or ''):
        v = v.strip()
        m = re.fullmatch(r"(?:\d+'[dD])?(\d+)", v)
        c = re.fullmatch(r"\{(.*)\}", v)
        if m:
            out[k] = int(m.group(1))
        elif c:      # Verilog concatenation of per-bank values: MSB first -> list element b = bank b
            out[k] = [int(re.sub(r"^\d+'[dD]", '', x.strip())) for x in c.group(1).split(',')][::-1]
        else:
            out[k] = v
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--die', required=True)
    ap.add_argument('--plan', required=True)
    ap.add_argument('--census-map', required=True)
    ap.add_argument('--census')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    die = T.Die(a.die, [])
    plan = json.loads(Path(a.plan).read_text())
    cm = json.loads(Path(a.census_map).read_text())
    lat = plan['latency']['lanes']
    # ---- lanes: (src part, dst part, kind) -> [(id, cycles, width)]
    lanes = collections.defaultdict(list)
    for ln in plan['lanes']:
        ps = {p['id']: p for p in plan['ports']}
        p0, p1 = ps[ln['ports'][0]], ps[ln['ports'][-1]]
        lanes[(p0['src']['part'], p1['dst']['part'], p0['kind'])].append((ln['id'], lat[ln['id']]['cycles'], p0['width']))
    # ---- instance -> candidate partitions
    parts = {}
    for n in die.insts:
        if n in cm['parts']:
            parts[n] = [cm['parts'][n]]
        else:
            for rx, g in cm['rules']:
                if re.search(rx, n):
                    parts[n] = cm['groups'][g]
                    break
    kinds = {}
    if a.census:
        for g in json.load(gzip.open(a.census, 'rt'))['groups']:
            kinds[(g['src'], g['src_bus'], g['dst'], g['dst_bus'])] = g['kind']

    def kind_of(si, sp, ki, kp):
        for f in (lambda x: x, lambda x: re.sub(r'(?<=_)NE(?=\d|_|$)', 'SW', x)):
            k = kinds.get((f(si), sp, f(ki), kp))
            if k:
                return 'ctl' if k == 'ctl' else 'data'
        return 'data'

    def lane(si, ki, kd):
        """(cycles, src part, dst part, lane ids) of the best member pair; cycles 0 inside one partition."""
        best = None
        for A in parts.get(si, []):
            for B in parts.get(ki, []):
                if A == B:
                    return 0, A, B, []
                ls = lanes.get((A, B, kd)) or lanes.get((A, B, 'data' if kd == 'ctl' else 'ctl')) or []
                if ls:
                    c = max(x[1] for x in ls)
                    if best is None or c < best[0]:
                        best = (c, A, B, [x[0] for x in ls])
        return best

    # ---- contract (d4g form) with plan stations on every cross-partition connection
    inst = {n: dict(master=i['master'], params=parse_params(i['params']), ports=sorted(i['conns'])) for n, i in die.insts.items()}
    edges, unmapped, nolane = [], set(), collections.Counter()
    traffic = collections.defaultdict(set)       # (A, B, kind) -> {(src inst, port, bit)}
    conn_lane = {}                               # (src inst, src port, sink inst, sink port) -> cycles
    nrly = 0
    for ki, i in die.insts.items():
        for kp, e in i['conns'].items():
            if die.dirs.get(e) == 'output':
                continue
            try:
                segs = die.resolve(T.parse_expr(e, die.widths))
            except Exception:
                continue
            off = 0
            for s, _ in segs:
                w = T.seg_width(s)
                if s[0] == 'n' and s[1] in die.driver:
                    si, sp = die.driver[s[1]]
                    if si not in parts or ki not in parts:
                        unmapped.update(x for x in (si, ki) if x not in parts)
                        edges.append(dict(source=[si, sp, s[2], s[3] + 1], sink=[ki, kp, off, off + w]))
                    else:
                        kd = kind_of(si, sp, ki, kp)
                        L = lane(si, ki, kd)
                        if L is None:
                            nolane[(parts[si][0], parts[ki][0], kd)] += w
                            cyc = 0
                        else:
                            cyc, A, B, _ = L
                            if cyc:
                                traffic[(A, B, kd)].update((si, sp, b) for b in range(s[2], s[3] + 1))
                        conn_lane[(si, sp, ki, kp)] = cyc
                        src = [si, sp, s[2], s[3] + 1]
                        for _ in range(cyc):
                            r = f'b2rly{nrly}'; nrly += 1
                            inst[r] = dict(master='hbfd_rly_b2', params={}, ports=['i', 'o'])
                            edges.append(dict(source=src, sink=[r, 'i', 0, w]))
                            src = [r, 'o', 0, w]
                        edges.append(dict(source=src, sink=[ki, kp, off, off + w]))
                off += w
    rows, summ = BL.check(dict(instances=inst, edges=edges))
    params = collections.defaultdict(dict)
    der = []
    for r in rows:
        if r['status'] == 'INFO' or r.get('want') is None or isinstance(r.get('want'), list):
            continue
        der.append(dict(inst=r['client'], param=r['param'], have=r.get('have'), want=r['want'], status=r['status'],
                        rule='d4g_bank_latency', bad=r['bad'][:3]))
        if r.get('have') != r['want']:
            params[r['client']][r['param']] = r['want']
    # scalar share / client rows report `rt` (not want) when PASS/FAIL on the param: recompute want for those
    for r in rows:
        if r['status'] in ('PASS', 'FAIL') and r.get('want') is None and r.get('param') and r.get('rt'):
            m = r['master']
            rule = next((x for x in BL.RULES.get(m, []) if x[2] == r['param']), None)
            if rule:
                want = rule[4] + max(r['rt']) - rule[5]
                have = inst[r['client']]['params'].get(r['param'], rule[3])
                der.append(dict(inst=r['client'], param=r['param'], have=have, want=want, status=r['status'],
                                rule='d4g_bank_latency', rt=r['rt'], bad=r['bad'][:3]))
                if have != want:
                    params[r['client']][r['param']] = want

    def lc(si, sp, ki, kp):
        return conn_lane.get((si, sp, ki, kp))
    # ---- non-bank rules
    for n, i in die.insts.items():
        m = i['master']
        if m == 'ot_hbm_idx_rootctl_static_am':
            sel = next((x for x in die.insts if die.insts[x]['master'].startswith('ot_hbm_idx_selector')), None)
            v = 4 + lc(n, 'sel_op', sel, 'op') + lc(sel, 'selected_v', n, 'selected_v')
            der.append(dict(inst=n, param='SEL_LAT', want=v, formula='4 + lane(sel_op) + lane(selected_v)'))
            params[n]['SEL_LAT'] = v
    # hub echo (cq -> hub -> cr) for the root clients on the two-stop ring master
    hub = next((x for x in die.insts if die.insts[x]['master'] == 'hfd_hgi_vms_glue_nw2_t'), None)
    peer = next((x for x in die.insts if die.insts[x]['master'] == 'hfd_hgi_vms_static_NE2_glue'), None)
    if hub:
        lo = lc(hub, 'ccw_out', peer, 'ccw_in'); lb = lc(peer, 'cw_out', hub, 'cw_in')
        for n, pn, base in (('hb_idx__ctl', 'CR_RT', 0), ('hb_argmax', 'ACK', 13)):
            if n not in die.insts:
                continue
            sid = parse_params(die.insts[n]['params']).get('SID', 0)
            remote = 0 if sid == 2 else 16 + lo + lb
            v = base + 1 + lc(n, 'cq', hub, 'cq') + lc(hub, 'cr', n, 'cr') + remote
            der.append(dict(inst=n, param=pn, want=v, formula=f'{base} + 1 (hub pin) + lane(cq) {lc(n, "cq", hub, "cq")} + '
                            f'lane(cr) {lc(hub, "cr", n, "cr")} + remote {remote} (SID {sid}; 16 + LINK {lo} + {lb})'))
            params[n][pn] = v
    sc = {}
    for q in ('NW', 'NE'):
        s, x = f'hb_idx__s_{q}', 'hb_idx__xq_N'
        p = 'a' if q == 'NW' else 'b'
        sel = next((y for y in die.insts if die.insts[y]['master'].startswith('ot_hbm_idx_selector')), None)
        if s in die.insts and x in die.insts:
            sc[q] = lc(s, 'score', x, p) + 2 + lc(x, 'y', sel, 'in_line')
    cap = []
    for (A, B, kd), bits in sorted(traffic.items()):
        ls = lanes.get((A, B, kd), [])
        have = sum(x[2] for x in ls)
        cap.append(dict(src=A, dst=B, kind=kd, need=len(bits), lanes=[x[0] for x in ls], width=have,
                        status='OK' if len(bits) <= have else 'OVER'))
    out = dict(schema='opentallas.hbm_b2.delays.v1', plan_note=plan.get('note', '')[:200],
               rule=__doc__.split('\n\n')[0], bank_latency=summ,
               params={k: v for k, v in sorted(params.items())}, derivations=der,
               score_chain=dict(edges=sc, formula='lane(score -> xq_N) + 2 (xq node) + lane(xq_N -> selector)'),
               lane_capacity=cap, capacity_over=[c for c in cap if c['status'] == 'OVER'],
               unmapped_instances=sorted(unmapped), no_lane={f'{k[0]}->{k[1]} {k[2]}': v for k, v in nolane.items()})
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(f'B2_DELAYS params={sum(len(v) for v in params.values())} bank_latency={summ} '
          f'capacity_over={len(out["capacity_over"])} unmapped={len(unmapped)} no_lane={len(nolane)}')


if __name__ == '__main__':
    main()
