#!/usr/bin/env python3
"""Q-COLLCAL 10-18: ONE latency per die bus + the collective calendar's SerDes lane cycles, from the die GEN's lanes.

The TP8 co-sim (TOKEN-XDIE-QTP8, claude/xdie-qtp8-1018 fed8119c7) found two Qwen compute die bugs:
  (1) the dv2f14 forwarded lanes between io_collective and io_serdes_j add cycles that the collective calendar (the
      SerDes face rx calendars, PHY = PS) did not count -> every die faults its static schedule;
  (2) the GEN gave each bus its own E from its own frame count: serdes2_txv E 6 vs serdes2_tx E 5 -> valid desynchronised
      from its data.
This module is the single source both the GEN (tools/qwen_rom_fulldie_b3r2.py, OT_SPLIT_FWD_LANES=1) and the checks
(tools/qwen_split/lane_latency_audit.py, run by port_bind_compute.sh = the strict bind gate) use:

  group_of(rows)        bus groups: a valid bus (<stem>v / <stem>_v [+ _wi/_wo]) and the data buses of the same
                        src -> dst whose bid is <stem>[<token>] (serdes2_tx + serdes2_txv, sf_result_v + sf_result_*,
                        dvw_arv_wo + dvw_ar{d,l,m,t}_wo, ...).  LANDING-CONTRACT L5: "a link is all lanes of one bundle,
                        because they share a compiler slot" -> ONE E per group.
  equalize(rows, D)     group E = max member E; the earlier members wait in their ring (E_sta + dE, the landing MCP)
                        -- fails closed when E_sta would leave the D-slot window (E_sta > D - 1);  K = (E + cal) mod 8 with
                        cal = the land plan's calendar offset G - R0 (0 when unplanned).  NOTE K is the TOTAL lane
                        epoch (the landing's write counter starts at the SOURCE release, rtl/qwen_split/qfd_fwd_lane.sv;
                        bench_fwd_lane.sh K = L - 1 - (R0 - G)), never the residual E_sta.
  lane_cycles(row)      core cycles a lane adds between the two blocks: L = E + 1 (o is a register; with K from the
                        calendar the latency is K + 1 + (R0 - G) = E + 1 at any reset calendar); a plain relay chain
                        of n frames adds n; no frames 0.
  coll_lane_latency()   per SerDes port j: TX = lanes io_collective -> io_serdes_j, RX = io_serdes_j -> io_collective
                        (data and valid of one direction MUST agree), and the calendar's
                        LX_j = TX(peer port of j) + RX(j) with the TP8 package mesh peer map {0: 2, 1: 1, 2: 0}
                        (port j of package P -> package (P+1+j) % 4 arrives on the peer's port 2-j).  UCIe has no
                        calendar knob: any UCIe lane cycle is a fail.  The die GEN writes it as case/coll_lane_latency.json
                        and as the io_collective master's elaboration parameters (die.v.params.json LX0..2).

    lane_groups.py emit --lanes case/fwd_lanes.json [--land-plan land_plan.json] --out coll_lane_latency.json
        (re-derives what the GEN emits from an existing GEN's lanes: equalize + coll_lane_latency)
"""
import argparse
import json
import re
import sys
from pathlib import Path

LAND_O = 1                                  # the landing's registered output o (flop-last)
PEER_PORT = {0: 2, 1: 1, 2: 0}              # TP8 package mesh: port j of P -> (P+1+j) % 4, arriving on port 2-j
SERDES_INST = ('io_serdes', 'io_serdes_1', 'io_serdes_2')
COLL_INST = 'io_collective'
COLL_MASTER = 'qfd_collective_static_io_production'
_VALID = re.compile(r'^(?P<stem>.+?)(?P<v>_v|v)(?P<suf>_w[io])?$')


def _members(stem, v, suf, bid, cands):
    out = []
    for c in cands:
        if c == bid or not c.startswith(stem) or not c.endswith(suf or ''):
            continue
        mid = c[len(stem):len(c) - len(suf or '')]
        # '<stem>v' family: the data bus is <stem> or <stem><one short token> (txv -> tx; arv -> ard/arl; rv -> rd/rr)
        # '<stem>_v' family: the data buses are <stem>_<anything> (sf_result_v -> sf_result_tag ...)
        if (v == 'v' and re.fullmatch(r'[a-z0-9]{0,3}', mid)) or (v == '_v' and mid.startswith('_') and '__' not in mid):
            out.append(c)
    return out


