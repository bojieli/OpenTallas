#!/usr/bin/env python3
"""TOK-DS-GAPS (10-24): arithmetic output words of the slice norm on a DATA cut -- the xfin NX flit (per-beat partial
sums of squares) of the norm-smoke slice, from the layer fixtures' INPUTS through the repository reference model.

Why: the data cuts (cut_0S / cut_0N / cut_7) replayed fault-free but the compiler encoded no output word on them (their
outputs were the off-die RD all-gather and the plan-only NX / XQ exchanges), so no data-cut replay was an exactness check.
The slice the compiler issues the attn norm on (lower_norm_smoke: HLOAD, GAIN, 5 x NORMR, XFIN_GO) emits ONE NX flit
per norm on its line / V faces; its payload is a pure function of the layer-entry state (H, GAIN, delayed pre):

  x   = BF16(seqsum_j pre[j] * h[j])                  hdc_golden_v41.Model.hc_pre (= fixture ops/<s>.hc_pre, asserted)
  p_k = csum(x[e:e+64] * x[e:e+64]),  e = 320 sid + 64 k   hdc_golden_v41.csum, R-ARITH chunk8 (fixture meta arith)
        (ot_s81dv_norm.sv header: each 64-lane beat is an aligned 8-chunk subtree of the golden csum, so the slice's
        ot_hbm_norm_grp produces exactly these per-beat partials; the 80 partials' padded tree = fixture <s>.norm.sumsq,
        asserted)

ABI of the flit (RTL of record, rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv + slice/ot_s81sl_rstop.sv):
  ot_s81dv_xfin collector: col[32 k +: 32] = leaf k partial; inj when leaf NVL-1 arrives; xstop injects the flit on eo
  (hops HE = NS / 2 = 8) and wo (hops HW = NS - 1 - NS / 2 = 7) on the same edge, base b = 5 sid.
  ot_s81sl_rstop nxb(): [0] 1, [3:1] K_NX 3, [8:4] {0, h}, [12:9] sid, [20:13] b, [21 +: 160] d; the snake-end side
  (map_e / map_w) leaves on V (vo = nxb[275:0]); the other on the physical line port (S tier: E port = eo, W port = wo;
  N tier: E port = wo, W port = eo).  A flit is ONE 276-b lane word (width 276): it is whole when lane 0 lands.

Layer-entry residency (the inputs): the entry H (4 BF16 HC copies, rows 0..31), the norm gains (rows 64..79) and the
delayed pre (row GU_FFN 1008) are written into the slice's 5 leaves by native XR CTL target-5 row writes (entry_inputs.py
packing, the production entry path of the first layer; for a later layer they model the state the previous layer left
in the leaf store).  They are emitted as CTL events BEFORE the layer (negative layer cycles, two edges apart, the
qualified target-5 cadence), not as calendar rows: the layer calendar / host boot are unchanged.  The replay drives
them on the cut's line input lanes like every other CTL beat (dv_cut_replay: payload186 events).

Edge: NX_AFTER_LAST_NORMR = edges from the last NORMR CTL event (the compiler's event cycle) to the slice's ro_e / vo
output register taking the flit.  MEASURED on the fc31 RTL (not a model) with every slice region clocked (reclocked
cut_0S, gaps/zero_reclock: the existing zero-data L0 replay, t0 100): the flit landed on w_tvN_s_0S_lnd at bench 468
(lane age 4) and on w_xrE_0S_l0_lnd at 479 (lane age 15) -> output edge 364 = NORMR k4 event 226 + 138.  (The first
calibration, 136, came from the frozen-clock fc31 bench: leaves 0, 1, 3, 4 and the lep K region never clocked.)  The data-independent latency
is a pipeline constant (go_to_partial_normr 115 + leaf relay + xfin collector / xstop + rstop flops).
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]

NX_AFTER_LAST_NORMR_NODSK = 138   # measured on the RECLOCKED cut_0S (zero-data L0 run, gaps/zero_reclock); 136 was the frozen-clock bench
# TOK-DS NORM-DESKEW 10-25 (COORD ruling 01:34): ot_s81sl_xrt aligns the 5 leaf partials on leaf 4's arrival edge with
# static per-leaf deskew registers (depth 4 - k). The old faulting serializer
# restarted on every partial, so its final pass also began on leaf 4's edge.
# Deskew adds four edges from the first command, already covered by the five
# consecutive command dates; it adds none after the last command. Full-cut
# confirmation is pending the inherited builds (the old 138 was measured).
XR_DESKEW = 4
NX_AFTER_LAST_NORMR = NX_AFTER_LAST_NORMR_NODSK
# the plan offsets of the deskew registers: NORMR k reaches the slice exactly k edges after NORMR 0 (one CTL a cycle)
NORMR_OFFSET = (0, 1, 2, 3, 4)
G_SHIFT_MAX = 6           # per-slice shift of the aligned k4 edge (NX words of one stop stay > 6 edges apart)
NS, NVL, K_NX = 16, 5, 3
HE, HW = NS // 2, NS - 1 - NS // 2
ENTRY_CADENCE = 2          # target-5 CTL beats two edges apart (entry_boot.py: the qualified source cadence)
ENTRY_GUARD = 40           # last entry write -> first layer CTL beat of the tier (commit margin before HLOAD)
LANE = 276


def _golden():
    sys.path.insert(0, str(ROOT / 'tools'))
    import hdc_golden_v41 as V
    return V


def _arr(fixtures, rel):
    files = json.loads((Path(fixtures) / 'files.json').read_text())
    spec = files[rel]
    return np.fromfile(Path(fixtures) / rel, dtype=np.dtype(spec['dtype'])).reshape(spec['shape'])


def partials(fixtures, which='attn', h_override=None):
    """the 80 per-beat partial sums of squares (FP32 bit patterns) of the layer's <which> norm input, from io/h_in +
    io/pre_in through the reference model; asserts the model reproduces the fixture's hc_pre and norm.sumsq"""
    fixtures = Path(fixtures)
    meta = json.loads((fixtures / 'meta.json').read_text())
    if meta.get('arith') != 'chunk8':
        raise ValueError(f'fixture arith {meta.get("arith")!r}: the slice partial ABI is the chunk8 csum subtree')
    if which != 'attn':
        raise ValueError('only the attn norm input is a pure function of the layer-entry state (ffn: attn outputs)')
    V = _golden()
    old = V.ARITH
    V.set_arith('chunk8')
    try:
        F = np.float32
        h = _arr(fixtures, 'io/h_in.bin').astype(F) if h_override is None else np.asarray(h_override, F)
        pre = _arr(fixtures, 'io/pre_in.bin').astype(F)
        x = V.to_bf16(V.seqsum([V.mul(pre[j], h[j]) for j in range(4)]))
        ref = _arr(fixtures, f'ops/{which}.hc_pre.bin').astype(F)
        if not np.array_equal(np.asarray(x, F).view(np.uint32), ref.view(np.uint32)):
            raise ValueError(f'reference hc_pre differs from fixture ops/{which}.hc_pre (model / fixture mismatch)')
        sq = V.mul(x, x)
        p = [F(V.csum(sq[64 * v:64 * v + 64])) for v in range(NS * NVL)]
        tot = F(V.split_sum_parts(p))
        ss = _arr(fixtures, f'ops/{which}.norm.sumsq.bin').astype(F)
        if np.asarray(tot, F).view(np.uint32) != ss.view(np.uint32)[0]:
            raise ValueError(f'partial tree {tot} != fixture {which}.norm.sumsq {ss[0]}')
        return [int(np.asarray(v, F).view(np.uint32)) for v in p]
    finally:
        V.set_arith(old)


