#!/usr/bin/env python3
"""S81-MUCAL140 (10-20): the S81 multi-user STATIC calendar on the PHYSICAL pinned stage windows (140 stages @ 122
frames, stage_map_f122_140 sha f5608b1e5f2a), replacing the 59 legacy Sxxx groups of dv_mu_calendar.py (Codex 13:04:
no inheritance of 46 AR / 10 MTP).

Inputs (all committed):
  map       results/token_pass/cal2_s81_1020/stage_pick_122/stage_map_f122_140.json (content of every TP4 stage)
  composer  tools/toksim_s81_compose.py on results/token_pass/measured_s81_1019/elements (release-partial, strict
            admission): per-NODE cycles of the static token DAG, captured from the composer itself (no re-pricing)
  cal2      results/token_pass/cal2_s81_1020/fold_cal2.py node deltas (XG5 +2/+1 a field op, COLL7 +4 a coll phase,
            IDX3R +62 an idx.score = measured rg3 req +s+4 / resp +s+1 worst pair 41 + 21 W->E chain, T0 +41) and the
            stage-hop law (N - 120) x (1006 + 2)

Physical stage model (static, linear chain; a token visits R000..R139 in order):
  per layer l, from the composed node cycles (segment span = longest path of the segment's sub-DAG):
    A_l  attention (attn.*, eng.*; includes the index path on the 8 index layers)       -> on the dense stage of l
    D_l  ffn pre-expert (norm, router, top6, shared expert)                              -> on the dense stage of l
    E_l  routed experts, all 6 of the token (experts_gu, swiglu, quant2, down, weights)  -> split over the stages
    C_l  combine allreduce + hc_post                                                     -> on the stage holding
                                                                                            expert (l, 383)
  STATIC RESERVATION: the router picks the experts at run time, so a stage holding N experts of layer l must reserve
    min(6, N) expert slots (AR) -- any routing then fits with no stall.  R(l, N) = E_l * min(6, N) / 6.
  FORWARD-X schedule: the layer input x_l leaves the dense stage right after D_l and is forwarded stage to stage at
    the hop law (the die receives the message, then re-sends it); each expert stage starts its reserved slots on x
    arrival and adds its partial to the partial arriving from upstream (one SU add, ADD) before sending it on.
    Single-user latency per layer = D + (n - 1) hops + R + n ADD + C -- the same hops the cal2 fold charged, plus the
    adds; the stage hold windows are what change.
  ONE JOB CONTEXT a stage (ot_dsdv_fixed_issue): a user holds a stage from its first item start to its last item end.
  MTP (6 verify positions a step, one shared index read): stage step window M_s = 6 W_s - 5 scan_s (scan_s = the
    stage's attn.idx.score cycles, read once a step) -- the S81-BALANCE law, here on physical windows.  Wave term of the
    step = 5 x the worst physical per-position busy max_s (W_s - scan_s) (replaces the composer's legacy wave.busy).
  Links: stage s -> s+1 carries x and the partial: 2 x H_MSG a position (AR), x6 (MTP), per copy pair.
  Head dies (52 other): head ops a position (AR); 6 x head + draft heads (MTP). Host plane HOST_TOK a token a user.
  Copy B: the 8 map-declared dense-owner stages (L2/8/14/20/24/28/32/36) have a second TP4 copy; users are 2-coloured.

Calendar: period P = phase-q4 ceiling of the user's own token (AR) / verify step (MTP); users at phase-q4 shifts
spread over P; the brute-force checker expands every window of every user modulo P on every resource (stage copy,
link copy pair, head, host) and FAULTS on any overlap.  Max users = the largest N with 0 collisions; the checker is
also run at N + 1 (must FAULT) and on an injected shift collision (must FAULT): negative controls.

Grades: node cycles carry the composer grades (80 % measured AR); the stage split, reservation, forward-x adds and the
MTP law are MODEL (exact arithmetic on the map + composed cycles); measured by MU.TOK on RTL.

  dv_mu_calendar_phys.py [--out DIR]          # writes calendar_phys140_{ar,mtp}.json + summary
  dv_mu_calendar_phys.py --check              # recompute and compare
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/s81_dv'))
import dv_mu_calendar as LEG  # noqa: E402  (assign_copies / copy_ok / constants of the legacy calendar)

MAP = ROOT / 'results/token_pass/cal2_s81_1020/stage_pick_122/stage_map_f122_140.json'
OUT = ROOT / 'results/token_pass/mucal140_s81_1020'
F = 1.2e9
TAU = 4.159
PHASE_Q = 4
HOP_SW = 1006 + 2              # switched-leg law (453 inside)
HOP = HOP_SW                   # cal2 STAGE_HOP law (link_rt 652 + KP4 PHY + UCIe + wire, + CAL1 guard/LEPCAP)
SHIFT_SEARCH = False            # STEWARD-TOK: --mtp-shift-search (position hold only)
MTP_HOLD = 'step'               # STEWARD-TOK: MTP stage hold = whole step ('step') or one job a position ('position')
HOP_REF = 120                  # stage hops in the composed DAG record
H_MSG = LEG.H_MSG              # 652 link serialisation a message
LANE_LANDING_CYCLES = 0        # measured sender + receiver region landing cost per crossing
HOST_TOK = LEG.HOST_TOK
SCHEMA = 'opentallas.s81_dv.mu_calendar_phys.v1'
E_OPS = {'ffn.experts_gu', 'ffn.swiglu', 'ffn.route_w', 'ffn.quant2', 'ffn.down', 'ffn.weights'}
C_OPS = {'ffn.combine_allreduce', 'ffn.hc_post'}


def qup(x):
    return -(-int(math.ceil(x)) // PHASE_Q) * PHASE_Q


# ------------------------------------------------------------------------------------------------ S81-CAL241 release
# S81-CAL241 (10-21): the release calendar on the qualified 72-frame map (241 stages / 964 layer dies, ccff664a5, bound
# 483869b91).  Every term below is OFF by default, so the 140 / 141 / sweet records still reproduce (--check SAME);
# --release241 (REL) turns them all on:
#   offchip   direct cabling (owner 10-21, no switch): every crossing's 453-cycle switched leg -> its class's D_cycles_max
#             from results/arch/release_rack_1021/hop_latency.json (claude/rack-1021 @4b528ad2b).  Applied per DAG node
#             (TP4 mesh collectives x their crossings, the composed stage / head hops) and to the stage-hop law HOP.
#   links     S81-LINK5: 5 lane pairs a die = TP4 mesh (3) + a dedicated stage-hop circuit (s_0N pair A -> successor
#             s_0N pair B).  Every message of one user from stage s to s+1 rides that ONE circuit, serialised in send
#             order (x, partial, combined, DENSE2 A->B); the link resource is one per stage boundary and copy pair.
#   land      LINK5 NB 80 / closed land view NS 1: a stage-hop window cuts through into ri (land 0) only if the stage is
#             already this user's: the first beat lands HOP - x_flat (+ RX_JIT) before the receiver's start, so the
#             receiver copy is held from that landing (stage window starts LEAD earlier).  The sender holds its TX (TX
#             send hold) so that no message lands earlier than LEAD before the receiver's start (ALAP slots), so LEAD is
#             the whole landing cost.
#   dense2    DENSE2 map (a_proj rows [0,224) on the A stage, the rest of the dense layer on B): A computes half the
#             a_proj and sends x + its partial (H_MSG + 8 cycles ser, receipt inter_die) to B on the stage circuit; B runs
#             A_l + D_l - a_proj/2 + 8.  Per layer: + 1 hop + 8 cycles (= the capacity receipt's split_layer_adds).
#   attn      attention service variant (S81-SVCFIT: attw time-multiplexed groups): attn.scores / attn.pv node cycles
#             G16 289 / 596 (composer), G8 449 / 756, G4 769 / 1,076 (release die72 = co-located G4 svc_full slot).
#   idx       TOK.DS.BENCH.4.4 / L5B-G7: index readers placed by the HBM PHY -> + IDX_LAT cycles a idx.score job.
#   eng       Source d5e45464e (functional only; ra640a/b physical FAIL): lookup RETURN_AGE640 / II704;
#             eng.hbm_read = 640 and a
#             per-stage Engram resource window of ENG_II a position (x 6 a MTP step) in the brute force.
#   host      S81.HOST option (b) (owner 07:10 10-21): stage dies start jobs from their local calendar (no per-job
#             host / KS frame on the stage circuits); this remains MODEL until the actual HOST descriptor programme
#             is connected. The host plane is the head die's (HOST_TOK a token a user).
REL = dict(offchip='switched', links_serial=False, land=False, attn='G16', idx_lat=0, eng_age=0, eng_ii=0,
           mtp_law='stretch')
REL0 = dict(REL)
REL241 = dict(offchip='direct', links_serial=True, land=True, attn='G4', idx_lat=40, eng_age=640, eng_ii=704,
              mtp_law='pipeline')   # STEWARD-TOK 10-21: causal six-position pipeline (overlap424 repair)
HOPLAT = ROOT / 'results/arch/release_rack_1021/hop_latency.json'
SWITCHED = 453
X_FLAT = 563                   # tb_xdie_s81_2 LEG 1 crossing incl. the die lane legs and the 453 switched leg
RX_JIT = 2
ATTN = {'G16': None, 'G8': {'attn.scores': 449.0, 'attn.pv': 756.0}, 'G4': {'attn.scores': 769.0, 'attn.pv': 1076.0}}
# TP4-mesh crossings a collective node carries (results/rtl/xdie_s81_1019/record.json modelled-PHY / 453 per op)
TP_X = {'attn.a_allgather': 1, 'attn.out_allreduce': 2, 'ffn.router_allgather': 1, 'ffn.combine_allreduce': 2,
        'attn.idx.topk_merge': 1, 'attn.rows_allgather': 1, 'attn.cand.merge': 1, 'head.argmax_merge': 1}
# composed stage-hop crossings (stage_hop class; head.hop = head_hop class); unplaced_hops carries 62
HOP_X = {'substage_hop0': 1, 'substage_hop1': 1, 'unplaced_hops': 62, 'hop_in': 1, 'wave.hop': 1}
DENSE2_SER = 8                 # capacity receipt inter_die: link_busy_add_per_position_cycles (1,856 B a stage, bf16)


def dcyc(cls):
    if REL['offchip'] != 'direct':
        return SWITCHED
    return json.loads(HOPLAT.read_text())['systems']['S81'][cls]['D_cycles_max'] + LANE_LANDING_CYCLES


def x_flat(cls='stage_hop'):
    return X_FLAT - SWITCHED + dcyc(cls)


def node_override(dag, cyc):
    """the REL per-node terms (direct legs, attention variant, index latency, Engram return age) -> (cyc', by-term log)"""
    out, log = dict(cyc), collections.Counter()
    sv_tp, sv_st, sv_hd = SWITCHED - dcyc('tp_mesh'), SWITCHED - dcyc('stage_hop'), SWITCHED - dcyc('head_hop')
    av = ATTN[REL['attn']] or {}
    for n in dag['nodes']:
        i, op = n['id'], (n.get('op') or '')
        c = out[i]
        if op in TP_X and sv_tp:
            out[i] = c - TP_X[op] * sv_tp
        elif op in HOP_X and sv_st:
            out[i] = c - HOP_X[op] * sv_st
        elif op == 'head.hop' and sv_hd:
            out[i] = c - sv_hd
        elif op in av:
            out[i] = av[op]
        elif op == 'attn.idx.score' and REL['idx_lat']:
            out[i] = c + REL['idx_lat']
        elif op == 'eng.hbm_read' and REL['eng_age']:
            out[i] = max(c, float(REL['eng_age']))
        if out[i] != c:
            log[op.split('.')[0] + ':' + op] += (out[i] - c) * (1 if n.get('critical') else 0)
    return out, log


def retime(dag, cyc, cyc2, extra, solve):
    """composer T (max(fixed critical sum, re-solved DAG) + extra terms) before / after a node override"""
    crit = [n['id'] for n in dag['nodes'] if n.get('critical')]
    ex = sum(e['cycles'] for e in extra)
    t0 = max(sum(cyc[i] for i in crit), solve(dag, cyc)[0]) + ex
    t1 = max(sum(cyc2[i] for i in crit), solve(dag, cyc2)[0]) + ex
    return t0, t1


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ------------------------------------------------------------------------------------------------ composed node cycles
ROMOPT = ROOT / 'results/rtl/s81_romopt_1020/c/compose/o3mix_prop_compiled.json.gz'
# S81-ROMOPT-C compose_c.py: the six field ops are substituted where the CALPIPE scenario still carries these values
ROMOPT_OLD = {'attn.wo_b': 901, 'attn.wo_a': 3531, 'ffn.router': 1419, 'ffn.experts_gu': 3680, 'ffn.down': 3084,
              'attn.wq_b': 1987}


def composed(mode='record'):
    """run the composer, capture its per-node cycles (the dict it passes to solve) for both workloads.
    record: release-partial composition of record (cycles.json, 834.0 / 2,649.1)
    romopt: CALPIPE scenario + S81-ROMOPT O1+O2+O3 (gu k2 + down k3 stretch 2) compiled op spans, exactly as
            results/rtl/s81_romopt_1020/c/compose_c.py case o3mix_prop_compiled (1,040.4 / 3,193.4); asserted equal"""
    import gzip
    C = load(ROOT / 'tools/toksim_s81_compose.py', 'toksim_s81_compose')
    cap = {}
    orig, orig_nc = C.solve, C.node_cycles

    def spy(dag, cyc):
        cap[dag['nodes'][0]['id'] + str(len(dag['nodes']))] = (dag, dict(cyc))
        return orig(dag, cyc)
    C.solve = spy
    hits = collections.Counter()
    if mode == 'romopt':
        ref = json.loads(gzip.decompress(ROMOPT.read_bytes()))
        v = ref['rate3']['op_values']

        def nc(n, ov):
            cyc, how = orig_nc(n, ov)
            op = n.get('op')
            if cyc is not None and op in v and abs(cyc - ROMOPT_OLD[op]) < 0.01:
                hits[op] += 1
                return float(v[op]), how
            return cyc, how
        C.node_cycles = nc
    try:
        r = C.build(C.OUT / 'elements', 'calpipe' if mode == 'romopt' else None)
    finally:
        C.solve, C.node_cycles = orig, orig_nc
    if mode == 'romopt':
        assert dict(hits) == ref['rate3']['substitutions'], (dict(hits), ref['rate3']['substitutions'])
        committed = ref
    else:
        committed = json.loads((C.OUT / 'cycles.json').read_text())
    for wl in ('ar', 'mtp'):
        assert r['workloads'][wl]['T_cycles'] == committed['workloads'][wl]['T_cycles'], wl
    dags = {}
    for wl, p in C.DAGS.items():
        n = json.loads(p.read_text())
        key = n['nodes'][0]['id'] + str(len(n['nodes']))
        dags[wl] = cap[key] if key in cap else None
    # both workloads have distinct node counts; fall back to order if not
    if None in dags.values():
        vals = list(cap.values())
        dags = dict(ar=vals[0], mtp=vals[1])
    return r, dags


def cal2_delta(n, F2):
    return sum(F2.node_delta(n, True).values())


def seg_of(n):
    op = n.get('op') or ''
    if n.get('cls') == 'hop' or 'substage_hop' in op:
        return None
    if op in E_OPS:
        return 'E'
    if op in C_OPS:
        return 'C'
    if op.startswith('ffn.'):
        return 'D'
    if op.startswith(('attn.', 'eng.')):
        return 'A'
    return None


APROJ = {}                   # layer -> attn.a_proj cycles + its start offset in the A segment (DENSE2)
IVS = {}                     # (layer, segment) -> [(start offset, end offset, engine class)] of the segment's nodes


def layer_segments(dag, cyc, F2, extra):
    """per layer: A / D / E / C spans (longest path of each segment's sub-DAG) + the idx.score scan cycles"""
    IVS.clear()
    APROJ.clear()
    nodes = {n['id']: n for n in dag['nodes']}
    c = {i: cyc[i] + cal2_delta(nodes[i], F2) for i in nodes}
    seg = collections.defaultdict(list)
    for n in dag['nodes']:
        L = n.get('layer')
        s = seg_of(n)
        if isinstance(L, int) and 0 <= L < 40 and s and not n['id'].startswith('V.'):
            seg[(L, s)].append(n['id'])
    pred = collections.defaultdict(list)
    for e in dag['edges']:
        pred[e['dst']].append((e['src'], float(e.get('cycles') or 0)))
    out = {}
    for (L, s), ids in seg.items():
        S = set(ids)
        end = {}

        def fin(i):
            if i in end:
                return end[i]
            st = max([fin(p) + w for p, w in pred[i] if p in S] or [0.0])
            end[i] = st + c[i]
            return end[i]
        span = max(fin(i) for i in ids)
        out.setdefault(L, {})[s] = span
        IVS[(L, s)] = sorted((end[i] - c[i], end[i], nodes[i].get('cls') or 'su') for i in ids if c[i] > 0)
        ap = [i for i in ids if nodes[i].get('op') == 'attn.a_proj']
        if s == 'A' and ap:                           # DENSE2: the A stage's half a_proj (prefix = its start offset)
            APROJ[L] = dict(cycles=c[ap[0]], prefix=end[ap[0]] - c[ap[0]])
    scan = collections.Counter()
    for n in dag['nodes']:
        if isinstance(n.get('layer'), int) and n['id'].endswith('attn.idx.score') and not n['id'].startswith('V.'):
            scan[n['layer']] = max(scan[n['layer']], c[n['id']])
    for t in extra:                                   # priced per-layer terms (p4l DV deltas) -> the dense segment
        if t['kind'] == 'layer' and t['slot'].startswith('L'):
            L = int(t['slot'][1:].split('.')[0])
            if L in out:
                a0 = out[L]['A']
                out[L]['A'] += t['cycles']
                if t['cycles'] > 0:                   # unknown engine: blocks every engine class (conservative)
                    IVS[(L, 'A')].append((a0, out[L]['A'], 'ALL'))
    head = sum(c[i] for i, n in nodes.items() if (n.get('op') or '').startswith('head.') and n.get('critical'))
    return out, dict(scan), head, c


# ------------------------------------------------------------------------------------------------ single-user timeline
def stage_items(st, dsplit=False):
    d = st['dense_layer']
    tail = [('X', l, b - a + 1) for l, a, b in st['experts'] if d is None or l < d]
    if dsplit:
        tail = [y for l in st.get('d_here', []) for y in [('D2', l, None)] + [x for x in tail if x[1] == l]] + \
            [x for x in tail if x[1] not in st.get('d_here', [])]
    head = [('X', l, b - a + 1) for l, a, b in st['experts'] if d is not None and l >= d]
    return tail + ([('D', d, None)] if d is not None else []) + head


def timeline(stages, seg, add, embed_end=0.0, alap=False, dsplit=False, causal_integer=False):
    """forward-x single-user schedule: per stage [start, end] hold window, item log, chain end; + legacy-equivalent"""
    edge = math.ceil if causal_integer else (lambda value: value)
    # Quantise durations before propagation: rounding final timestamps can move an
    # arrival ahead of its producer or lose a cycle at each fractional segment.
    if causal_integer:
        seg = {layer: {kind: math.ceil(cycles) for kind, cycles in parts.items()}
               for layer, parts in seg.items()}
        add, embed_end = math.ceil(add), math.ceil(embed_end)
    last_stage = {}
    for i, st in enumerate(stages):
        for l, a, b in st['experts']:
            if b == 383:
                last_stage[l] = i
    if dsplit:                                   # S81-SWEET --dsplit: D_l on the first downstream stage with l experts
        seen = set()
        for i, st in enumerate(stages):
            st['d_here'] = []
            for l, a, b in st['experts']:
                if l not in seen and (st['dense_layer'] is None or l < st['dense_layer']):
                    seen.add(l)
                    st['d_here'].append(l)
        assert seen == set(range(40)), 'dsplit: a layer has no expert stage after its dense stage'
    x_arr, p_arr, comb = {}, {}, {}          # per layer: x arrival at the current stage, partial arrival, combined out
    d2_out, d2_arr = {}, {}                  # DENSE2: A-half done (x + a_proj partial leaves A) / its arrival at B
    win, log = [], []
    links = []
    for i, st in enumerate(stages):
        cur, first = None, None
        part_out = {}
        for kind, l, N in stage_items(st, dsplit):
            if kind == 'D2':
                s0 = max(cur or 0.0, x_arr[l])
                x_arr[l] = s0 + seg[l]['D']
                e0 = x_arr[l]
                busy = [(s0 + a, s0 + b, k) for a, b, k in IVS.get((l, 'D'), [])]
                log.append(dict(stage=st['stage'], item=f'ffn pre-expert L{l} (dsplit)', start=s0, end=e0, busy=busy))
                first = s0 if first is None else first
                cur = e0
                continue
            if kind == 'D' and st.get('dense_split2') == 'A':
                # DENSE2 A half: a_proj rows [0,224) (half the a_proj after the norm prefix); x + partial go to B
                ready = comb.get(l - 1, embed_end) if l > 0 else embed_end
                s0 = max(cur or 0.0, ready)
                e0 = edge(s0 + edge(APROJ[l]['prefix']) + edge(0.5 * APROJ[l]['cycles']))
                d2_out[l] = e0
                log.append(dict(stage=st['stage'], item=f'dense L{l} A half (a_proj rows [0,224))', start=s0, end=e0,
                                busy=[(s0, e0, 'field')]))
            elif kind == 'D' and st.get('dense_split2') == 'B':
                # DENSE2 B half: the rest of the dense layer once x + the A partial landed (+ 8 cycles ser)
                s0 = max(cur or 0.0, d2_arr[l])
                xl = edge(s0 + edge(seg[l]['A'] + seg[l]['D'] - 0.5 * APROJ[l]['cycles']) + DENSE2_SER)
                x_arr[l] = xl
                e0 = xl
                busy = [(s0 + a, s0 + b, k) for a, b, k in IVS.get((l, 'A'), [])] + \
                       [(s0 + seg[l]['A'] + a, s0 + seg[l]['A'] + b, k) for a, b, k in IVS.get((l, 'D'), [])]
                log.append(dict(stage=st['stage'], item=f'dense L{l} B half', start=s0, end=e0, busy=busy))
            elif kind == 'D':
                ready = comb.get(l - 1, embed_end) if l > 0 else embed_end
                s0 = max(cur or 0.0, ready)
                xl = s0 + seg[l]['A'] + (0.0 if dsplit else seg[l]['D'])
                x_arr[l] = xl                               # x leaves now (forwarded to the next stage below)
                e0 = xl
                busy = [(s0 + a, s0 + b, k) for a, b, k in IVS.get((l, 'A'), [])] + \
                       ([] if dsplit else
                        [(s0 + seg[l]['A'] + a, s0 + seg[l]['A'] + b, k) for a, b, k in IVS.get((l, 'D'), [])])
                log.append(dict(stage=st['stage'], item=f'dense L{l}', start=s0, end=e0, busy=busy))
            else:
                R = edge(seg[l]['E'] * min(6, N) / 6.0)
                pin = p_arr.get(l)
                s0 = max(cur or 0.0, x_arr[l])
                if alap and pin is not None:          # just-in-time slots: end as the upstream partial lands (same out)
                    s0 = edge(max(s0, pin - R))
                e = s0 + R
                po = (max(e, pin) + add) if pin is not None else e
                part_out[l] = po
                e0 = po
                # engine classes: the expert slots hold field + su for the whole reservation; the add is an SU op;
                # the combine holds coll + su (conservative unions)
                busy = [(s0, e, 'field'), (s0, e, 'su')] + ([(po - add, po, 'su')] if pin is not None else [])
                if last_stage.get(l) == i:
                    comb[l] = po + seg[l]['C']
                    busy += [(po, comb[l], 'coll'), (po, comb[l], 'su')]
                    e0 = comb[l]
                log.append(dict(stage=st['stage'], item=f'experts L{l} x{N} (slots {min(6, N)})', start=s0, end=e0,
                                busy=busy))
            first = s0 if first is None else first
            cur = e0
        win.append((first, cur))
        # messages to the next stage (one per layer still open downstream): the layer input x (unless the next stage
        # computes it), the running partial, and the combined output when the next layer's dense stage is downstream
        if i + 1 < len(stages):
            nxt = stages[i + 1]
            nl = {l for l, _, _ in nxt['experts']}
            msgs = []                                # (ready, order, label, length, destination dict, layer)
            for l in sorted(nl):
                if l in x_arr and nxt['dense_layer'] != l:
                    msgs.append((x_arr[l], 0, f'x L{l}', H_MSG, x_arr, l))
                if l in part_out and last_stage.get(l) != i:
                    msgs.append((part_out[l], 1, f'partial L{l}', H_MSG, p_arr, l))
            for l, t in list(comb.items()):
                if last_stage.get(l) == i and l + 1 < 40 and stages[i]['dense_layer'] != l + 1:
                    msgs.append((t, 2, f'combined L{l}', H_MSG, comb, l))
            if st.get('dense_split2') == 'A' and nxt.get('dense_split2') == 'B' and st['dense_layer'] in d2_out:
                l = st['dense_layer']
                msgs.append((d2_out[l], 3, f'x + a_proj partial L{l} (DENSE2 A->B)', H_MSG + DENSE2_SER, d2_arr, l))
            free = -1e18
            for t, _, what, ln, dst, l in (sorted(msgs, key=lambda m: (m[0], m[1])) if REL['links_serial'] else msgs):
                s0 = edge(max(t, free) if REL['links_serial'] else t)     # LINK5: one stage-hop circuit, send order
                free = s0 + ln
                links.append((i, s0, what, ln))
                dst[l] = s0 + HOP
    chain = comb[39] - embed_end
    legacy = sum(seg[l]['A'] + seg[l]['D'] + seg[l]['E'] + seg[l]['C'] for l in range(40)) + (len(stages) - 1) * HOP
    return win, log, links, chain, legacy


def timeline_positions(stages, seg, add, embed_end, alap, scan, positions=6):
    """STEWARD-TOK 10-21: causal PIPELINED MTP step (the same-user overlap424 repair of 6f8bbf5c4).

    6f8bbf5c4 serialised each stage circuit for ONE position (AR message lengths) and then stretched every message to
    6 x H_MSG in the checker, so x L0 [18136,22048) and partial L0 [21624,25536) of the SAME user overlapped (424
    cycles, 200 / 240 circuits).  Here every one of the six verify positions is propagated through the DAG:
      * a stage runs position-major (all its items for position p, then p + 1: ONE job context, the MTP law
        6 W - 5 scan): positions p >= 1 skip the shared index read (scan_l on the dense item);
      * each position's messages (x, partial, combined, DENSE2 A->B) are real H_MSG messages on the ONE LINK5 stage
        circuit, serialised in send order across ALL positions and message kinds (free pointer carried);
      * every arrival is the serialised send + HOP, and the downstream item of that position waits for it, so a TX
        delay propagates to the receiver's stage window, its own sends and the head (dependency-propagated).
    Integer causality: durations are ceiled before propagation (as Codex 181a2cdce).
    Returns per stage: hold window (first start, last end) + per-position (start, end) + per-position dense start;
    links (stage, position, start, label, length); per-position chain end (combined L39 at its last stage)."""
    assert not any(st.get('d_here') for st in stages), 'positions timeline: --dsplit not supported'
    seg = {layer: {kind: math.ceil(cycles) for kind, cycles in parts.items()} for layer, parts in seg.items()}
    add, embed_end = math.ceil(add), math.ceil(embed_end)
    last_stage = {}
    for i, st in enumerate(stages):
        for l, a, b in st['experts']:
            if b == 383:
                last_stage[l] = i
    x_arr, p_arr, comb, d2_arr = {}, {}, {}, {}     # keyed (position, layer)
    out, links = [], []
    for i, st in enumerate(stages):
        cur, first = None, None
        part_out, d2_out = {}, {}
        pos_win, dense_start, msgs = [], {}, []
        for p in range(positions):
            pfirst = None
            for kind, l, N in stage_items(st):
                sc = math.ceil(scan.get(l, 0.0)) if p else 0      # shared index read: position 0 only
                if kind == 'D' and st.get('dense_split2') == 'A':
                    ready = comb.get((p, l - 1), embed_end) if l > 0 else embed_end
                    s0 = max(cur or 0, ready)
                    e0 = s0 + math.ceil(APROJ[l]['prefix']) + math.ceil(0.5 * APROJ[l]['cycles'])
                    d2_out[(p, l)] = e0
                elif kind == 'D' and st.get('dense_split2') == 'B':
                    s0 = max(cur or 0, d2_arr[(p, l)])
                    e0 = s0 + math.ceil(seg[l]['A'] - sc + seg[l]['D'] - 0.5 * APROJ[l]['cycles']) + DENSE2_SER
                    x_arr[(p, l)] = e0
                    dense_start[p] = s0
                elif kind == 'D':
                    ready = comb.get((p, l - 1), embed_end) if l > 0 else embed_end
                    s0 = max(cur or 0, ready)
                    e0 = s0 + seg[l]['A'] - sc + seg[l]['D']
                    x_arr[(p, l)] = e0
                    dense_start[p] = s0
                else:
                    R = math.ceil(seg[l]['E'] * min(6, N) / 6.0)
                    pin = p_arr.get((p, l))
                    s0 = max(cur or 0, x_arr[(p, l)])
                    if alap and pin is not None:
                        s0 = max(s0, pin - R)
                    e = s0 + R
                    po = (max(e, pin) + add) if pin is not None else e
                    part_out[(p, l)] = po
                    e0 = po
                    if last_stage.get(l) == i:
                        comb[(p, l)] = po + seg[l]['C']
                        e0 = comb[(p, l)]
                first = s0 if first is None else first
                pfirst = s0 if pfirst is None else pfirst
                cur = e0
            pos_win.append((pfirst, cur))
            if i + 1 < len(stages):
                nxt = stages[i + 1]
                nl = {l for l, _, _ in nxt['experts']}
                for l in sorted(nl):
                    if (p, l) in x_arr and nxt['dense_layer'] != l:
                        msgs.append((x_arr[(p, l)], p, 0, f'x L{l} pos {p}', H_MSG, x_arr, (p, l)))
                    if (p, l) in part_out and last_stage.get(l) != i:
                        msgs.append((part_out[(p, l)], p, 1, f'partial L{l} pos {p}', H_MSG, p_arr, (p, l)))
                for (q, l), t in list(comb.items()):
                    if q == p and last_stage.get(l) == i and l + 1 < 40 and st['dense_layer'] != l + 1:
                        msgs.append((t, p, 2, f'combined L{l} pos {p}', H_MSG, comb, (p, l)))
                if st.get('dense_split2') == 'A' and nxt.get('dense_split2') == 'B' and (p, st['dense_layer']) in d2_out:
                    l = st['dense_layer']
                    msgs.append((d2_out[(p, l)], p, 3, f'x + a_proj partial L{l} pos {p} (DENSE2 A->B)',
                                 H_MSG + DENSE2_SER, d2_arr, (p, l)))
        free = -10 ** 18
        for t, p, _, what, ln, dst, key in sorted(msgs, key=lambda m: (m[0], m[1], m[2])):
            s0 = max(t, free)                       # LINK5: ONE stage-hop circuit, send order, all positions
            free = s0 + ln
            links.append((i, p, s0, what, ln))
            dst[key] = s0 + HOP
        out.append(dict(first=first, last=cur, positions=pos_win, dense_start=dense_start))
    chain_end = [comb[(p, 39)] for p in range(positions)]
    return out, links, chain_end


def mtp_pipeline_graph(model, tl, links, chain_end, hop_head, lead):
    """six-position pipelined step graph for windows(): stage hold windows (one job context, LINK5 land-0 lead on the
    receivers), every position's message on its stage circuit, Engram windows a position, heads a position + draft."""
    stages = []
    for i, (q, w) in enumerate(zip(model['stages'], tl)):
        ld = lead if i else 0
        eng = []
        if q.get('eng_off') is not None and REL['eng_ii']:
            eng = [w['dense_start'][p] for p in sorted(w['dense_start'])]
        stages.append(dict(stage=q['stage'], owner_start=w['first'] - ld, owner_end=w['last'],
                           position_windows=[list(x) for x in w['positions']], eng_starts=eng))
    heads, t = [], 0
    for p, c in enumerate(chain_end):
        h0 = max(c + hop_head, t)
        t = h0 + model['head_ar']
        heads.append([h0, t])
    draft = [t, t + model['draft_tail']]
    host = [heads[0][0], heads[0][0] + HOST_TOK * len(chain_end)]
    end = max(draft[1], host[1])
    return dict(schema='opentallas.s81_mtp.pipeline.v1', positions=len(chain_end), stages=stages,
                links=[dict(sender_index=i, position=p, send_start=s, send_end=s + ln, label=what)
                       for i, p, s, what, ln in links],
                heads=heads, draft=draft, host=host, step_end=end, chain_end=chain_end,
                law='position-major stages (6 W - 5 scan), every position message serialised on its LINK5 circuit and '
                    'propagated (arrival = send + HOP) to the receiving item; heads a position, then the draft tail',
                qualification='MODEL (exact integer causal arithmetic on composed node cycles); RTL calendar programme '
                              'emission pending')


# ------------------------------------------------------------------------------------------------ calendar + checker
def position_barrier_graph(model):
    """Conservative six-position graph, with an explicit global completion barrier.

    Every position executes the complete AR graph, including its scan. There is
    no scan-reuse or pipeline credit. This is a scheduler MODEL requiring compiler
    emission; it does not qualify the existing RTL calendar programmes.
    """
    base = windows(model, 0, 0, 'ar', {})
    receive_end = max(t + HOP for _, t, _, _ in model['links'])
    actual_end = max([end for _, _, end in base] + [receive_end])
    span = qup(max(model['T_ar'], actual_end))
    draft = model['draft_tail']  # rounded from draft nodes themselves, never subtract rounded head totals
    lead = math.ceil(HOP - x_flat('stage_hop') + RX_JIT) if REL['land'] else 0
    owners = []
    for i, q in enumerate(model['stages']):
        arrivals = [t + HOP - lead for j, t, _, _ in model['links'] if j + 1 == i]
        tx_ends = [t + length for j, t, _, length in model['links'] if j == i]
        owners.append((min([q['t']] + arrivals), max([q['t'] + q['occ']] + tx_ends)))
    positions = []
    for position in range(6):
        offset = position * span
        positions.append(dict(position=position, start=offset, barrier=offset + span,
            stages=[dict(stage=q['stage'], owner_start=offset + owners[i][0],
                         owner_end=offset + owners[i][1]) for i, q in enumerate(model['stages'])],
            links=[dict(sender_index=i, sender=model['stages'][i]['stage'], receiver=model['stages'][i + 1]['stage'],
                        label=label, send_start=offset + t, send_end=offset + t + length,
                        receive_first=offset + t + HOP - lead, receive_complete=offset + t + HOP)
                   for i, t, label, length in model['links']],
            head=dict(start=offset + model['head_t'], end=offset + model['head_t'] + model['head_ar'])))
    return dict(schema='opentallas.s81_mtp.position_barriers.v1', positions=positions,
                position_span=span, actual_ar_resources_end=actual_end,
                ar_composer_end=model['T_ar'], terminal_guard=span - actual_end,
                draft_start=6 * span, draft_end=6 * span + draft,
                host_tail_end=6 * span + draft + HOST_TOK,
                step_cycles=qup(6 * span + draft + HOST_TOK),
                qualification='MODEL only; compiler must emit position completion barriers and draft tail',
                integer_causality='ceil segment durations before stage/compute/send/arrival propagation',
                scan_reuse=False, pipeline_overlap=False)


def windows(model, user, shift, kind, col):
    mt = kind == 'mtp'
    pipe = model.get('mtp_pipeline')
    if mt and pipe:
        ws = []
        for i, w in enumerate(pipe['stages']):
            st = model['stages'][i]
            cp = col.get(st['stage'], {}).get(user, 'A') if st['copies'] > 1 else 'A'
            if pipe.get('hold') == 'position':     # one job a position: the copy is free between positions
                ld = pipe['lead'] if i else 0
                ws.extend((f"{st['stage']}.{cp}", shift + a, shift + b)       # land lead; touching jobs merge
                          for a, b in merge_iv([(a - ld, b) for a, b in w['position_windows']]))
            else:
                ws.append((f"{st['stage']}.{cp}", shift + w['owner_start'], shift + w['owner_end']))
            ws.extend((f"eng.{st['stage']}.{cp}", shift + e, shift + e + REL['eng_ii']) for e in w['eng_starts'])
        for m in pipe['links']:
            i = m['sender_index']
            a, b = model['stages'][i:i + 2]
            ca = col.get(a['stage'], {}).get(user, 'A') if a['copies'] > 1 else 'A'
            cb = col.get(b['stage'], {}).get(user, 'A') if b['copies'] > 1 else 'A'
            ws.append((f"link.{a['stage']}.{ca}-{b['stage']}.{cb}", shift + m['send_start'], shift + m['send_end']))
        ws.extend(('head', shift + a, shift + b) for a, b in pipe['heads'] + [pipe['draft']])
        ws.append(('host', shift + pipe['host'][0], shift + pipe['host'][1]))
        return [w for w in ws if w[2] > w[1]]
    graph = model.get('mtp_position_graph')
    if mt and graph:
        ws = []
        for position in graph['positions']:
            for i, owner in enumerate(position['stages']):
                st = model['stages'][i]
                cp = col.get(st['stage'], {}).get(user, 'A') if st['copies'] > 1 else 'A'
                ws.append((f"{st['stage']}.{cp}", shift + owner['owner_start'], shift + owner['owner_end']))
            for message in position['links']:
                i = message['sender_index']
                a, b = model['stages'][i:i + 2]
                ca = col.get(a['stage'], {}).get(user, 'A') if a['copies'] > 1 else 'A'
                cb = col.get(b['stage'], {}).get(user, 'A') if b['copies'] > 1 else 'A'
                ws.append((f"link.{a['stage']}.{ca}-{b['stage']}.{cb}",
                           shift + message['send_start'], shift + message['send_end']))
            ws.extend(w for w in windows(model, user, shift + position['start'], 'ar', col)
                      if w[0].startswith(('eng.', 'head', 'host')))
        ws.append(('head', shift + graph['draft_start'], shift + graph['draft_end']))
        ws.append(('host', shift + graph['draft_end'], shift + graph['host_tail_end']))
        return [w for w in ws if w[2] > w[1]]
    ws = []
    for i, st in enumerate(model['stages']):
        cp = col.get(st['stage'], {}).get(user, 'A') if st['copies'] > 1 else 'A'
        L = st['step'] if mt else st['occ']
        ws.append((f"{st['stage']}.{cp}", shift + st['t'], shift + st['t'] + L))
    for i, t, what, ln in model['links']:
        a, b = model['stages'][i], model['stages'][i + 1]
        ca = col.get(a['stage'], {}).get(user, 'A') if a['copies'] > 1 else 'A'
        cb = col.get(b['stage'], {}).get(user, 'A') if b['copies'] > 1 else 'A'
        L = ln * (6 if mt else 1)
        ws.append((f"link.{a['stage']}.{ca}-{b['stage']}.{cb}", shift + t, shift + t + L))
    for st in model['stages']:                    # Engram lookup engine: one window in flight, II ENG_II a position
        if st.get('eng_off') is not None and REL['eng_ii']:
            cp = col.get(st['stage'], {}).get(user, 'A') if st['copies'] > 1 else 'A'
            e0 = shift + st['t'] + st['eng_off']
            ws.append((f"eng.{st['stage']}.{cp}", e0, e0 + REL['eng_ii'] * (6 if mt else 1)))
    h0 = shift + model['head_t']
    ws.append(('head', h0, h0 + (model['head_mtp'] if mt else model['head_ar'])))
    ws.append(('host', h0, h0 + HOST_TOK * (6 if mt else 1)))
    return ws


def interval_collisions(by, P):
    """Exact half-open circuit/engine occupancy, including a sender's own messages.

    Compare distinct reservations against adjacent periods, and each reservation
    against its own next period. Equal user identity never exempts occupancy.
    """
    bad = []
    for resource, reservations in by.items():
        rows = sorted(reservations)
        for i, (a, length, user) in enumerate(rows):
            if length > P:
                bad.append(dict(resource=resource, users=[user, user], overlap=length - P,
                                intervals=[[a, a + length], [a + P, a + P + length]],
                                same_user=True, periodic_self=True))
            for b, length2, user2 in rows[i + 1:]:
                for cycle in (-P, 0, P):
                    start = max(a, b + cycle)
                    end = min(a + length, b + cycle + length2)
                    if end > start:
                        bad.append(dict(resource=resource, users=[user, user2],
                                        overlap=round(end - start, 6),
                                        intervals=[[a, a + length], [b + cycle, b + cycle + length2]],
                                        same_user=user == user2))
    return bad


def intrinsic_calendar_failure(model, mode, P, contexts=1):
    """A shift/copy search cannot repair a user's collisions with itself."""
    user = [dict(user=0, shift=0, kind=mode)]
    bad, resources = (check(model, user, P, {}) if contexts == 1 else
                      check2(model, user, P, {}, mode, contexts))
    if not bad:
        return None
    return dict(P=P, users=[], col={}, bad=bad, nres=resources, nonrep=0,
                tried=[dict(users=1, result='FAULT', collisions=len(bad), first=bad[0],
                            why='Intrinsic same-user occupancy; shift/copy search cannot repair it')])


def check(model, users, P, col):
    by = collections.defaultdict(list)
    for u in users:
        for r, s, e in windows(model, u['user'], u['shift'], u['kind'], col):
            by[r].append((s % P, e - s, u['user']))
    bad = interval_collisions(by, P)
    # a user's own windows on one link must not overlap each other either (x and partial on the same link)
    return bad, {r: len(v) for r, v in by.items()}


def assign_k(shifts, P, win, k):
    """S81-SWEET: k >= 3 copies of one stage: users round-robin over the copies in shift order (latency user on A);
    every circular gap on a copy must be >= the window (same rule as LEG.copy_ok, k labels)"""
    labels = 'ABCDEFGH'[:k]
    order = sorted(range(len(shifts)), key=lambda u: shifts[u])
    pos = order.index(0)
    seq = order[pos:] + order[:pos]
    for rot in range(len(seq)):                       # where the short wrap gap falls when n % k != 0
        col = {u: labels[(i if i < len(seq) - rot else i + 1) % k] for i, u in enumerate(seq)} if rot else \
            {u: labels[i % k] for i, u in enumerate(seq)}
        ok = True
        for cp in labels:
            us = sorted(shifts[u] for u in col if col[u] == cp)
            for i, x in enumerate(us):
                nxt = us[(i + 1) % len(us)] + (P if i + 1 == len(us) else 0)
                if (len(us) > 1 and nxt - x < win) or (len(us) == 1 and P < win):
                    ok = False
        if ok and col[0] == 'A':
            return col
    return None


def colour(model, shifts, P, mode):
    col = {}
    for st in model['stages']:
        if st['copies'] > 1:
            w = st['step'] if mode == 'mtp' else st['occ']
            c = LEG.assign_copies(shifts, P, w) if st['copies'] == 2 else assign_k(shifts, P, w, st['copies'])
            if c is None:
                return None, st['stage']
            col[st['stage']] = c
    return col, None


def calendar(model, mode, N=None):
    P = qup(model['T_ar'] if mode == 'ar' else model['T_mtp_step'])
    intrinsic = intrinsic_calendar_failure(model, mode, P, 1)
    if intrinsic:
        return intrinsic
    key = 'step' if mode == 'mtp' else 'occ'
    nonrep = max(st[key] for st in model['stages'] if st['copies'] == 1)
    nonrep = max(nonrep, model['head_mtp'] if mode == 'mtp' else model['head_ar'])
    pipe = model.get('mtp_pipeline') if mode == 'mtp' else None
    if pipe and pipe.get('hold') == 'position':
        return calendar_position_jobs(model, P, N)
    tried = []
    for n in ([N] if N else range(max(1, P // int(nonrep)), 0, -1)):
        shifts = [(k * (P // PHASE_Q)) // n * PHASE_Q for k in range(n)]
        col, why = colour(model, shifts, P, mode)
        users = [dict(user=k, shift=shifts[k], kind=mode if (model.get('mtp_position_graph') or model.get('mtp_pipeline')) else ('latency' if k == 0 else mode)) for k in range(n)]
        if col is None:
            tried.append(dict(users=n, result='FAULT', why=f'{why}: no A/B colouring'))
            if N:
                return dict(P=P, users=users, col={}, tried=tried, bad=[dict(resource=why)], nres={})
            continue
        bad, nres = check(model, users, P, col)
        tried.append(dict(users=n, result='PASS' if not bad else 'FAULT', collisions=len(bad),
                          first=bad[0] if bad else None))
        if not bad or N:
            return dict(P=P, users=users, col=col, tried=tried, bad=bad, nres=nres, nonrep=nonrep)
    return dict(P=P, users=[], col={}, tried=tried, bad=[], nres={}, nonrep=nonrep)


def shift_search_pos(model, P, limit=64):
    """first-fit shifts for the one-job-a-position MTP pipeline: user k takes copy 'AB'[k % 2] on every duplicated
    stage; a shift difference D is forbidden if any window of one user overlaps any window of the other at D (same
    copy: every resource; other copy: every resource but the duplicated stage copies / their Engram engines)."""
    import numpy as np
    n = P // PHASE_Q
    byr = collections.defaultdict(list)
    for r, a, b in windows(model, 0, 0, 'mtp', {}):
        byr[r].append((a, b))
    copyb = {st['stage'] for st in model['stages'] if st['copies'] > 1}
    FD_same = np.zeros(n, dtype=bool)
    FD_diff = np.zeros(n, dtype=bool)
    for r, iv in byr.items():
        A = np.array([x[0] for x in iv]); B = np.array([x[1] for x in iv])
        lo = np.subtract.outer(A, B).ravel()
        hi = np.subtract.outer(B, A).ravel()
        _forbid(FD_same, lo, hi, P)
        stg = r.split('.')[1] if r.startswith('eng.') else r.split('.')[0]
        if not (stg in copyb and not r.startswith(('link', 'head', 'host'))):
            _forbid(FD_diff, lo, hi, P)
    FD_same[0] = FD_diff[0] = True
    users, F = [], {0: np.zeros(n, dtype=bool), 1: np.zeros(n, dtype=bool)}
    for k in range(limit):
        c = k % 2
        cand = np.nonzero(~F[c])[0]
        if not len(cand):
            break
        x = int(cand[0]) * PHASE_Q
        users.append(dict(user=k, shift=x, kind='mtp', colour='AB'[c]))
        for c2 in (0, 1):
            F[c2] |= np.roll(FD_same if c2 == c else FD_diff, x // PHASE_Q)
    return users


def calendar_position_jobs(model, P, N=None):
    """MTP pipeline, one job a position: per-user busy bound -> uniform phase-q shifts; copies round-robin in shift
    order (every rotation of the odd wrap tried); the exact checker (every window, same user included) decides."""
    pipe = model['mtp_pipeline']
    busy = []
    for i, (st, w) in enumerate(zip(model['stages'], pipe['stages'])):
        ld = pipe['lead'] if i else 0
        busy.append(sum(b - a for a, b in merge_iv([(a - ld, b) for a, b in w['position_windows']])) / st['copies'])
    nonrep = max(busy + [sum(b - a for a, b in pipe['heads'] + [pipe['draft']])])
    tried = []
    if SHIFT_SEARCH and N is None:                 # greedy first-fit on the phase grid (same-colour / other-colour sets)
        users = shift_search_pos(model, P)
        col = {st['stage']: {u['user']: 'ABCDEFGH'[u['user'] % st['copies']] for u in users}
               for st in model['stages'] if st['copies'] > 1}
        bad, nres = check(model, users, P, col)
        tried.append(dict(users=len(users), result='PASS' if not bad else 'FAULT', collisions=len(bad),
                          first=bad[0] if bad else None, search='greedy first-fit phase-grid shifts'))
        return dict(P=P, users=users if not bad else [], col=col, tried=tried, bad=bad, nres=nres, nonrep=nonrep,
                    searched=True)
    for n in ([N] if N else range(max(1, int(P // nonrep)), 0, -1)):
        shifts = [(k * (P // PHASE_Q)) // n * PHASE_Q for k in range(n)]
        users = [dict(user=k, shift=shifts[k], kind='mtp') for k in range(n)]
        best = None
        for rot in range(n if n % 2 else 1):
            col = {}
            for st in model['stages']:
                k = st['copies']
                if k > 1:
                    col[st['stage']] = {u: 'ABCDEFGH'[(u if u < n - rot or not rot else u + 1) % k] for u in range(n)}
            bad, nres = check(model, users, P, col)
            if best is None or len(bad) < len(best[1]):
                best = (col, bad, nres)
            if not bad:
                break
        col, bad, nres = best
        tried.append(dict(users=n, result='PASS' if not bad else 'FAULT', collisions=len(bad),
                          first=bad[0] if bad else None))
        if not bad or N:
            return dict(P=P, users=users, col=col, tried=tried, bad=bad, nres=nres, nonrep=nonrep)
    return dict(P=P, users=[], col={}, tried=tried, bad=[], nres={}, nonrep=nonrep)


# ------------------------------------------------------------------------------------------------ two job contexts
# ot_dsdv_fixed_issue (rtl/dsrom_sys/s81_dv/unit) already holds TWO job contexts (active[1:0], next_slot) that execute
# the same immutable calendar; a command on an engine the other context holds is a run fault (code 9: duplicate issue /
# engine_available low).  So two users may overlap on one stage copy iff (a) at most 2 users hold the stage copy at any
# edge and (b) their engine busy intervals never overlap.  Engine classes = the DAG node classes (field, su, coll, hbm,
# select, embed), each treated as ONE engine (the issuer has 13; a class may hold several: conservative); priced per-layer
# terms with no engine (dv_p4l / scan legs) block every class; expert slots hold field + su for the whole reservation;
# the combine holds coll + su.  MTP: the stage pattern repeated 6 times back to back (window 6 W >= 6 W - 5 scan).
CLASSES = ('field', 'su', 'coll', 'hbm', 'select', 'embed')


def merge_iv(iv):
    out = []
    for a, b in sorted(iv):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def stage_busy(log, st_rec):
    by = collections.defaultdict(list)
    for x in log:
        by[x['stage']].extend(x.get('busy', []))
    for st in st_rec:
        t = st['t']
        cls = collections.defaultdict(list)
        for a, b, k in by[st['stage']]:
            for kk in (CLASSES if k == 'ALL' else (k,)):
                cls[kk].append((a - t, b - t))
        st['busy'] = {k: merge_iv(v) for k, v in cls.items()}
        st['busy_total'] = {k: round(sum(b - a for a, b in v)) for k, v in st['busy'].items()}


def windows2(model, user, shift, mode, col):
    mt = mode == 'mtp'
    ex, ctx = [], []
    for st in model['stages']:
        cp = col.get(st['stage'], {}).get(user, 'A') if st['copies'] > 1 else 'A'
        r = f"{st['stage']}.{cp}"
        W = st['occ']
        reps = 6 if mt else 1
        ctx.append((r, shift + st['t'], shift + st['t'] + W * reps))
        for k in range(reps):
            o = shift + st['t'] + k * W
            for c, iv in st['busy'].items():
                ex.extend((f'{r}.{c}', o + a, o + b) for a, b in iv)
    for r, a, b in windows(model, user, shift, mode, col):
        if r.startswith(('link.', 'head', 'host')):
            ex.append((r, a, b))
    return ex, ctx


def check2(model, users, P, col, mode, cap=2):
    by = collections.defaultdict(list)
    cx = collections.defaultdict(list)
    for u in users:
        ex, ctx = windows2(model, u['user'], u['shift'], mode, col)
        for r, s, e in ex:
            by[r].append((s % P, e - s, u['user']))
        for r, s, e in ctx:
            cx[r].append((s % P, e - s, u['user']))
    bad = interval_collisions(by, P)
    for r, lst in cx.items():                       # at most two users hold a stage copy at any edge
        ev = []
        for s, L, u in lst:
            if L > P:
                bad.append(dict(resource=r + '.ctx', users=[u], overlap=L - P))
                continue
            e = s + L
            ev += [(s, 1), (e, -1)] if e <= P else [(s, 1), (P, -1), (0, 1), (e - P, -1)]
        ev.sort(key=lambda x: (x[0], x[1]))
        k = 0
        for t, d in ev:
            k += d
            if k > cap:
                bad.append(dict(resource=r + '.ctx', time=t, holders=k))
                break
    return bad, {r: len(v) for r, v in by.items()}


def calendar2(model, mode, N=None):
    P = qup(model['T_ar'] if mode == 'ar' else model['T_mtp_step'])
    intrinsic = intrinsic_calendar_failure(model, mode, P, 2)
    if intrinsic:
        return intrinsic
    reps = 6 if mode == 'mtp' else 1
    lb = 1
    for st in model['stages']:
        need = max([v for v in st['busy_total'].values()] + [st['occ'] / 2.0]) * reps / st['copies']
        lb = max(lb, need)
    lb = max(lb, model['head_mtp'] if mode == 'mtp' else model['head_ar'])
    tried = []
    for n in ([N] if N else range(int(P // lb), 0, -1)):
        shifts = [(k * (P // PHASE_Q)) // n * PHASE_Q for k in range(n)]
        col = {st['stage']: {k: 'AB'[k % 2] for k in range(n)} for st in model['stages'] if st['copies'] > 1}
        users = [dict(user=k, shift=shifts[k], kind=mode if (model.get('mtp_position_graph') or model.get('mtp_pipeline')) else ('latency' if k == 0 else mode)) for k in range(n)]
        bad, nres = check2(model, users, P, col, mode)
        tried.append(dict(users=n, result='PASS' if not bad else 'FAULT', collisions=len(bad),
                          first=bad[0] if bad else None))
        if not bad or N:
            return dict(P=P, users=users, col=col, tried=tried, bad=bad, nres=nres, nonrep=lb)
    return dict(P=P, users=[], col={}, tried=tried, bad=[], nres={}, nonrep=lb)


def _forbid(G, lo, hi, P):
    """mark grid cells (PHASE_Q cycles) whose offset lies in any open range (lo, hi) mod P (conservative rounding)"""
    import numpy as np
    n = len(G)
    a = np.floor(np.asarray(lo, dtype=float) / PHASE_Q).astype(np.int64)
    b = np.ceil(np.asarray(hi, dtype=float) / PHASE_Q).astype(np.int64)
    keep = b - a > 1
    a, b = a[keep] + 1, b[keep]              # cells strictly inside: offset k*Q with lo < kQ < hi
    full = (b - a) >= n
    if full.any():
        G[:] = True
        return
    d = np.zeros(2 * n + 2, dtype=np.int64)
    a0 = np.mod(a, n)
    b0 = a0 + (b - a)
    np.add.at(d, a0, 1)
    np.add.at(d, b0, -1)
    c = np.cumsum(d)[:2 * n]
    G |= (c[:n] + c[n:2 * n]) > 0


def shift_search(model, mode, P, cap=2):
    """greedy first-fit user shifts on the PHASE_Q grid: pairwise engine / link / head / host exclusivity through two
    forbidden-difference sets (same copy colour, other colour), the <= 2 holders a stage copy through a coverage map"""
    import numpy as np
    n = P // PHASE_Q
    reps = 6 if mode == 'mtp' else 1
    FD_same = np.zeros(n, dtype=bool)
    FD_diff = np.zeros(n, dtype=bool)
    # per resource interval lists of ONE user at shift 0 (copy A everywhere for the same-colour set, copy-B stages are
    # dropped from the other-colour set); links / head / host: one resource each (conservative across colours)
    ex, ctx = windows2(model, 0, 0, mode, {})
    byr = collections.defaultdict(list)
    for r, a, b in ex + (ctx if cap == 1 else []):     # one context: the hold window itself is exclusive
        byr[r].append((a, b))
    copyb = {st['stage'] for st in model['stages'] if st['copies'] > 1}
    for r, iv in byr.items():
        A = np.array([x[0] for x in iv]); B = np.array([x[1] for x in iv])
        lo = np.subtract.outer(A, B).ravel()          # other - mine: overlap iff a2 - b1 < D < b2 - a1
        hi = np.subtract.outer(B, A).ravel()
        _forbid(FD_same, lo, hi, P)
        stg = r.split('.')[0]
        if not (stg in copyb and not r.startswith(('link', 'head', 'host'))):
            _forbid(FD_diff, lo, hi, P)
    FD_same[0] = FD_diff[0] = True
    sts = [(st['stage'], st['copies'] > 1, st['t'], st['occ'] * reps) for st in model['stages']]
    cov = {}
    users, F = [], {0: np.zeros(n, dtype=bool), 1: np.zeros(n, dtype=bool)}
    k = 0
    while True:
        col = k % 2
        free = ~F[col]
        # context: x is invalid where a stage copy already has 2 holders during x's window
        bad = np.zeros(n, dtype=bool)
        for (name, cb, t, W) in (sts if cap == 2 else []):
            key = (name, col if cb else 0)
            if key in cov:
                full = cov[key] >= 2
                if full.any():
                    idx = np.nonzero(full)[0]
                    # x window [x + t, x + t + W] hits cell j  ->  x in (j*Q - t - W, j*Q + Q - t)
                    _forbid(bad, idx * PHASE_Q - t - W - PHASE_Q, idx * PHASE_Q + PHASE_Q - t + PHASE_Q, P)
        cand = np.nonzero(free & ~bad)[0]
        if not len(cand):
            break
        x = int(cand[0]) * PHASE_Q
        users.append(dict(user=k, shift=x, kind='latency' if k == 0 else mode, colour='AB'[col]))
        for c2 in (0, 1):
            F[c2] |= np.roll(FD_same if c2 == col else FD_diff, x // PHASE_Q)
        for (name, cb, t, W) in sts:
            key = (name, col if cb else 0)
            cv = cov.setdefault(key, np.zeros(n, dtype=np.int8))
            a = (x + t) // PHASE_Q
            b = -(-(x + t + W) // PHASE_Q)
            idx = np.arange(a, b + 1) % n
            cv[idx] += 1
        k += 1
        if k > 400:
            break
    return users


def calendar3(model, mode, N=None, users=None, cap=2):
    """two job contexts with searched shifts; N + 1 control = every grid shift for one more user FAULTS (greedy-maximal)"""
    P = qup(model['T_ar'] if mode == 'ar' else model['T_mtp_step'])
    intrinsic = intrinsic_calendar_failure(model, mode, P, cap)
    if intrinsic:
        return intrinsic
    if users is None:
        users = shift_search(model, mode, P, cap)
    if N is not None:
        users = users[:N]
    col = {st['stage']: {u['user']: u.get('colour', 'AB'[u['user'] % 2]) for u in users}
           for st in model['stages'] if st['copies'] > 1}
    bad, nres = check2(model, users, P, col, mode, cap)
    return dict(P=P, users=users, col=col, tried=[dict(users=len(users), result='PASS' if not bad else 'FAULT',
                                                      collisions=len(bad), first=bad[0] if bad else None,
                                                      search='greedy first-fit shifts')],
                bad=bad, nres=nres, nonrep=0)


def link_bound(model, mode, P):
    """the busiest stage-hop circuit: one user's windows on it a period (x 6 a MTP step), and the users it alone allows"""
    by = collections.Counter()
    for r, a, b in windows(model, 0, 0, mode, {}):
        if r.startswith('link.'):
            by[r] += b - a
    r, busy = max(by.items(), key=lambda x: x[1])
    return dict(resource=r, busy_per_user=round(busy, 1), users_if_only_bound=int(P // busy), circuits=len(by),
                messages=sum(1 for x in model['links']))


# ------------------------------------------------------------------------------------------------ build
def build(mapp=MAP, cmode='record', alap=False, unqualified=False, contexts=1, dsplit=False, mtp_position_barriers=False):
    mp = json.loads(Path(mapp).read_text())
    sha = hashlib.sha256(Path(mapp).read_bytes()).hexdigest()
    stages = mp['stages']
    qualified = bool(mp.get('verdict', {}).get('all_pass'))
    assert (qualified or unqualified) and len(stages) == mp['stages_count'], 'map has no exact capacity PASS verdict'
    F2 = load(ROOT / 'results/token_pass/cal2_s81_1020/fold_cal2.py', 'fold_cal2')
    r, dags = composed(cmode)
    wa = r['workloads']['ar']
    wm = r['workloads']['mtp']
    global HOP
    HOP = HOP_SW - (SWITCHED - dcyc('stage_hop'))           # direct cabling: the stage-hop law's off-chip leg
    hop_head = HOP_SW - (SWITCHED - dcyc('head_hop'))
    solve = load(ROOT / 'tools/toksim_s81_compose.py', 'toksim_s81_compose_rt').solve
    ovr = {}
    for wl, w in (('ar', wa), ('mtp', wm)):                 # REL node terms -> composer T re-solved on the same DAG
        d0, c0 = dags[wl]
        c1, lg = node_override(d0, c0)
        t0, t1 = retime(d0, c0, c1, w['extra_terms'], solve)
        assert abs(t0 - w['T_cycles']) < 1.0, (wl, t0, w['T_cycles'])
        dags[wl] = (d0, c1)
        ovr[wl] = dict(T_before=round(t0, 1), T_after=round(t1, 1), delta=round(t1 - t0, 1),
                       critical_by_op={k: round(v, 1) for k, v in sorted(lg.items()) if v})
    dag, cyc = dags['ar']
    seg, scan, head_ar, cnode = layer_segments(dag, cyc, F2, wa['extra_terms'])
    # SU add of the partial: priced by analogy with the measured eng.add (an SU vector add), per instance
    eadd = [cnode[n['id']] for n in dag['nodes'] if n.get('op') == 'eng.add']
    add = max(eadd) if eadd else 120.0
    embed = sum(cnode[n['id']] for n in dag['nodes'] if n.get('op') == 'embed')
    win, log, links, chain, legacy = timeline(stages, seg, add, embed, alap, dsplit,
                                              causal_integer=mtp_position_barriers)
    # token: composer T + cal2 structural + 20 added hops + the forward-x / reservation change of the chain
    s_ar = sum(cal2_delta(n, F2) for n in dag['nodes'] if n.get('critical'))
    dagm, cycm = dags['mtp']
    s_mtp = sum(cal2_delta(n, F2) for n in dagm['nodes'] if n.get('critical'))
    dh = (len(stages) - HOP_REF) * HOP
    dchain = chain - legacy
    T_ar = wa['T_cycles'] + ovr['ar']['delta'] + s_ar + dh + dchain
    st_rec = []
    for i, st in enumerate(stages):
        a, b = win[i]
        occ = math.ceil(b - a)
        sc = scan.get(st['dense_layer'], 0.0) if st['dense_layer'] is not None else 0.0
        st_rec.append(dict(stage=st['stage'], dense_layer=st['dense_layer'], experts=st['experts'],
                           copies=int(st.get('copies') or (2 if st['copy_b'] else 1)), t=math.floor(a), occ=occ,
                           step=math.ceil(6 * (b - a) - 5 * sc), scan=round(sc, 1)))
    wave_old = sum(cycm[n['id']] for n in dagm['nodes'] if n.get('op') == 'wave.busy' and n.get('critical'))
    wave_new = 5 * max(s['occ'] - s['scan'] for s in st_rec)
    draft_tail = sum(cycm[n['id']] for n in dagm['nodes'] if (n.get('op') or '').startswith('draft.')
                     and n.get('critical'))
    head_mtp = 6 * head_ar + draft_tail
    T_mtp = wm['T_cycles'] + ovr['mtp']['delta'] + s_mtp + dh + dchain + (wave_new - wave_old)
    eng_layers = {n['layer'] for n in dag['nodes'] if n.get('op') == 'eng.hbm_read'}
    for x in (log if REL['eng_ii'] else []):     # Engram engine window: at the start of its dense (B half) item
        for l in eng_layers:
            if x['item'] in (f'dense L{l}', f'dense L{l} B half'):
                sr = next(q for q in st_rec if q['stage'] == x['stage'])
                sr['eng_off'] = math.floor(x['start']) - sr['t']
    lead = 0
    if REL['land']:                               # LINK5 land 0: the receiver copy is held from the first beat's landing
        lead = math.ceil(HOP - x_flat('stage_hop') + RX_JIT)
        for q in st_rec[1:]:
            q['t'] -= lead
            q['occ'] += lead
            q['step'] += lead
            if q.get('eng_off') is not None:
                q['eng_off'] += lead
    model = dict(stages=st_rec, links=links, head_t=math.ceil(chain + embed + hop_head), head_ar=math.ceil(head_ar),
                 head_mtp=math.ceil(head_mtp), draft_tail=math.ceil(draft_tail), T_ar=T_ar, T_mtp_step=T_mtp)
    if REL['mtp_law'] == 'pipeline' and not mtp_position_barriers:
        if contexts != 1:
            raise ValueError('MTP pipeline MODEL supports one job context only')
        tl, plinks, chain_end = timeline_positions(stages, seg, add, embed, alap, scan, 6)
        tl1, _, chain1 = timeline_positions(stages, seg, add, embed, alap, scan, 1)
        pipe = mtp_pipeline_graph(model, tl, plinks, chain_end, math.ceil(hop_head), lead)
        pipe['hold'], pipe['lead'] = MTP_HOLD, lead
        model['mtp_pipeline'] = pipe
        T_mtp_old = T_mtp
        # Owner decision15: the checker-qualified causal pipeline is the law
        # of record; the former6f stretch law remains a sensitivity below.
        model['T_mtp_step'] = T_mtp = pipe['step_end'] + (T_ar - (chain1[0] + hop_head + head_ar))
        pipe['T_mtp_law_6f'] = round(T_mtp_old, 1)
        pipe['ar_tail_beyond_head'] = round(T_ar - (chain1[0] + hop_head + head_ar), 1)
        pipe['ar_chain_integer_check'] = dict(timeline=round(chain + embed, 1), positions1=chain1[0])
        for i, q in enumerate(st_rec):
            q['step'] = math.ceil(pipe['stages'][i]['owner_end'] - pipe['stages'][i]['owner_start'])
    if mtp_position_barriers:
        if contexts != 1:
            raise ValueError('Position-barrier MODEL currently supports one job context only')
        graph = position_barrier_graph(model)
        model['mtp_position_graph'] = graph
        model['T_mtp_step'] = T_mtp = graph['step_cycles']
        # Colouring reserves the whole span between first and final position use.
        # This is conservative; the exact checker still receives every interval.
        for i, q in enumerate(st_rec):
            q['step'] = graph['positions'][-1]['stages'][i]['owner_end'] - graph['positions'][0]['stages'][i]['owner_start']
    comp = dict(composer=('tools/toksim_s81_compose.py release-partial (results/token_pass/measured_s81_1019/cycles.json)'
                          if cmode == 'record' else 'tools/toksim_s81_compose.py --scenario calpipe + S81-ROMOPT o3mix '
                          'compiled spans (' + str(ROMOPT.relative_to(ROOT)) + ')'),
                ar=dict(T_composer=wa['T_cycles'], tok_s_composer=wa['tok_s'], pct_measured=wa['pct_measured'],
                        cal2_structural=s_ar, added_hops=dh, forward_x_chain_delta=round(dchain, 1),
                        T=round(T_ar, 1), tok_s=round(F / T_ar, 1)),
                mtp=dict(T_composer=wm['T_cycles'], tok_s_composer=wm['tok_s'], pct_measured=wm['pct_measured'],
                         cal2_structural=s_mtp, added_hops=dh, forward_x_chain_delta=round(dchain, 1),
                         wave_composer=round(wave_old, 1), wave_physical=round(wave_new, 1),
                         T=round(T_mtp, 1), tok_s=round(TAU * F / T_mtp, 1)),
                partial_add_cycles=round(add, 1), partial_add_grade='priced (= measured eng.add SU add instance)')
    if REL != REL0:
        comp['release241'] = dict(REL, hop=HOP, hop_head=hop_head, x_flat_stage_hop=x_flat('stage_hop'), land_lead=lead,
                                d_cycles={k: dcyc(k) for k in ('tp_mesh', 'stage_hop', 'head_hop')},
                                hop_latency=str(HOPLAT.relative_to(ROOT)) + ' @4b528ad2b',
                                node_override=ovr, dense2=bool(mp.get('dense_split2')),
                                dense2_ser=DENSE2_SER if mp.get('dense_split2') else 0,
                                eng_stages=[q['stage'] for q in st_rec if q.get('eng_off') is not None],
                                host='MODEL S81.HOST option (b), not connected production programme: local calendar job start; host plane = '
                                     'head die only (HOST_TOK a token a user), no host / KS frame on stage circuits')
    if contexts != 1:
        stage_busy(log, st_rec)
    recs = {}
    for mode in ('ar', 'mtp'):
        cap = 1 if contexts in (1, -1) else 2
        if contexts == 1:
            cal = calendar(model, mode)
            n = len(cal['users'])
            neg = calendar(model, mode, n + 1) if n else None
        else:
            cal = calendar3(model, mode, cap=cap)
            n = len(cal['users'])
            # N + 1: one more user at EVERY grid shift (both colours) must collide -> the exhaustive control
            neg = dict(bad=[], tried=0)
            P = cal['P']
            fails = 0
            last = dict(user=n, kind=mode)
            step = max(PHASE_Q, (P // 64) // PHASE_Q * PHASE_Q)   # 64 sampled shifts x 2 colours, exact check2
            for xs in range(0, P, step):
                for colour in 'AB':
                    uu = cal['users'] + [dict(last, shift=xs, colour=colour)]
                    cc = {g: {**c, n: colour} for g, c in cal["col"].items()}
                    b2, _ = check2(model, uu, P, cc, mode, cap)
                    neg['tried'] += 1
                    fails += 1 if b2 else 0
            neg['bad'] = [1] if fails == neg['tried'] else []
            neg['sampled_shifts'] = neg['tried']
            neg['sampled_fault'] = fails
        inj = None
        if n >= 2:
            u = [dict(x) for x in cal['users']]
            u[1]['shift'] = u[0]['shift'] + PHASE_Q          # injected collision: user 1 on top of user 0
            inj = len((check(model, u, cal['P'], cal['col']) if contexts == 1 else
                       check2(model, u, cal['P'], cal['col'], mode, cap))[0])
        T = model['T_ar'] if mode == 'ar' else model['T_mtp_step']
        per = (F / max(T, cal['P'])) * (TAU if mode == 'mtp' else 1.0)
        recs[mode] = dict(
            schema=SCHEMA, lane='S81-MUCAL140' if REL == REL0 else 'S81-CAL241', mode=mode, map=str(Path(mapp).resolve().relative_to(ROOT)), compose=cmode, map_sha256=sha, alap=alap, job_contexts=contexts, map_capacity_verdict='PASS' if qualified else 'UNQUALIFIED (model only)',
            stages=len(stages), copy_b_stages=[s['stage'] for s in st_rec if s['copies'] > 1],
            period=cal['P'], users=n, per_user_tok_s=round(per, 1) if n and not cal['bad'] else None,
            aggregate_tok_s=round(n * per) if n and not cal['bad'] else None,
            rate_qualified=bool(n and not cal['bad']),
            collision_witnesses=cal['bad'][:20],
            calendar_failure=('Same-user occupancy must be fixed by a dependency-propagated per-position timeline; '
                              'TX-only serialization does not update downstream arrivals/owners/head.' if cal['bad'] else None),
            bound_window=dict(cycles=int(cal.get('nonrep') or 0),
                              stage=max((s for s in st_rec if s['copies'] == 1),
                                        key=lambda s: s['step' if mode == 'mtp' else 'occ'])['stage']),
            checker=dict(result='PASS' if n and not cal['bad'] else 'FAULT', collisions=len(cal['bad']),
                         same_user_checked=True,
                         source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                         position_graph_sha256=(hashlib.sha256(json.dumps(model['mtp_position_graph'],
                             sort_keys=True, separators=(',', ':')).encode()).hexdigest()
                             if model.get('mtp_position_graph') and mode == 'mtp' else None),
                         resources=len(cal['nres']), windows=sum(cal['nres'].values()),
                         negative_n_plus_1=dict(users=n + 1, result='FAULT' if neg and (neg['bad']) else 'PASS?!',
                                                collisions=len(neg['bad']) if neg else None),
                         negative_injected_shift=dict(collisions=inj, result=('NOT_APPLICABLE: fewer than two admitted users'
                                                    if n < 2 else 'FAULT' if inj else 'MISSED'))),
            search=cal['tried'][:12],
            slots=[dict(slot=i, user=u['user'], shift=u['shift'],
                        copy={g: c.get(u['user'], 'A') for g, c in cal['col'].items()})
                   for i, u in enumerate(cal['users'])],
            **({'binding_link': link_bound(model, mode, cal['P']),
                'binding_next_user': ([t for t in cal['tried'] if t['result'] != 'PASS'] or [None])[-1]}
               if REL != REL0 else {}),
            stage_windows=[{k: s[k] for k in ('stage', 'dense_layer', 'copies', 't', 'occ', 'step', 'busy_total', 'eng_off') if k in s}
                           for s in st_rec],
            composition=comp, grade='node cycles: composer grades; stage split / reservation / forward-x / MTP law: MODEL')
    if model.get('mtp_pipeline'):
        recs['mtp']['pipeline_graph'] = model['mtp_pipeline']
        recs['mtp']['grade'] = model['mtp_pipeline']['qualification']
        comp['mtp']['schedule_law'] = model['mtp_pipeline']['law']
    if mtp_position_barriers:
        recs['mtp']['position_graph'] = graph
        recs['mtp']['grade'] = graph['qualification']
        recs['mtp']['rtl_calendar_qualified'] = False
        comp['mtp']['schedule_law'] = 'Explicit six complete AR position graphs; global barriers; draft and host tail'
    if not recs['mtp']['rate_qualified']:
        comp['mtp']['unqualified_original_T'] = comp['mtp'].pop('T')
        comp['mtp']['tok_s'] = None
        comp['mtp']['schedule_verdict'] = 'FAILED: MTP dependency/occupancy timeline'
    recs['ar']['layer_segments'] = {f'L{l}': {k: round(v, 1) for k, v in seg[l].items()} for l in range(40)}
    recs['ar']['timeline_log'] = [dict({k: v for k, v in x.items() if k != 'busy'}, start=round(x['start'], 1),
                                       end=round(x['end'], 1)) for x in log]
    return recs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default=str(OUT))
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--map', default=str(MAP))
    ap.add_argument('--compose', choices=['record', 'romopt'], default='record')
    ap.add_argument('--unqualified', action='store_true', help='allow a map without the exact capacity verdict (model)')
    ap.add_argument('--contexts', type=int, choices=[1, 2, -1], default=1,
                    help='job contexts a stage: 1 uniform shifts (record), -1 = 1 context + searched shifts, 2 = RTL two contexts + searched shifts')
    ap.add_argument('--alap', action='store_true', help='just-in-time expert slots on the partial chain (compiler)')
    ap.add_argument('--tag', default='phys140', help='output name calendar_<tag>_{ar,mtp}.json')
    ap.add_argument('--release241', action='store_true', help='S81-CAL241 release terms (REL241: direct cabling, LINK5 '
                    'serial stage circuit + land-0 lead with TX hold, G4 attention, idx +40, Engram RA640 / II 704)')
    ap.add_argument('--attn', choices=sorted(ATTN), help='attention service variant (overrides REL)')
    ap.add_argument('--mtp-position-barriers', action='store_true', help='Conservative explicit six-position MODEL; compiler implementation pending')
    ap.add_argument('--mtp-hold', choices=['step', 'position'], default='step',
                    help='MTP pipeline: a stage copy is held for the whole six-position step (one job context, default) '
                         'or one job a position (copy free between positions; needs per-position job starts)')
    ap.add_argument('--mtp-shift-search', action='store_true', help='MTP pipeline + --mtp-hold position: greedy '
                    'first-fit phase-grid shifts instead of uniform shifts (the exact checker still decides)')
    ap.add_argument('--lane-landing-cycles', type=int, default=0, choices=[0, 6, 7],
                    help='Measured end-slice lane crossing cost: 6 landing edges, 7 with IN_PIPE')
    a = ap.parse_args(argv)
    global LANE_LANDING_CYCLES
    LANE_LANDING_CYCLES = a.lane_landing_cycles
    global MTP_HOLD, SHIFT_SEARCH
    MTP_HOLD, SHIFT_SEARCH = a.mtp_hold, a.mtp_shift_search
    if a.release241:
        REL.update(REL241)
    if a.attn:
        REL['attn'] = a.attn
    recs = build(a.map, a.compose, a.alap, a.unqualified, a.contexts, mtp_position_barriers=a.mtp_position_barriers)
    rc = 0
    for mode, rec in recs.items():
        f = Path(a.out) / f'calendar_{a.tag}_{mode}.json'
        txt = json.dumps(rec, indent=1) + '\n'
        if a.check:
            same = f.exists() and f.read_text() == txt
            print(f'{mode}: {"SAME" if same else "DIFFERS"} {f}')
            rc |= 0 if same else 1
        else:
            f.write_text(txt)
        c = rec['checker']
        print(f"{mode}: {rec['users']} users x {rec['per_user_tok_s']} = {rec['aggregate_tok_s']} agg; period "
              f"{rec['period']}; bound {rec['bound_window']}; checker {c['result']} ({c['windows']} windows, "
              f"{c['collisions']} coll); N+1 {c['negative_n_plus_1']['result']}; inject {c['negative_injected_shift']['result']}")
        if c['result'] != 'PASS':
            rc = 2
    print(json.dumps(recs['ar']['composition'], indent=1))
    return rc


if __name__ == '__main__':
    sys.exit(main())