def group_of(rows):
    """{bid: group id}; a bus in no valid/data family is its own group.  rows: dicts with bid, src, dst."""
    by_pair = {}
    for r in rows:
        by_pair.setdefault((r.get('src'), r.get('dst')), []).append(r['bid'])
    g = {r['bid']: r['bid'] for r in rows}
    for (s, d), bids in by_pair.items():
        for b in bids:
            m = _VALID.match(b)
            if not m:
                continue
            mem = _members(m.group('stem'), m.group('v'), m.group('suf'), b, bids)
            if mem:
                gid = f"{m.group('stem')}*{m.group('suf') or ''}:{s}->{d}"
                for x in [b] + mem:
                    g[x] = gid
    # QXF-SEAMC 10-18 (TOKEN-XDIE-QWEN F5, LAYERBENCH G-C2): a RECORD BUNDLE (tools/qwen_split/record_bundles.py: valid +
    # slots + kind / beat + payload of one static record, selected by endpoint pins as the compiler does) is ONE group
    # whatever its bus names: lnk_rx_payload rides with lnk_native_rx_*, sf_prog_auth_slot with sf_prog_rx_v
    for r in rows:
        if r.get('bundle'):
            g[r['bid']] = f"record:{r['bundle']}"
    return g


T_PS = 833.333


# QK-LANDEN 10-19 (coordinator, Q.STA.LAND600.3 option (b)): a one-frame lane (n = 1, qfd_landh0) registers the source's
# released reset en on ck_s before its hop-0 clock gate (rtl/qwen_split/qfd_fwd_lane.sv ot_qfd_land FIRST=1): its write
# epoch is source edge G + 1, so its strap is K = (E + G + 1 - R0) mod 8.  The data age E (and lane_cycles) is unchanged:
# every word is still written on the same physical edge.  Added ONCE here (the land plan's K / calendar exclude it) and in
# reset_calendar_audit.py (finalize_model / audit), which owns the post-reset-tree strap.
# RLYH0-EN 10-19: the multi-frame lanes' hop-0 station (qfd_rlyh0, ot_qfd_lane_st FIRST=1) registers en on its source root
# the same way (closed rlyh0 views: en -> ICG native capture 194-278 ps > 190), so EVERY forwarded data lane (n >= 1)
# carries the +1: K = (E + G + 1 - R0) mod 8.
HOP0_EN_REG = 1


def hop0_en_reg(row):
    """release edges the hop-0 en register adds to the lane's write epoch: 1 for every forwarded data lane (n >= 1:
    landh0 or rlyh0 registers en on the source root before its clock gate), else 0"""
    return HOP0_EN_REG if int(row.get('n') or 0) >= 1 else 0


def equalize(rows, D=4, cal=None, h0=None):
    """In-place: one E per bus group for the forwarded data lanes (rows with E not None).  cal: {bid: G - R0};
    h0: {bid: {corner: single-cycle hold slack ps}} from the land plan (die STA).  The earlier member's landing MCP grows
    by dE; its hold window is hold_E = H0 + (D - E_sta) T >= 0 at every corner (land plan rule) when the STA is known,
    else E_sta <= D - 1 (no STA yet: keep one slot of margin).  Raises ValueError when a group cannot share one E."""
    cal, h0 = cal or {}, h0 or {}
    data = [r for r in rows if r.get('E') is not None]
    gid = group_of(data)
    groups = {}
    for r in data:
        groups.setdefault(gid[r['bid']], []).append(r)
    rec, bad = {}, []
    for g, mem in sorted(groups.items()):
        if len(mem) < 2:
            continue
        E = max(int(r['E']) for r in mem)
        cals = {(int(cal.get(r['bid'], 0))) % 8 for r in mem}
        if len(cals) > 1:
            bad.append(f'{g}: members on different reset calendars {sorted(cals)}')
        for r in mem:
            dE = E - int(r['E'])
            if dE:
                r.setdefault('E_own', int(r['E']))
                r['E_sta'] = int(r.get('E_sta') or 2) + dE
                r['E'] = E
                r['E_basis'] = (r.get('E_basis') or '') + f'; Q-COLLCAL bus group {g}: +{dE} (one E per bus, LANDING-CONTRACT L5)'
                hh = h0.get(r['bid'])
                if hh:
                    r['hold_E_group'] = {c: round(v + (D - r['E_sta']) * T_PS, 1) for c, v in hh.items()}
                    if any(v < 0 for v in r['hold_E_group'].values()):
                        bad.append(f"{r['bid']}: group E {E} -> landing MCP {r['E_sta']}: hold window {r['hold_E_group']} < 0 (raise D)")
                elif r['E_sta'] > D - 1:
                    bad.append(f"{r['bid']}: group E {E} needs landing MCP {r['E_sta']} > D-1 = {D - 1} without die STA (raise D)")
            r['group'] = g
        rec[g] = dict(E=E, members={r['bid']: r.get('E_own', E) for r in mem})
    for r in data:
        r['cal'] = (int(cal.get(r['bid'], 0)) + hop0_en_reg(r)) % 8
        r['K'] = (int(r['E']) + r['cal']) % 8
        r['K_basis'] = ('Q-COLLCAL: K = (total E + G - R0) mod 8' + (' (land plan calendar)' if r['bid'] in cal else ' (G = R0)')
                        + (' + 1 (hop-0 en registered on the source root: QK-LANDEN landh0 / RLYH0-EN rlyh0)' if hop0_en_reg(r) else ''))
    if bad:
        raise ValueError('bus groups: ' + '; '.join(bad))
    return rec