def nxb(sid, hops, data160, base=None):
    """ot_s81sl_rstop nxb(f, sid_c): the line / V word of an xfin flit; [12:9] = the EMITTING stop's sid strap,
    [20:13] = the flit's base b = NVL * origin sid (forwards keep b, take hops - 1 and the forwarding stop's sid)"""
    b = NVL * sid if base is None else base
    return 1 | K_NX << 1 | (hops & 0xF) << 4 | (sid & 0xF) << 9 | (b & 0xFF) << 13 | data160 << 21


def flit_ports(sid):
    """slice port -> hops of the flit it carries (ot_s81sl_rstop map_e / map_w, tier E / W port roles)"""
    col, tier = sid >> 1, sid & 1
    map_e = col == 0 if tier else col == 7
    map_w = col == 7 if tier else col == 0
    out = {}
    if map_e:
        out['vo'] = HE
    elif map_w:
        out['vo'] = HW
    # physical E port: S tier eo, N tier wo; W port the other
    e_side, w_side = (('wo', 'eo') if tier else ('eo', 'wo'))
    for port, side in (('ro_e', e_side), ('ro_w', w_side)):
        mapped = map_e if side == 'eo' else map_w
        if not mapped:
            out[port] = HE if side == 'eo' else HW
    return out


def side_ports(sid):
    """xfin side -> slice port: 'e' = the snake-forward side (eo / ei), 'w' = the other.  S line W -> E, up column 7's V,
    N line E -> W, down column 0's V (ot_s81sl_rstop header)"""
    col, tier = sid >> 1, sid & 1
    map_e = col == 0 if tier else col == 7
    map_w = col == 7 if tier else col == 0
    e_port = 'vo' if map_e else ('ro_w' if tier else 'ro_e')
    w_port = 'vo' if map_w else ('ro_e' if tier else 'ro_w')
    return {'e': e_port, 'w': w_port}


