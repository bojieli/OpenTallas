#!/usr/bin/env python3
"""QXF-SEAMC 10-18: RECORD BUNDLES of the Qwen compute die seams -- one E (one arrival edge) per bundle.

A static record crosses the die as ONE bundle: its valid, its slot strobes, its kind / beat and its payload are produced
on one edge by the source block's pin registers and the consumer samples them on one edge (no ready, no FIFO, owner
static-schedule rule 10-14).  The compiler's D2D calendar (claude/layerbench-qwen-1018 tools/qwen_layerbench/
layer_compile.py BUNDLES + OT_RELAY_SCHEDULE compiled_L1/relay_schedule/compute_compiled.json) compiles ONE seam age per
bundle, so the die must deliver every member on that one age.  Two die bugs broke it:
  F5 (TOKEN-XDIE-QWEN, dv2f14bn die.v sha a7a9f980): d2d_rom -> native59 rx record: rx_payload was a 1-frame lane
     (landh0, K 2 -> 3 edges) but native_rx_v / slot / kind / beat were direct wires (0 edges) -> rx_record fault at the
     first RESULT.  Cause: LAND_CROSS / the forwarded-lane pass treat every BUS on its own; a member gets a landing only
     when the relay planner happened to give it a frame (zero-stage buses stay direct).
  G-C2 (LAYERBENCH-QWEN smoke): d2d_rom -> sys_face program record: prog_auth_slot 6 frames K 4 (+5), prog_witness_slot
     5 frames K 3 (+4) vs rx_payload / prog_rx_v / prog_context_slot K 2 (+3) -> record-port slot_fault at HOST BEGIN.
     Cause: each lane's E = fwd_e_est(own frame count); Q-COLLCAL's bus groups (lane_groups.group_of, valid-name
     families) do not see these bundles (prog_* has no '<stem>_v' family; rx_payload is a lnk_* bus).
The rule here: bundles are defined by their ENDPOINT PINS (source inst.port -> sink inst.port, the selection the
compiler uses), never by bus names, and the GEN must
  (1) give every zero-stage member of a bundle whose other members have frames a one-frame landing (close_zero_stage),
  (2) equalize the bundle's lanes to one E (lane_groups.equalize with the bundle as the group: the early members wait
      in their ring, K = total E + calendar), and
  (3) fail closed when the built bundle still has unequal lane cycles (audit_rows / audit_netlist).

Consumer evidence (which pins are sampled together, file:line on the Q-COLLCAL lineage 04f8b56c6):
  C.rx_record  qfd_native59_record_endpoint -> qkd_native_attention_record rx_event / rx_expected / rx_payload kind /
               epoch / layer / beat checked on ONE edge (rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv:52-57)
  C.tx_slot    same codec, tx_expected / tx_expected_kind / tx_expected_beat on the tx_event edge (:50-55)
  C.tx_record  qfd_d2d_static pin registers native_tx_v + native_tx_payload (ot_qwen_d2d_dies.sv:405-412)
  C.x3_record  qfd_d2d_static x3 + x3_identity + x3_generation (KVN record, one capture)
  SF.rx_record qfd_sys_face_record_port: slot_fault if rx_v !== (auth_slot | context_slot) on any edge, auth / context
               RX decode rx_record on rx_v && slot (rtl/qwen_split/qfd_sys_face_record_port.sv:51-56); the EMB path
               samples rx_payload on emb_rx_v and faults emb_rx_v !== emb_rx_slot (qfd_sys_face.sv:477-480); the
               witness slot is the same d2d calendar's strobe (one seam age per direction)
  SF.cfg       qfd_d2d_static cal cfg_we + cfg_addr + cfg_data written on one edge (ot_qwen_d2d_static.sv:147-151)
  SF.cal       cal_start + cal_seg (start_seg sampled with start, ot_qwen_d2d_static.sv:148)
  SF.tx_record prog_tx_observed_v + prog_tx_record (witness record into the d2d TX)
  SF.status    ot_qwen_d2d_status_tx packs epoch16, the six levels and result_* into ONE kind-15 record at its slot
               (rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_services.sv:118-133)

    record_bundles.py audit DIE_V [--lanes fwd_lanes.json] --out audit.json       netlist audit (strict bind); exit 1 FAIL
    record_bundles.py audit-lanes LANES [--land-plan LP] [--fix] --out audit.json  GEN lanes record audit (--fix applies
                                                                                   the GEN fix first: closure + equalize)
    record_bundles.py slice DIE_V | --lanes LANES --out seam.v                     seam slice netlist for the slice bench
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lane_groups as LG  # noqa: E402

D2D, N59, SF = 'd2d_rom', 'native59', 'sys_face'


def _same(src, dst, ports):
    return [(src, p, dst, p) for p in ports]


# bundle -> [(src_inst, src_port, dst_inst, dst_port)]  (dst ports: tools/qwen_split/static_link_bind.py, sys_face_bind.py)
BUNDLES = {
    'C.tx_slot':   [(D2D, 'native_tx_slot', N59, 'tx_slot'), (D2D, 'native_tx_slot_kind', N59, 'tx_slot_kind'),
                    (D2D, 'native_tx_slot_beat', N59, 'tx_slot_beat')],
    'C.rx_record': [(D2D, 'native_rx_v', N59, 'native_rx_v'), (D2D, 'native_rx_slot', N59, 'rx_slot'),
                    (D2D, 'native_rx_slot_kind', N59, 'rx_slot_kind'), (D2D, 'native_rx_slot_beat', N59, 'rx_slot_beat'),
                    (D2D, 'rx_payload', N59, 'native_rx_payload')],
    'C.tx_record': [(N59, 'native_tx_v', D2D, 'native_tx_v'), (N59, 'native_tx_payload', D2D, 'native_tx_payload')],
    'C.x3_record': _same(N59, D2D, ('x3', 'x3_identity', 'x3_generation')),
    'SF.rx_record': _same(D2D, SF, ('rx_payload', 'prog_rx_v', 'prog_auth_slot', 'prog_context_slot', 'prog_witness_slot',
                                    'emb_rx_v', 'emb_rx_slot')),
    'SF.cfg':      _same(SF, D2D, ('cfg_tx_we', 'cfg_rx_we', 'cfg_addr', 'cfg_data')),
    'SF.cal':      _same(SF, D2D, ('cal_start', 'cal_seg')),
    'SF.tx_record': _same(SF, D2D, ('prog_tx_observed_v', 'prog_tx_record')),
    'SF.status':   _same(SF, D2D, ('status_epoch16', 'vm_drained', 'collective_drained', 'collective_busy', 'crom_fault',
                                   'execution_active', 'admit_ready', 'result_v', 'result_done', 'result_fault',
                                   'result_cause', 'result_tag', 'result_gen', 'result_token', 'result_value',
                                   'result_cycles')),
}
# the compiler's own bundle names (layer_compile.py BUNDLES, compute side): every one of them is a bundle here
COMPILER_BUNDLES = ('C.tx_slot', 'C.rx_record', 'C.tx_record', 'C.x3_record')
INDEX = {(s, sp, d): b for b, mem in BUNDLES.items() for s, sp, d, _ in mem}
SINK = {(s, sp, d): dp for b, mem in BUNDLES.items() for s, sp, d, dp in mem}


def fwd_e_est(n):
    """= tools/qwen_rom_fulldie_b3r2.fwd_e_est (pre-STA E of an n-frame forwarded lane)."""
    return max(2, math.ceil((n - 1) / 2) + 1)


def key_of(eps):
    if len(eps) != 2:
        return None
    (s, sp), (d, _) = eps
    return (s, sp.lstrip('*'), d)


def bundle_map(buses):
    """buses: [(bid, eps)] (2-endpoint legs; a fan-out leg <bus>__fo<k> is its own entry).  -> ({bid: bundle},
    problems): a bundle with some members on the die and others missing is a problem (fail closed), a bundle with no
    member at all is not this die."""
    got, seen = {}, {}
    for bid, eps in buses:
        k = key_of(eps)
        if k in INDEX:
            if k in seen:
                return {}, [f'{INDEX[k]}: {k[0]}.{k[1]} -> {k[2]} carried by two buses {seen[k]} / {bid}']
            got[bid], seen[k] = INDEX[k], bid
    problems = []
    for b, mem in BUNDLES.items():
        have = [(s, sp, d) for s, sp, d, _ in mem if (s, sp, d) in seen]
        if have and len(have) != len(mem):
            miss = [f'{s}.{sp}->{d}' for s, sp, d, _ in mem if (s, sp, d) not in seen]
            problems.append(f'{b}: members {miss} not on the die (a bundle lands whole or not at all)')
    return got, problems


_NAME = re.compile(r'^(?:lnk|sf)_(?P<port>\w+?)(?:__fo(?P<fo>\d+))?$')


def bundle_of_bid(bid, src, dst):
    """name fallback for records without endpoint ports (fwd_lanes.json, die.v relay names): lnk_<src port> (static link
    bind) / sf_<port> (sys_face bind) [+ __fo<k> fan-out leg], resolved against the endpoint instances."""
    m = _NAME.match(bid or '')
    if not m or src is None or dst is None:
        return None
    return INDEX.get((src, m.group('port'), dst))


def close_zero_stage(bmap, nframes):
    """GEN step (1): bids of zero-frame members of bundles that have a member with frames (or a pad).  nframes: {bid: n}
    (frames the bus will carry, pads included).  Each returned bid gets a one-frame landing at its sink."""
    by = {}
    for bid, b in bmap.items():
        by.setdefault(b, []).append(bid)
    out = []
    for b, bids in sorted(by.items()):
        if any(nframes.get(x, 0) > 0 for x in bids):
            out += sorted(x for x in bids if nframes.get(x, 0) == 0)
    return out


def plain_pads(bmap, nframes):
    """GEN step (1') without forwarded lanes (plain relays: one edge per frame): {bid: extra frames} to the bundle max."""
    by = {}
    for bid, b in bmap.items():
        by.setdefault(b, []).append(bid)
    pads = {}
    for b, bids in by.items():
        top = max(nframes.get(x, 0) for x in bids)
        pads.update({x: top - nframes.get(x, 0) for x in bids if nframes.get(x, 0) < top})
    return pads


def frame_pads(bmap, nframes, esta=None, D=4):
    """GEN step (1b), forwarded lanes: the bundle's one E is reached by ring wait (landing MCP E_sta + dE) only up to
    E_sta <= D - 1 (lane_groups.equalize, no die STA: one slot of margin); a member further behind gets extra frames
    (half-cycle stations at its sink end) until fwd_e_est(n + p) + E_sta - 2 >= E - (D - 1 - E_sta).  nframes: frames
    after close_zero_stage; esta: {bid: landing MCP (land plan E)}, default 2.  -> {bid: extra frames}."""
    esta = esta or {}
    by = {}
    for bid, b in bmap.items():
        by.setdefault(b, []).append(bid)
    pads = {}
    for b, bids in by.items():
        if not any(nframes.get(x, 0) for x in bids):
            continue
        es = {x: int(esta.get(x, 2)) for x in bids}
        E = max(fwd_e_est(nframes[x]) + es[x] - 2 for x in bids)
        for x in bids:
            need, p = E - (D - 1 - es[x]), 0
            while fwd_e_est(nframes[x] + p) + es[x] - 2 < need:
                p += 1
            if p:
                pads[x] = p
    return pads


def cycles(row):
    """lane cycles a member adds between the two blocks: forwarded lane E + 1 (landing o register), plain relay chain n,
    direct 0 (lane_groups.lane_cycles)."""
    if row is None:
        return 0
    return LG.lane_cycles(row)


def audit_rows(rows, bmap, source=''):
    """rows: {bid: lane row (E for forwarded lanes, n for plain chains)}; a bmap member without a row is a direct wire.
    -> audit record (verdict FAIL when any bundle's members have different lane cycles)."""
    by = {}
    for bid, b in bmap.items():
        by.setdefault(b, []).append(bid)
    out, fails = {}, []
    for b in BUNDLES:
        if b not in by:
            continue
        mem = {}
        for bid in sorted(by[b]):
            r = rows.get(bid)
            kind = 'direct' if r is None else ('fwd' if r.get('E') is not None else 'plain')
            mem[bid] = dict(cycles=cycles(r), kind=kind, n=0 if r is None else r.get('n'),
                            E=None if r is None else r.get('E'), K=None if r is None else r.get('K'),
                            basis=None if r is None else r.get('E_basis_audit'))
        cyc = sorted({v['cycles'] for v in mem.values()})
        # QK-LANDEN / RLYH0-EN 10-19: every forwarded member (hop-0 en registered) carries K + 1 for the SAME arrival edge:
        # compare the source-epoch K (K - lane_groups.hop0_en_reg)
        ks = sorted({(v['K'] - LG.hop0_en_reg(v)) % 8 if v['K'] is not None else None
                     for v in mem.values() if v['kind'] == 'fwd'}, key=str)
        ok = len(cyc) == 1 and len(ks) <= 1
        out[b] = dict(cycles=cyc, consistent=ok, members=mem)
        if not ok:
            fails.append(f'{b}: members arrive on different edges {dict((k, v["cycles"]) for k, v in mem.items())} '
                         f'(kinds {sorted({v["kind"] for v in mem.values()})}' + (f', K {ks}' if len(ks) > 1 else '') + ')')
    return dict(schema='opentallas.qwen_split.record_bundle_audit.v1', source=source,
                rule='one arrival edge per record bundle (valid + every field of one record): lane cycles equal, '
                     'forwarded lanes on one K (tools/qwen_split/record_bundles.py)',
                bundles=out, verdict='FAIL' if fails else 'PASS', fails=fails)


# ------------------------------------------------------------------------------------------------ netlist (die.v) side
INST_LINE = re.compile(r'^\s*(\w+)\s+(\w+)\s*\((.*)\);\s*$')
CONN = re.compile(r'\.(\w+)\(([^()]*)\)')


def _insts(text, names):
    out = {}
    for line in text.splitlines():
        m = INST_LINE.match(line)
        if m and m.group(2) in names:
            out[m.group(2)] = dict(CONN.findall(m.group(3)))
    return out


def netlist_members(die_v_text, bundles=None):
    """-> ({bid: bundle}, {bid: dict(src_net, dst_net, key)}, problems) from the seam instances' pin nets."""
    ins = _insts(die_v_text, {D2D, N59, SF})
    bmap, info, problems = {}, {}, []
    for b, mem in (bundles or BUNDLES).items():
        have = []
        for s, sp, d, dp in mem:
            if s not in ins or d not in ins:
                continue
            sn, dn = ins[s].get(sp), ins[d].get(dp)
            if sn is None or dn is None:
                problems.append(f'{b}: {s}.{sp} -> {d}.{dp} pin not connected in die.v')
                continue
            bid = re.sub(r'__r\d+$', '', dn)[2:] if dn != sn else re.sub(r'__r\d+$', '', sn)[2:]
            bmap[bid] = b
            info[bid] = dict(src_net=sn, dst_net=dn, key=f'{s}.{sp}->{d}.{dp}')
            have.append(bid)
        if have and len(have) != len(mem):
            problems.append(f'{b}: only {len(have)} of {len(mem)} members found in die.v')
    return bmap, info, problems


def rows_from_netlist(die_v, lanes=None, bundles=None):
    """-> (bmap, info, rows, problems): the lane rows of every bundle member as BUILT in die.v (direct members have no
    row); forwarded lanes carry n, K (straps) and E (fwd_lanes.json when given, else E = K: G = R0, E < 8)."""
    import lane_latency_audit as LLA
    text = Path(die_v).read_text()
    bmap, info, problems = netlist_members(text, bundles)
    net = LLA.parse(die_v)
    fl = {r['bid']: r for r in (json.loads(Path(lanes).read_text()).get('lanes', []) if lanes else [])}
    rows = {}
    for bid, i in info.items():
        if i['src_net'] == i['dst_net']:
            continue                                   # direct wire: 0 edges
        L = net.get(bid)
        if L is None:
            problems.append(f'{bid}: sink net {i["dst_net"]} is not a relay chain of {i["src_net"]}')
            continue
        if 'fwd' in L['kind']:
            r = fl.get(bid)
            if r is not None and r.get('E') is not None:
                E, basis = int(r['E']), f'E from {Path(lanes).name}'
            elif L['K'] is not None:
                # QK-LANDEN / RLYH0-EN 10-19: every forwarded landing is strapped K = E + 1 (hop-0 en registered)
                E = (int(L['K']) - LG.hop0_en_reg(L)) % 8
                basis = 'E = landing K straps (no fwd_lanes record: G = R0 assumed, E < 8; K - 1: hop-0 en registered)'
            else:
                problems.append(f'{bid}: landing K straps not on tie cells'); continue
            rows[bid] = dict(bid=bid, n=L['n'], E=E, K=L['K'], E_basis_audit=basis)
        else:
            rows[bid] = dict(bid=bid, n=L['n'], E=None, K=None, E_basis_audit='plain relays: one edge per frame')
    for bid, r in rows.items():
        s_, sp_, d_ = info[bid]['key'].split('->')[0].split('.') + [info[bid]['key'].split('->')[1].split('.')[0]]
        r.update(src=s_, dst=d_, bundle=bmap[bid], E_sta=2)
    return bmap, info, rows, problems


def audit_netlist(die_v, lanes=None):
    bmap, info, rows, problems = rows_from_netlist(die_v, lanes)
    rec = audit_rows(rows, bmap, source=f'{die_v} (netlist)' + (f' + {lanes}' if lanes else ''))
    for b, v in rec['bundles'].items():
        for bid in v['members']:
            v['members'][bid]['pins'] = info[bid]['key']
    if problems:
        rec['fails'] = problems + rec['fails']
        rec['verdict'] = 'FAIL'
    return rec


# ------------------------------------------------------------------------------------------- compute D2D seam stages
# MU-DQ-TXDP 10-19 (COORD 0ki): the compute die's D2D seam STAGES as built (d2d_link_calendar.STAGE_NAMES, compute part),
# from THIS die.v + fwd_lanes.json: the compiler's TXD for the compute master (producer_txd C + PINREG_EXT) and the image's
# RX calendar are functions of them, so the bound TXDP / image are checked against these, never against a hand constant.
# CS_X3S is the d2d_rom.kv_x3_slot -> native59 strobe (one lane, not a record bundle; dv2f18mu lands it E 2 -> 3 cycles).
SEAM_SINGLE = {'C.x3_slot': [(D2D, 'kv_x3_slot', N59, 'kv_x3_slot')]}
SEAM_STAGE_OF = (('CS_TXS', 'C.tx_slot'), ('CS_RXV', 'C.rx_record'), ('CS_RXP', 'C.rx_record'), ('CS_X3S', 'C.x3_slot'),
                 ('SC_TX', 'C.tx_record'), ('SC_X3', 'C.x3_record'))


def seam_stages(die_v, lanes=None):
    """-> (stages {CS_TXS..SC_X3: lane cycles} or None, record, problems).  Fail closed: a missing seam member, a member
    whose lane cannot be read, or a bundle whose members disagree is a problem (no stage is guessed)."""
    bset = {b: BUNDLES[b] for b in COMPILER_BUNDLES}
    bset.update(SEAM_SINGLE)
    bmap, info, rows, problems = rows_from_netlist(die_v, lanes, bset)
    by = {}
    for bid, b in bmap.items():
        by.setdefault(b, []).append(bid)
    per = {}
    for b in bset:
        if b not in by:
            problems.append(f'{b}: no member on the die (compute D2D seam {D2D} / {N59} not found)')
            continue
        cyc = {bid: cycles(rows.get(bid)) for bid in sorted(by[b])}
        if len(set(cyc.values())) != 1:
            problems.append(f'{b}: members arrive on different edges {cyc}')
            continue
        per[b] = dict(cycles=next(iter(cyc.values())), members=cyc)
    st = None if problems else {s: per[b]['cycles'] for s, b in SEAM_STAGE_OF}
    return st, dict(stages=st, bundles=per, source=str(die_v) + (f' + {lanes}' if lanes else ''),
                    rule='record_bundles.seam_stages: lane cycles per seam bundle as built (fwd E + 1, plain n, direct 0)'), problems


def seam_stages_str(st):
    """compute part of a d2d_link_calendar --die-stages string"""
    return ','.join(str(st[s]) for s, _ in SEAM_STAGE_OF)


# ----------------------------------------------------------------------------------------------- GEN lanes record side
def lanes_with_plan(fl, land_plan=None):
    """the GEN's lane E with OT_SPLIT_LAND_PLAN (as lane_groups.py emit): E_sta = plan E, E = fwd_e_est(n) + E_sta - 2,
    calendar = plan K - plan E.  -> (rows, cal, h0)"""
    rows = [dict(r) for r in fl['lanes']]
    cal, h0 = {}, {}
    if land_plan:
        lp = {x['bid']: x for x in land_plan['links']}
        for r in rows:
            x = lp.get(r['bid'])
            if r.get('E') is None or not x or x.get('E') is None:
                continue
            r['E_sta'] = int(x['E'])
            r['E'] = fwd_e_est(r['n']) + r['E_sta'] - 2
            if x.get('K') is not None:
                cal[r['bid']] = (int(x['K']) - int(x['E'])) % 8
            if x.get('h0'):
                h0[r['bid']] = x['h0']
    return rows, cal, h0


def lanes_bundle_map(rows):
    """{bid: bundle} for a lanes record: rows by their 'bundle' field (GEN) or name; a bundle member with no row is a
    direct wire on that die and is named lnk_<port> / sf_<port> (its bus id in the static link / sys_face binds)."""
    bmap, have = {}, set()
    for r in rows:
        b = r.get('bundle') or bundle_of_bid(r['bid'], r.get('src'), r.get('dst'))
        if b:
            bmap[r['bid']] = b
            have.add((r.get('src'), _NAME.match(r['bid']).group('port'), r.get('dst')))
    for b in sorted(set(bmap.values())):
        for s, sp, d, _ in BUNDLES[b]:
            if (s, sp, d) not in have:
                bmap[f'lnk_{sp}' if b.startswith('C.') else f'sf_{sp}'] = b
    return bmap


def _member_of(bid, b):
    port = _NAME.match(bid).group('port')
    return next(((s, d) for s, sp, d, _ in BUNDLES[b] if sp == port), (None, None))


def fix_lanes(rows, bmap, D=4, cal=None, h0=None):
    """the GEN fix on a lanes record (what tools/qwen_rom_fulldie_b3r2.py does on the plans): (1) every direct member of
    a bundle with lanes gets a one-frame landing (n 1, E fwd_e_est(1) + E_sta - 2 = 2); (2) lane_groups.equalize with the
    record bundles as groups (one E, earlier members wait in their ring, K = total E + calendar).  Returns the rows."""
    by = {r['bid']: r for r in rows}
    nfr = {bid: (by[bid]['n'] if bid in by else 0) for bid in bmap}
    for bid in close_zero_stage(bmap, nfr):
        s_, d_ = _member_of(bid, bmap[bid])
        r = dict(bid=bid, src=s_, dst=d_, n=1, E_sta=2, E=fwd_e_est(1), lane='data',
                 E_basis='QXF-SEAMC record bundle: zero-stage member landed with its bundle (one-frame landing)')
        rows.append(r)
        by[bid] = r
    fwd = {r['bid']: r for r in rows if r['bid'] in bmap and r.get('E') is not None}
    pads = frame_pads({b: bmap[b] for b in fwd}, {b: int(r['n']) for b, r in fwd.items()},
                      {b: int(r.get('E_sta') or 2) for b, r in fwd.items()}, D)
    for bid, p in pads.items():
        r = fwd[bid]
        r['n_own'], r['n'] = r['n'], int(r['n']) + p
        r['E'] = fwd_e_est(r['n']) + int(r.get('E_sta') or 2) - 2
        r['E_basis'] = (r.get('E_basis') or '') + f'; QXF-SEAMC: +{p} frames to reach its record bundle E within the ring window'
    for r in rows:
        if r['bid'] in bmap:
            r['bundle'] = bmap[r['bid']]
    data = [r for r in rows if r.get('E') is not None]
    LG.equalize(data, D, cal or {}, h0 or {})
    return rows


# ------------------------------------------------------------------------------------------- seam slice (slice bench)
def _ksel(K, b):
    return 'hi' if (K >> b) & 1 else 'lo'


def emit_lane_lines(bid, n, K, W):
    """the GEN's forwarded-lane instance lines (tools/qwen_rom_fulldie_b3r2.py emit: rly_<bid>_<k>, n_<bid>__r<k>,
    n_fck_* / n_fep_* lane clock / epoch, n_ftk_<bid>_hi/_lo tie nets) with role nets SRC_CK / SRC_EN / DST_CK / DST_RS."""
    L, w = [], f'_{W}_EW_65x30'
    tie = f'.tie_hi(n_ftk_{bid}_hi), .tie_lo(n_ftk_{bid}_lo), ' + \
          ', '.join(f'.k{b}(n_ftk_{bid}_{_ksel(K, b)})' for b in range(3))
    if n == 1:
        L.append(f'  qfd_landh0{w} rly_{bid}_0 (.ck_s(SRC_CK), .en(SRC_EN), .a(n_{bid}), .ck(DST_CK), .rs(DST_RS), {tie}, '
                 f'.b(n_{bid}__r1), .fault(n_flt_{bid}));')
        return L
    L.append(f'  qfd_rlyh0{w} rly_{bid}_0 (.a(n_{bid}), .b(n_{bid}__r1), .eb(n_fep_{bid}__r1), .ck(SRC_CK), '
             f'.ck_o(n_fck_{bid}__h1), .en(SRC_EN));')
    for k in range(1, n - 1):
        L.append(f'  qfd_rlyh{w} rly_{bid}_{k} (.a(n_{bid}__r{k}), .ea(n_fep_{bid}__r{k}), .b(n_{bid}__r{k + 1}), '
                 f'.eb(n_fep_{bid}__r{k + 1}), .ckf(n_fck_{bid}__h{k}), .ck_o(n_fck_{bid}__h{k + 1}));')
    L.append(f'  qfd_landh{w} rly_{bid}_{n - 1} (.a(n_{bid}__r{n - 1}), .ea(n_fep_{bid}__r{n - 1}), {tie}, '
             f'.b(n_{bid}__r{n}), .ck(DST_CK), .ckf(n_fck_{bid}__h{n - 1}), .rs(DST_RS), .fault(n_flt_{bid}));')
    return L


ROLE_SRC = {('qfd_rlyh0_', 'ck'), ('qfd_rlyh0_', 'en'), ('qfd_landh0_', 'ck_s'), ('qfd_landh0_', 'en')}
ROLE_DST = {('qfd_landh_', 'ck'), ('qfd_landh_', 'rs'), ('qfd_landh0_', 'ck'), ('qfd_landh0_', 'rs')}


def slice_netlist(members, lines, widths, name='qxf_seam'):
    """members: [(bid, bundle, src_inst, dst_inst, src_net, dst_net)]; lines: relay instance lines of those bids (the
    GEN's own, as built or emitted); widths: {net: W}.  Role nets are rewritten per lane: the hop-0 clock / gate enable
    -> src_ck / src_en (the source block root + released reset), the landing clock / reset -> <dst>_ck / <dst>_rs (the
    receiving block root + reset).  The cells, frame counts and K straps stay exactly as given."""
    side = {N59: 'n59', SF: 'sf', D2D: 'd2d'}
    out, wires, fam_of = [], {}, lambda mn: next((f for f in ('qfd_rlyh0_', 'qfd_rlyh_', 'qfd_landh0_', 'qfd_landh_')
                                                       if mn.startswith(f)), None)
    by_bid = {}
    for ln in lines:
        m = INST_LINE.match(ln)
        bid = re.sub(r'_\d+$', '', m.group(2))[4:]
        by_bid.setdefault(bid, []).append(m)
    ports, faults, driven = ['output wire lane_fault'], [], set()
    for bid, b, s, d, sn, dn in members:
        W = widths.get(sn, 1)
        ports += [f'input wire [{W - 1}:0] s_{bid}', f'output wire [{W - 1}:0] d_{bid}']
        wires[sn] = W
        if sn == dn:
            out.append(f'  assign d_{bid} = s_{bid};      // {b}: direct wire (0 edges)')
            continue
        wires[dn] = W
        if sn not in driven:                       # fan-out legs share the source pin net (one driver)
            out.append(f'  assign {sn} = s_{bid};')
            driven.add(sn)
        out.append(f'  assign d_{bid} = {dn};')
        for m in sorted(by_bid.get(bid, []), key=lambda m_: int(m_.group(2).rsplit('_', 1)[1])):
            mn, inst, conns = m.group(1), m.group(2), CONN.findall(m.group(3))
            fam = fam_of(mn)
            cc = []
            for p, net in conns:
                if (fam, p) in ROLE_SRC:
                    net = 'src_ck' if p in ('ck', 'ck_s') else 'src_en'
                elif (fam, p) in ROLE_DST:
                    net = f'{side[d]}_ck' if p == 'ck' else f'{side[d]}_rs'
                else:
                    wires.setdefault(net, W if p in ('a', 'b') else 1)
                if p == 'fault':
                    faults.append(net)
                cc.append(f'.{p}({net})')
            out.append(f'  {mn} {inst} ({", ".join(cc)});')
    hdr = [f'module {name} (input wire src_ck, input wire src_en, input wire n59_ck, input wire n59_rs, input wire sf_ck, '
           f'input wire sf_rs, input wire d2d_ck, input wire d2d_rs,', '  ' + ',\n  '.join(ports) + ');']
    decl = [f'  wire [{w - 1}:0] {n};' for n, w in sorted(wires.items())]
    out.append(f'  assign lane_fault = ' + (' | '.join(faults) if faults else "1'b0") + ';   // landing ring faults (L6)')
    return '\n'.join(hdr + decl + out + ['endmodule']) + '\n'


def slice_from_die(die_v_text, bundles=('C.rx_record', 'SF.rx_record')):
    bmap, info, problems = netlist_members(die_v_text)
    if problems:
        raise SystemExit('slice: ' + '; '.join(problems))
    widths = {}
    for m in re.finditer(r'^\s*wire\s*\[(\d+):(\d+)\]\s*(\w+)\s*;', die_v_text, re.M):
        widths[m.group(3)] = abs(int(m.group(1)) - int(m.group(2))) + 1
    mem, lines = [], []
    rly = re.compile(r'^\s*qfd_(?:rlyh0?|landh0?)_\w+\s+rly_(\w+)_(\d+)\s*\(.*\);\s*$')
    want = {bid for bid, b in bmap.items() if b in bundles}
    for ln in die_v_text.splitlines():
        m = rly.match(ln)
        if m and m.group(1) in want:
            lines.append(ln)
    for b in bundles:
        for s, sp, d, dp in BUNDLES[b]:
            bid = next(x for x, i in info.items() if i['key'] == f'{s}.{sp}->{d}.{dp}')
            mem.append((bid, b, s, d, info[bid]['src_net'], info[bid]['dst_net']))
    return mem, lines, widths


def slice_from_lanes(rows, bundles=('C.rx_record', 'SF.rx_record'), bits=None):
    """seam slice of what a GEN emits for the given lanes (fix_lanes output): one forwarded lane per member with its n
    and K, emitted in the GEN's instance form (emit_lane_lines)."""
    by = {r['bid']: r for r in rows}
    mem, lines, widths = [], [], {}
    for b in bundles:
        for s, sp, d, dp in BUNDLES[b]:
            bid = next((x for x, r in by.items() if (r.get('bundle') or bundle_of_bid(x, r.get('src'), r.get('dst'))) == b
                        and _NAME.match(x).group('port') == sp and r.get('src') == s and r.get('dst') == d), None)
            if bid is None:
                bid = f'lnk_{sp}' if d == N59 else f'sf_{sp}'
                if d == SF and sp == 'rx_payload':
                    bid = 'lnk_rx_payload__fo1'
                mem.append((bid, b, s, d, f'n_{bid}', f'n_{bid}'))
                widths[f'n_{bid}'] = (bits or {}).get(sp, 1)
                continue
            r = by[bid]
            W = int(r.get('bits') or (bits or {}).get(sp, 1))
            widths[f'n_{bid}'] = W
            mem.append((bid, b, s, d, f'n_{bid}', f'n_{bid}__r{r["n"]}'))
            lines += emit_lane_lines(bid, int(r['n']), int(r['K']), W)
    return mem, lines, widths


PORT_BITS = dict(rx_payload=548, native_rx_slot_kind=4, native_rx_slot_beat=5)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    a1 = sp.add_parser('audit')
    a1.add_argument('die_v', type=Path)
    a1.add_argument('--lanes', type=Path)
    a1.add_argument('--out', required=True, type=Path)
    a2 = sp.add_parser('audit-lanes')
    a2.add_argument('lanes', type=Path)
    a2.add_argument('--land-plan', type=Path)
    a2.add_argument('--fix', action='store_true')
    a2.add_argument('--equalize-only', action='store_true',
                    help='Q-COLLCAL state: lane_groups.equalize with the bus-name groups only (no record bundles)')
    a2.add_argument('--lanes-out', type=Path)
    a2.add_argument('--out', required=True, type=Path)
    a4 = sp.add_parser('fix-die', help='the GEN fix applied to the lanes of a built die.v -> lanes record (slice input)')
    a4.add_argument('die_v', type=Path)
    a4.add_argument('--out', required=True, type=Path)
    a5 = sp.add_parser('seam-stages', help='MU-DQ-TXDP: compute D2D seam stages of DIE_V (the C part of --die-stages)')
    a5.add_argument('die_v', type=Path)
    a5.add_argument('--lanes', type=Path)
    a5.add_argument('--out', type=Path)
    a3 = sp.add_parser('slice')
    a3.add_argument('die_v', type=Path, nargs='?')
    a3.add_argument('--lanes', type=Path, help='a (fixed) lanes record: emit the GEN form of its lanes')
    a3.add_argument('--mut-k', help='BID:+d -- shift one landing K strap (mutant)')
    a3.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    if a.cmd == 'fix-die':
        bmap, info, rows, problems = rows_from_netlist(a.die_v)
        if problems:
            raise SystemExit('fix-die: ' + '; '.join(problems))
        rows = fix_lanes(list(rows.values()), bmap)
        rec = audit_rows({r['bid']: r for r in rows}, bmap, source=f'{a.die_v} + fix')
        a.out.write_text(json.dumps(dict(schema='opentallas.qwen_split.fwd_lanes.qxf_fix.v1', source=str(a.die_v),
                                         rule='record_bundles.fix_lanes (GEN fix: closure + equalize per bundle)',
                                         D=4, lanes=rows, audit=rec), indent=1) + '\n')
        print(f"FIX_DIE {rec['verdict']} lanes={len(rows)}")
        return 0 if rec['verdict'] == 'PASS' else 1
    if a.cmd == 'seam-stages':
        lanes = a.lanes or (a.die_v.parent / 'fwd_lanes.json' if (a.die_v.parent / 'fwd_lanes.json').exists() else None)
        st, rec, problems = seam_stages(a.die_v, lanes)
        rec['problems'] = problems
        if a.out:
            a.out.write_text(json.dumps(rec, indent=1) + '\n')
        for p_ in problems:
            print('FAIL ' + p_, file=sys.stderr)
        if st is None:
            return 1
        print(seam_stages_str(st))
        return 0
    if a.cmd == 'audit':
        lanes = a.lanes or (a.die_v.parent / 'fwd_lanes.json' if (a.die_v.parent / 'fwd_lanes.json').exists() else None)
        rec = audit_netlist(a.die_v, lanes)
    elif a.cmd == 'audit-lanes':
        fl = json.loads(a.lanes.read_text())
        rows, cal, h0 = lanes_with_plan(fl, json.loads(a.land_plan.read_text()) if a.land_plan else None)
        bmap = lanes_bundle_map(rows)
        if a.fix:
            rows = fix_lanes(rows, bmap, fl.get('D', 4), cal, h0)
        elif a.equalize_only:
            LG.equalize([r for r in rows if r.get('E') is not None], fl.get('D', 4), cal, h0)
        for r in rows:
            if r['bid'] in bmap:
                r.setdefault('bundle', bmap[r['bid']])
        rec = audit_rows({r['bid']: r for r in rows if r['bid'] in bmap}, bmap,
                         source=str(a.lanes) + (f' + {a.land_plan}' if a.land_plan else '') + (' + fix' if a.fix else ''))
        if a.lanes_out:
            a.lanes_out.write_text(json.dumps(dict(fl, lanes=rows, qxf_seamc='fix_lanes' if a.fix else 'as given'), indent=1) + '\n')
    else:
        if a.lanes:
            rows = json.loads(a.lanes.read_text())['lanes']
            if a.mut_k:
                bid, d = a.mut_k.split(':')
                r = next(r for r in rows if r['bid'] == bid)
                r['K'] = (int(r['K']) + int(d)) % 8
            mem, lines, widths = slice_from_lanes(rows, bits=PORT_BITS)
        else:
            mem, lines, widths = slice_from_die(a.die_v.read_text())
        a.out.write_text('`timescale 1ns/1ps\n// GENERATED by tools/qwen_split/record_bundles.py slice from '
                         f'{a.die_v or a.lanes}' + (f' (mutant K {a.mut_k})' if a.mut_k else '') + '\n'
                         + slice_netlist(mem, lines, widths))
        lat = {}
        for bid, b, s, d, sn, dn in mem:
            m = re.search(r'__r(\d+)$', dn)
            ln = next((x for x in lines if f' rly_{bid}_{int(m.group(1)) - 1} ' in x), None) if m else None
            K = None
            if ln:
                ks = dict(CONN.findall(ln))
                K = sum((1 << q) for q in range(3) if ks.get(f'k{q}', '').endswith('_hi'))
            nf = int(m.group(1)) if m else 0
            # QK-LANDEN / RLYH0-EN 10-19: every forwarded landing is strapped K = E + 1 -> its cycles are K (not K + 1)
            lat[bid] = dict(bundle=b, frames=nf, K=K,
                            lane_cycles=(K + 1 - LG.hop0_en_reg({'n': nf})) if K is not None else 0)
        rec = dict(schema='opentallas.qwen_split.record_bundle_slice.v1', out=str(a.out), members=lat)
        print(json.dumps(rec))
        return 0
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(f"RECORD_BUNDLE_AUDIT {rec['verdict']} bundles={len(rec['bundles'])} fails={len(rec['fails'])}"
          + (f" first: {rec['fails'][0]}" if rec['fails'] else ''))
    return 1 if rec['fails'] else 0


if __name__ == '__main__':
    sys.exit(main())