def lane_cycles(row):
    if row.get('E') is not None:
        return int(row['E']) + LAND_O
    if row.get('lane') == 'reset':
        return None
    return int(row.get('n') or 0)          # plain relay chain: one cycle per frame


def coll_lane_latency(rows, plain=None, source=''):
    """rows: forwarded lanes (fwd_lanes.json 'lanes'); plain: [{bid, src, dst, n}] buses carried by plain relays (or
    zero-frame).  Returns the record with LX0..2 and a verdict."""
    every = {r['bid']: r for r in (plain or [])}
    every.update({r['bid']: r for r in rows})
    ports, bad = {}, []

    def cyc(bid):
        r = every.get(bid)
        return (0, 0, None) if r is None else (lane_cycles(r), r.get('n', 0), r.get('K'))

    for j, inst in enumerate(SERDES_INST):
        p = {}
        for d in ('tx', 'txv', 'rx', 'rxv'):
            L, n, K = cyc(f'serdes{j}_{d}')
            p[d] = dict(cycles=L, n=n, K=K, E=(every.get(f'serdes{j}_{d}') or {}).get('E'))
        for a, b in (('tx', 'txv'), ('rx', 'rxv')):
            if p[a]['cycles'] != p[b]['cycles']:
                bad.append(f'serdes{j}: {a} {p[a]["cycles"]} vs {b} {p[b]["cycles"]} cycles (one latency per bus)')
        p['TX'], p['RX'] = p['tx']['cycles'], p['rx']['cycles']
        ports[j] = p
    LX = [ports[PEER_PORT[j]]['TX'] + ports[j]['RX'] for j in range(3)]
    ucie = {d: cyc(f'ucie_{d}')[0] for d in ('tx', 'txv', 'rx', 'rxv')}
    if any(ucie.values()):
        bad.append(f'UCIe lane cycles {ucie}: the UCIe calendar (LU) has no lane knob')
    return dict(schema='opentallas.qwen_split.coll_lane_latency.v1', source=source, master=COLL_MASTER, instance=COLL_INST,
                rule='LX_j = TX(peer port of j) + RX(j); lane cycles = E + 1 (forwarded lane, o register) | n (plain relays)',
                peer_port=PEER_PORT, land_o=LAND_O, ports=ports, ucie=ucie, LX=LX,
                params={f'LX{j}': LX[j] for j in range(3)}, verdict='FAIL' if bad else 'PASS', fails=bad)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    e = sp.add_parser('emit')
    e.add_argument('--lanes', required=True, type=Path)
    e.add_argument('--land-plan', type=Path, help='land plan whose E_sta / calendar the GEN would take (OT_SPLIT_LAND_PLAN)')
    e.add_argument('--out', required=True, type=Path)
    e.add_argument('--lanes-out', type=Path, help='write the equalized lanes too')
    a = ap.parse_args()
    fl = json.loads(a.lanes.read_text())
    rows = fl['lanes']
    cal, h0 = {}, {}
    if a.land_plan:
        # the GEN with OT_SPLIT_LAND_PLAN: E_sta = plan E, E = fwd_e_est(n) + E_sta - 2; calendar = plan K - plan E
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import math
        lp = {x['bid']: x for x in json.loads(a.land_plan.read_text())['links']}
        h0 = {b: x['h0'] for b, x in lp.items() if x.get('h0')}
        for r in rows:
            x = lp.get(r['bid'])
            if r.get('E') is None or not x or x.get('E') is None:
                continue
            r['E_sta'] = int(x['E'])
            r['E'] = max(2, math.ceil((r['n'] - 1) / 2) + 1) + r['E_sta'] - 2
            if x.get('K') is not None:
                cal[r['bid']] = (int(x['K']) - int(x['E'])) % 8
    groups = equalize(rows, fl.get('D', 4), cal, h0)
    plain = [dict(bid=s['bid'], src=None, dst=None, n=s.get('n', 0)) for s in fl.get('skipped', [])]
    rec = coll_lane_latency(rows, plain, source=str(a.lanes) + (f' + {a.land_plan}' if a.land_plan else ''))
    rec['bus_groups'] = groups
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    if a.lanes_out:
        a.lanes_out.write_text(json.dumps(fl, indent=1) + '\n')
    print(json.dumps(dict(LX=rec['LX'], verdict=rec['verdict'], fails=rec['fails'], groups=len(groups))))
    return 0 if rec['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