def snake_index(sid):
    col, tier = sid >> 1, sid & 1
    return col if tier == 0 else NS - 1 - col


def entry_writes(die, fixtures, sid):
    """the slice's layer-entry target-5 rows (entry_inputs.compile_inputs packing, hash-checked inputs)"""
    sys.path.insert(0, str(Path(__file__).parent))
    from entry_inputs import compile_inputs
    img = compile_inputs(die, fixtures)
    return [w for w in img['writes'] if w['sid'] == sid], img['input_sources']


def emit(die, prog, smoke, fixtures, ctl_cycles):
    """entry-state CTL events + the NX flit output words for the norm-smoke slice; replaces the plan-only NX event.
    ctl_cycles = every CTL event cycle already on the smoke slice's tier (the entry writes end ENTRY_GUARD before them).
    Negative control: dv_cut_replay --mutant corrupt:<line lane>:<bit> flips a bit of the first entry write."""
    sl, sid = smoke['slice'], smoke['sid']
    p = partials(fixtures)
    mine = p[NVL * sid:NVL * sid + NVL]
    data = sum(v << (32 * k) for k, v in enumerate(mine))
    writes, sources = entry_writes(die, fixtures, sid)
    port = smoke['ctl_latency']['entry_port']
    last = min(ctl_cycles) - ENTRY_GUARD
    n = len(writes)
    evs = []
    for i, w in enumerate(writes):
        pl = int(w['ctl_payload186'], 16)
        evs.append(dict(cycle=last - ENTRY_CADENCE * (n - 1 - i), inst=sl, port=port, dir='in', kind='CTL',
                        tag=f"entry.{w['region']}.leaf{w['leaf']}.row{w['row']}", payload=f'entry {pl:047x}',
                        payload186=f'{pl:047x}', entry_state=True))
    go_last = max(e['cycle'] for e in prog.events if e.get('inst') == sl and e['kind'] == 'CTL'
                  and str(e.get('tag', '')).startswith('attn.NORMR.k'))
    edge = go_last + NX_AFTER_LAST_NORMR
    prog.events[:] = [e for e in prog.events if not (e.get('inst') == sl and e.get('kind') == 'NX'
                                                       and e.get('tag') == 'attn.partial_roots')]
    for pt, hops in sorted(flit_ports(sid).items()):
        v = nxb(sid, hops, data)
        prog.events.append(dict(cycle=edge, inst=sl, port=pt, ports=[pt], dir='out', kind='NX', tag='attn.partial_roots',
                                width=LANE, valid_bit=0, words=[[edge, f'{v:x}', f'{(1 << LANE) - 1:x}']],
                                payload=f'xfin NX flit sid {sid} hops {hops}: partials ' +
                                        ' '.join(f'{x:08x}' for x in mine),
                                source='hdc_golden_v41 chunk8 csum of BF16(hc_pre(io/h_in, io/pre_in))^2 per 64-beat'))
    prog.events.extend(evs)
    return dict(slice=sl, sid=sid, entry_writes=n, entry_first=evs[0]['cycle'], entry_last=evs[-1]['cycle'],
                entry_sources=sources, nx_edge=edge, nx_after_last_normr=NX_AFTER_LAST_NORMR,
                nx_ports=flit_ports(sid), partials=[f'{x:08x}' for x in mine],
                qualification='NX flit = arithmetic output word of the slice norm (hc_pre mix, square, chunk8 beat '
                              'sums) from layer-entry inputs; rstd / XQ need the 16-slice composition (not compiled)')



# ================================================================================================ 16-slice composition
# TOK-DS-GAPS 10-24: --entry-norm-check all.  Every slice runs the attn norm (HLOAD, GAIN, NORMR k0..k4, XFIN_GO, the
# smoke's arrival-relative pattern) and the 16 xfin flits go round the snake.  ot_s81dv_xstop's schedule contract: every
# stop injects on the SAME cycle (an injection meeting a forward on either output is a sticky fault), so the compiler
# aligns the LAST NORMR (leaf 4: the collector injects when leaf NVL-1's partial lands) of every slice on the smoke
# slice's edge G; each slice's other beats take free line issue edges (one CTL beat a tier line edge, issue domain =
# arrival - ctl_path edges).  Ring words: each stop's output register carries its own flit (edge E0 = G +
# NX_AFTER_LAST_NORMR) and, later, every forward (hops > 1) of a flit that landed on it; a forward leaves NX_FWD edges
# after the flit lands (landed pin -> forwarding output register; CALIBRATION constant per in -> out port class).
# Every stop's flit words are 'out' events: a cut holding the stop is CHECKED on them, a cut holding the receiver is
# DRIVEN with them (dv_cut_replay), so a cut sees real arrivals of the other slices' partials (fixture inputs through
# the reference model) and its own xfin forwards / injects as checked arithmetic words.
# measured (reclocked cut_0S, r3all base: every forward of the 13 driven flits left 6 edges after it landed, values exact)
NX_FWD = {('line', 'line'): 6, ('v', 'line'): 6, ('line', 'v'): 6}


def _port_class(p):
    return 'v' if p in ('vo', 'vi') else 'line'


def _lane0(die, inst, port):
    """the lane carrying bits [275:0] of <inst>.<port> -> (link, dst inst, dst port, age)"""
    cand = [lk for lk, L in die.links.items() if (inst, port) in [tuple(x) for x in L['src']]]
    l0 = [lk for lk in cand if lk.endswith('_l0')]
    if len(l0) == 1:
        cand = l0
    if len(cand) != 1:
        raise ValueError(f'norm_nx: lane 0 of {inst}.{port} ambiguous / absent: {cand}')
    best = (cand[0], die.links[cand[0]])
    lk, L = best
    d = L['dst'][0]
    return lk, d[0], d[1], L['age_edges']


def emit_all(die, prog, smoke, fixtures, D):
    """entry state of all 16 slices + their norm commands + the snake flit words (see the block comment above)"""
    S = die.slices()
    by_sid = {v['sid']: k for k, v in S.items()}
    lat = {sl: D.ctl_path(die, sl)['edges'] for sl in S}
    eport = {sl: D.ctl_path(die, sl)['entry_port'] for sl in S}
    tier = lambda sl: 'N' if sl.endswith('N') else 'S'
    sm = smoke['slice']
    arr = {e['tag']: e['cycle'] for e in prog.events if e.get('inst') == sm and e['kind'] == 'CTL'
           and str(e.get('tag', '')).startswith('attn.')}
    G = arr['attn.NORMR.k4']
    rel = {t: arr[t] - G for t in ('attn.HLOAD', 'attn.GAIN', 'attn.NORMR.k0', 'attn.NORMR.k1', 'attn.NORMR.k2',
                                   'attn.NORMR.k3', 'attn.XFIN_GO')}
    if [rel.get(f'attn.NORMR.k{k}', 0) for k in range(5)] != [NORMR_OFFSET[k] - 4 for k in range(5)]:
        raise ValueError(f'norm_nx all: smoke NORMRs not on the deskew plan offsets {NORMR_OFFSET}: {rel}')
    gap_hg = rel['attn.GAIN'] - rel['attn.HLOAD']
    gap_gn = rel['attn.NORMR.k0'] - rel['attn.GAIN']
    busy = {'S': set(), 'N': set()}
    for e in prog.events:
        if e['kind'] == 'CTL' and e.get('dir') == 'in' and e.get('inst') in S and not e.get('derived_from'):
            busy[tier(e['inst'])].add(e['cycle'] - lat[e['inst']])
    for r in prog.rows:
        if r['eng'] in (D.ENG['VN'], D.ENG['VS']):
            busy['N' if r['eng'] == D.ENG['VN'] else 'S'].add(r['issue'])
    # NORM-DESKEW (10-25): the 5 NORMRs of a slice reach it on 5 CONSECUTIVE edges (the xrt deskew depths are static:
    # leaf k must arrive NORMR_OFFSET[k] edges after leaf 0), so a slice needs the 5 consecutive tier issue edges
    # i4 - 4 .. i4.  With every k4 on one edge G two slices whose CTL path latencies differ by < 5 need overlapping
    # windows (S tier 3S / 5S: 120 / 119, 2S / 6S: 130 / 128; N tier 3N / 5N, 2N / 6N), so a slice may take
    # G + d (0 <= d <= G_SHIFT_MAX): its flit is injected d edges later.  The snake words of all 16 origins are then
    # checked for a shared (stop, port, edge) -- an injection meeting a forward is an xstop sticky fault -- by a
    # depth-first search over the d's (smallest d first, fail closed).
    order = [sl for sl in sorted(S, key=lambda x: S[x]['sid']) if sl != sm]

    def window(sl, d):
        i4 = G + d - lat[sl]
        return [i4 - (4 - k) for k in range(5)]
    p_all = partials(fixtures)
    used_words = {}

    def snake(o, d):
        so = by_sid[o]
        data = sum(v << (32 * k) for k, v in enumerate(p_all[NVL * o:NVL * o + NVL]))
        ws = []
        for side, hops in (('e', HE), ('w', HW)):
            at, port, edge, h = so, side_ports(o)[side], G + d + NX_AFTER_LAST_NORMR, hops
            while True:
                ws.append(dict(inst=at, port=port, edge=edge, sid=S[at]['sid'], hops=h, origin=o, data=data))
                if h <= 1:
                    break
                lk, nxt, inport, age = _lane0(die, at, port)
                land = edge + age
                nsid = S[nxt]['sid']
                oport = side_ports(nsid)[side]
                edge = land + NX_FWD[(_port_class(inport), _port_class(oport))]
                at, port, h = nxt, oport, h - 1
        return ws
    # Solve the fixed-offset windows as a small constraint problem. A fixed SID-order
    # DFS can revisit millions of impossible prefixes; propagate each assignment
    # to every remaining slice and choose the smallest remaining domain first.
    fixed = {(w['inst'], w['port'], w['edge']) for w in snake(S[sm]['sid'], 0)}
    choices, domains = {}, {}
    for sl in order:
        choices[sl] = {}
        for d in range(G_SHIFT_MAX + 1):
            win = set(window(sl, d))
            keys = {(w['inst'], w['port'], w['edge']) for w in snake(S[sl]['sid'], d)}
            if win & busy[tier(sl)] or keys & fixed:
                continue
            choices[sl][d] = (win, keys)
        domains[sl] = set(choices[sl])
    compatible = {}
    for ia, sa in enumerate(order):
        for sb in order[ia + 1:]:
            for da, (wa, ka) in choices[sa].items():
                for db, (wb, kb) in choices[sb].items():
                    ok = not (ka & kb) and not (tier(sa) == tier(sb) and wa & wb)
                    compatible[sa, da, sb, db] = ok
                    compatible[sb, db, sa, da] = ok

    def solve(left, picked):
        if not left:
            return picked
        sa = min(left, key=lambda sl: (len(left[sl]), S[sl]['sid']))
        for da in sorted(left[sa]):
            nxt = {sb: {db for db in ds if compatible[sa, da, sb, db]}
                   for sb, ds in left.items() if sb != sa}
            if any(not ds for ds in nxt.values()):
                continue
            answer = solve(nxt, dict(picked, **{sa: da}))
            if answer is not None:
                return answer
        return None
    shift = solve(domains, {sm: 0})
    if shift is None:
        raise ValueError(f'norm_nx all: no deskew-legal NORMR windows / collision-free snake with G shifts <= {G_SHIFT_MAX}')
    for sl in order:
        busy[tier(sl)].update(window(sl, shift[sl]))
    plan = {}

    def take(t, want, step, lo=None, hi=None):
        e = want
        while e in busy[t] or (lo is not None and e < lo) or (hi is not None and e > hi):
            e += step
            if (step < 0 and lo is not None and e < lo) or (step > 0 and hi is not None and e > hi) or abs(e - want) > 4096:
                raise ValueError(f'norm_nx all: no free issue edge near {want} on tier {t}')
        busy[t].add(e)
        return e
    for sl in order:
        t, win = tier(sl), window(sl, shift[sl])
        P = {f'attn.NORMR.k{k}': win[k] for k in range(5)}
        # GAIN >= gain_slot before the first NORMR, HLOAD >= hload_slot before GAIN (the smoke's VP slot rules, minima)
        P['attn.GAIN'] = take(t, win[0] - gap_gn, -1)
        P['attn.HLOAD'] = take(t, P['attn.GAIN'] - gap_hg, -1)
        P['attn.XFIN_GO'] = take(t, win[4] + rel['attn.XFIN_GO'], +1)
        plan[sl] = P
    # templates / calendar rows / events (same payloads as lower_norm_smoke)
    eps = D.norm_eps_bits()
    GU_ROWS = dict(D.family_lowerings())['gu'].GU_ROWS
    r_pre = GU_ROWS['ffn']
    n_cmd = 0
    for sl, P in plan.items():
        sid, smask = S[sl]['sid'], 1 << S[sl]['sid']
        eng = D.ENG['VN'] if sl.endswith('N') else D.ENG['VS']
        pay = {'attn.HLOAD': D.ctl_payload(smask, 0, 0x1F, D.vp_cmd(D.VP['HLOAD'], a0=0)),
               'attn.GAIN': D.ctl_payload(smask, 0, 0x1F, D.vp_cmd(D.VP['GAIN'], a0=64)),
               'attn.XFIN_GO': D.ctl_payload(smask, 1, 0, D.xfin_go(eps))}
        for k in range(5):
            pay[f'attn.NORMR.k{k}'] = D.ctl_payload(smask, 0, 1 << k, D.vp_cmd(D.VP['NORMR'], a0=r_pre, a1=5 * sid + k, n=3))
        for tag, issue in sorted(P.items(), key=lambda kv: kv[1]):
            ti = prog.template(f'{tag}.{sl}', pay[tag])
            prog.vrow(eng, issue, ti, what=f'norm16 {tag} {sl}')
            prog.events.append(dict(cycle=issue + lat[sl], inst=sl, port=eport[sl], dir='in', kind='CTL', tag=tag,
                                    payload=f'template {ti}', norm16=True))
            n_cmd += 1
    # entry state of every slice: round-robin over the tier's slices, one beat a free issue edge, ending ENTRY_GUARD
    # before the tier's first CTL issue (two-edge per-slice cadence holds: >= 4 slices interleave on a tier)
    from entry_inputs import compile_inputs
    img = compile_inputs(die, fixtures)
    n_entry = 0
    first = {}
    for t in ('S', 'N'):
        sls = sorted([sl for sl in S if tier(sl) == t], key=lambda x: S[x]['sid'])
        per = {sl: [w for w in img['writes'] if w['sid'] == S[sl]['sid']] for sl in sls}
        order = []
        for i in range(max(len(v) for v in per.values())):
            order += [(sl, per[sl][i]) for sl in sls if i < len(per[sl])]
        last = min(busy[t]) - ENTRY_GUARD
        for j, (sl, w) in enumerate(order):
            issue = last - (len(order) - 1 - j)
            pl = int(w['ctl_payload186'], 16)
            prog.events.append(dict(cycle=issue + lat[sl], inst=sl, port=eport[sl], dir='in', kind='CTL',
                                    tag=f"entry.{w['region']}.leaf{w['leaf']}.row{w['row']}", payload=f'entry {pl:047x}',
                                    payload186=f'{pl:047x}', entry_state=True))
        first[t] = last - (len(order) - 1)
        n_entry += len(order)
    # the snake: own flits at E0, forwards after landing
    E0 = G + NX_AFTER_LAST_NORMR
    prog.events[:] = [e for e in prog.events if not (e.get('kind') == 'NX' and e.get('tag') == 'attn.partial_roots')]
    words = []
    for o in range(NS):
        words += snake(o, shift[by_sid[o]])
    for w in words:
        v = nxb(w['sid'], w['hops'], w['data'], base=NVL * w['origin'])
        prog.events.append(dict(cycle=w['edge'], inst=w['inst'], port=w['port'], ports=[w['port']], dir='out', kind='NX',
                                tag=f"attn.nx.o{w['origin']}.h{w['hops']}", width=LANE, valid_bit=0,
                                words=[[w['edge'], f'{v:x}', f'{(1 << LANE) - 1:x}']],
                                payload=f"xfin NX flit origin sid {w['origin']} hops {w['hops']} at {w['inst']}",
                                source='hdc_golden_v41 chunk8 partials of BF16(hc_pre(io/h_in, io/pre_in))^2'))
    # the idle die-link framing of the end-slice link lanes (from die reset; layer_prog/link_frames.py)
    import link_frames
    n_lk = link_frames.emit(die, prog)
    return dict(mode='all', G=G, E0=E0, g_shift={sl: d for sl, d in sorted(shift.items()) if d}, xr_deskew=XR_DESKEW,
                nx_after_last_normr=NX_AFTER_LAST_NORMR, nx_fwd={f'{a}->{b}': v for (a, b), v in NX_FWD.items()},
                norm_commands=n_cmd, entry_writes=n_entry, link_frame_lanes=n_lk, entry_first_issue=first, nx_words=len(words),
                lat=lat, plan={sl: P for sl, P in plan.items()},
                qualification='16-slice NX snake words (own + forwards) from layer-entry inputs; NX_FWD is a calibration '
                              'constant (measured on the cut runs); rstd / XQ words not yet encoded')

if __name__ == '__main__':
    fx = sys.argv[1]
    p = partials(fx)
    print(json.dumps(dict(partials=[f'{x:08x}' for x in p])))
