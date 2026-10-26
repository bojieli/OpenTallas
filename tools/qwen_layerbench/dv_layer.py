#!/usr/bin/env python3
"""dv_layer: the FULL Qwen compute-die decode layer lowered onto the 12 DV slices + its analytic cycle composition
(QW-CLAYER 10-18, TOK.QW.LAYER; dv2f14bi lane ages).

Inputs (all compiled / measured elsewhere, nothing re-priced here):
  ctlm_image.compile_image   the tt_ctlm decode plan (W5-pin edges of every programme op from the stage start) on the
                             bi lane ages (R_CMD / R_HR 19, R_SS / R_AG 17) -- the PRICED layer
  dv_lower.lower             RMSNorm sum of squares PC0 (per-slice SSQ, fused ROOT r)          ages: slice_ages.json
  dv_lower_vec.lower_vec     qk (PC2..PC10: v*r, q/k*r, head SSQ, rsqrt, QK-norm, RoPE -> D2D), resid (PC14 + PC15 /
                             PC22 + PC23: AR landing, fused post-scale + residual add + SSQ, x stream), silu (PC17..19)
                             attn (PC11 -> PC12, QW-ATTNRET: KV result dr words landed on PORTS dd windows + o_proj x
                             stream; measured span results/rtl/qw_attnret_1019/record.json)
                                                                                                ages: vec_ages.json
  dv_lower_mat               STN of qkv / o / gate-up / down, XC dst 0, AR stagger                ages: stn_ages.json
  TOKEN-XDIE-QTP8 record     TP8 AR 256 x 512 b on the production collective: last in -> first out E 284, first in ->
                             last out 795 (LS 376; dv2f14bi needs LS 378 = +2, Q-COLLCAL3)
Every RTL timing constant above was measured by a Verilator 5.050 bench of the slice2 / collective RTL; the lowered
families were each benched (PASS on their compiled edges, mutants FAIL).  This tool:
  (1) places every family on the layer timeline (dependency-driven, the ctlm plan's gaps kept), emits the ONE spliced
      decode calendar (all families) and checks it: one command a W5 edge, cmd_cal fetch model, image capacity,
      cross-family occupancy of the shared chains;
  (2) composes the layer cycles analytically (L0 cold from the stage-0 start, L1 chained = the stage period) and lists
      each stage: priced span (ctlm plan) vs lowered span, and where each number comes from;
  (3) lists every op that cannot be lowered / placed (precise gaps).
Usage: dv_layer.py --out FILE.json [--stage 1] [--tile-first 40] [--ar-order row|slice]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ctlm_image as CI      # noqa: E402
import dv_lower as D         # noqa: E402
import dv_lower_mat as M     # noqa: E402
import dv_lower_vec as V     # noqa: E402

ROOT = D.ROOT
N = D.NSLICE
LANE_AGES = 'results/rtl/qwen_layer_tput_1018/ctlm_prog/lane_ages_dv2f14bi.json'
QTP8 = dict(E=284, span=795, words=256, ls_rec=376, ls_bi=378,
            source='lanes/TOKEN-XDIE-QTP8.md + results/rtl/xdie_qtp8_1018/record.json (claude/xdie-qtp8-1018 fed8119c7): '
                   'AR 256 x 512 b, production LU 53 / LS 376, Verilator 5.050; bi LS 378 (Q-COLLCAL3 e1a641d23)')
MARGIN = 2
ATTNRET_REC = 'results/rtl/qw_attnret_1019/record.json'     # QW-ATTNRET: measured attention-return span (bench)
# critical-path stage boundaries where compose(die_edges=...) inserts PRICED die edges (TOKSIM-QW2 10-20)
EDGE_POINTS = ('pre_qkv', 'pre_qk', 'pre_attn', 'pre_o', 'pre_r1', 'pre_gu', 'pre_silu', 'pre_down', 'pre_r2')


def ctlm_rec(stage, lane_ages=LANE_AGES):
    a = argparse.Namespace(program=CI.DEF_PROGRAM, lowering=CI.DEF_LOWERING, token_path=CI.DEF_TOKEN_PATH,
                           relay=CI.DEF_RELAY, lane_ages=lane_ages, stage=stage, sys_face_events=CI.DEF_SF_EVENTS,
                           period=None, lead_margin=2, xpf_transport_edges=None, me_observe_edges=1, su_first_write=12,
                           dv_lower=True, tload=False, lm_head=False, head_plan=CI.HEAD_PLAN)
    image, rec = CI.compile_image(a)
    return rec


def vec_family(mode, ar_order):
    """lower_vec + the Sched it used (occupancy keys of the scalar / x / d2d chains)"""
    got = []
    base = V.Sched

    class Cap(base):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            got.append(self)
    V.Sched = Cap
    try:
        lw = V.lower_vec(mode, ar_order=ar_order)
    finally:
        V.Sched = base
    return lw, got[-1]


def ssq_family():
    lw = D.lower()
    cmds = [c for c in lw['commands'] if c['label'].startswith('SSQ')]
    e0 = min(c['edge'] for c in cmds)
    span = max(c['edge'] for c in cmds) - e0 + lw['ages']['ssq_psum_out'][-1] + D.SC_HOP * (N - 1) + 61
    boot = [c for c in lw['commands'] if not c['label'].startswith('SSQ')]
    return lw, cmds, e0, span, boot


def compose(stage=1, tile_first=40, ar_order='row', lane_ages=LANE_AGES, tile_mode='priced', attn_cycles=None,
            tile_meas=None, qtp8=None, die_edges=None):
    """TOKSIM-QW 10-19: attn_cycles = MEASURED attention round trip (q,k,v last D2D word at W5 -> first result dr word
    at the W5 return pin + 16, replaces the ctlm price); tile_mode 'measured' + tile_meas = {op: {first_rs, first_final,
    last_final, far}} edges from hr go at the slice pins (XT1 column-slice RTL run) replace the tile_first PARAMETER /
    ME price; qtp8 = measured TP8 AR constants (E, ls_rec, ls_bi) overriding QTP8.
    TOKSIM-QW2 10-20 (TOK.QW.SCHED): die_edges = {boundary: [{label, cycles, grade, source}, ...]} PRICED die edges the
    compiler must absorb (landings, native59, ctlm hr/tl, slice2 landed-parent lanes), inserted on the critical path at
    the named stage boundary (EDGE_POINTS) as their own stage rows; everything after the boundary moves later, the
    spliced calendar and the chained period / L0 cold see them. Default None = unchanged composition."""
    Q8 = dict(QTP8, **(qtp8 or {}))
    rec = ctlm_rec(stage, lane_ages)
    R, C = rec['relay'], rec['constants']
    plan = rec['plan']
    P = {p['pc']: p for p in plan if p['pc'] is not None and p['kind'] in ('SU', 'ME', 'NATIVE', 'END')}
    XCp = [p for p in plan if p['kind'] == 'XC']
    ages = M.load_ages()
    own = D.ownership()
    smap = D.slice_map()
    gaps, notes = [], []

    # ---------------- family spans (each from its own lowering, local timeline)
    ssq_lw, ssq_cmds, ssq_e0, ssq_span, ssq_boot = ssq_family()
    fam = {m: vec_family(m, ar_order if m == 'resid' else 'slice') for m in ('qk', 'resid', 'silu', 'attn')}
    at_lw, _ = fam['attn']
    at_r0 = at_lw['dd_r0']
    at_span_c = max(x['edge_e5'] for x in at_lw['expected']['x']) - at_r0
    at_rec = json.loads((ROOT / ATTNRET_REC).read_text()) if (ROOT / ATTNRET_REC).exists() else {}
    at_span = at_rec.get('measured_span_edges')
    if at_span is None:
        gaps.append(f'ATTENTION RETURN: no measured span ({ATTNRET_REC}); the compiled span {at_span_c} is used')
        at_span = at_span_c
    elif at_span != at_span_c:
        gaps.append(f'ATTENTION RETURN: measured span {at_span} != compiled {at_span_c} (re-bench the attn family)')
    qk, _ = fam['qk']
    qk_c0 = min(c['edge'] for c in qk['commands'])
    qk_end = max(d['edge_w5'] for d in qk['expected']['d2d'])
    rs, _ = fam['resid']
    rs_cfg = [c for c in rs['commands'] if c['label'].startswith(('ROOT', 'STREAM'))]
    rs_r0 = rs['ar_r0']
    rs_xend = max(x['edge_e5'] for x in rs['expected']['x'])
    rs_psum = max(int(k.split(',')[1]) for k in rs['expected']['psum'])
    sl, _ = fam['silu']
    sl_c0 = min(c['edge'] for c in sl['commands'])
    sl_end = max(x['edge_e5'] for x in sl['expected']['x'])
    rv = {7: ages['l8_ar'] - 7, 8: ages['l8_ar'], 9: ages['l8_ar'] + 7}

    def go_w5(at):
        return at + C['ISSUE_TO_ROM'] + R['R_HR']

    tile_note = []

    def mv_land(name, at, done):
        """VM-destination matvec: the column tiles deliver the far words; with tile_first the DV tail is lowered, the
        tile compute is the ctlm price (the last result lands no earlier than the priced ME done)"""
        tf = tile_first
        if tile_mode == 'measured':                      # tiles: first rs word / last final word measured from hr go
            m = tile_meas[name]
            tf = m['first_rs'] + m['far']
            done = go_w5(at) + m['last_final'] + m['far'] + rv[own[name]['level']]
        for _ in range(2):
            ch = M.Chain(smap)
            low = M.lower_matvec(name, go_w5(at) + tf, ages, ch, own=own)
            land = max(d['far'][-1] for d in low['deliveries']) + rv[own[name]['level']]
            if land >= done or tile_mode == 'first':
                break
            tf += done - land
        tile_note.append(dict(matvec=name, tile_first_eff=tf, dv_tail=land - (go_w5(at) + tf), land=land, priced_done=done,
                              go_w5=go_w5(at)))
        return low, ch, go_w5(at) + tf, land

    def mv_ar(name, at, done):
        tf = tile_first
        if tile_mode == 'priced':                        # the last AR word leaves W5 no earlier than the priced ME done
            tf = max(tf, done - 255 - go_w5(at) - ages['l8_ar'] - 2 * (N - 1))
        elif tile_mode == 'measured':                    # first AR word after the first measured final word, last after the last
            m = tile_meas[name]
            tf = max(m['first_final'] + m['far'], m['last_final'] + m['far'] - 255)
        tile_note.append(dict(matvec=name, tile_first_eff=tf, priced_done=done, go_w5=go_w5(at)))
        ch = M.Chain(smap)
        t0 = go_w5(at) + tf + ages['l8_ar'] + 2 * (N - 1)
        x = M.lower_xc(ch, ages, t0, 4096 // 16, 0)
        low = M.lower_matvec(name, t0, ages, ch, own=own)
        coll = M.ar_collisions(low, ages)
        if coll:
            gaps.append(f'{name}: AR outbound lane collisions {coll[:2]}')
        last_in = t0 + 255
        first_out = last_in + Q8['E'] + (Q8['ls_bi'] - Q8['ls_rec'])
        return low, ch, x, t0, first_out

    # ---------------- critical path (W5-pin edges from the stage start), plan gaps kept between dependent ops
    gap = lambda a, b: P[b]['at'] - P[a]['done']                         # noqa: E731
    st = []

    def stage_rec(name, pcs, start, end, p_start, p_end, src, **kw):
        st.append(dict(stage=name, pcs=pcs, start=start, end=end, cycles=end - start, priced_start=p_start,
                       priced_end=p_end, priced_cycles=p_end - p_start, source=src, **kw))
        return end
    DE = die_edges or {}
    bad = sorted(set(DE) - set(EDGE_POINTS))
    if bad:
        raise ValueError(f'die_edges: unknown boundaries {bad} (known {EDGE_POINTS})')

    def edge(point, t):
        """insert the PRICED die edges of one stage boundary at t (one stage row each); returns the moved time"""
        for e in DE.get(point, []):
            if e['cycles']:
                t = stage_rec(f'die edge @{point}: {e["label"]}', [], t, t + e['cycles'], t, t, e.get('source', ''),
                              grade=e.get('grade', 'PRICED'), die_edge=True)
        return t
    t_ssq = stage_rec('rmsnorm1 SSQ + fused ROOT r (DV)', [0, 2], P[0]['at'], P[0]['at'] + ssq_span, P[0]['at'],
                      P[0]['done'], 'dv_lower (slice_ages.json measured); r of PC2 = fused ROOT (no command)')
    qkv_at = edge('pre_qkv', P[1]['at'])
    qkv_low, qkv_ch, qkv_t0, qkv_land = mv_land('qkv', qkv_at, qkv_at + P[1]['done'] - P[1]['at'])
    t_qkv = stage_rec('qkv matvec L9 -> VM QKV (column tiles + STN)', [1], qkv_at, qkv_land, P[1]['at'], P[1]['done'],
                      f'dv_lower_mat STN (stn_ages.json); tile_first {tile_first} = ME issue -> first far word '
                      '(PARAMETER: no tool compiles the xhead / ROM tile delivery)')
    q0 = edge('pre_qk', max(t_qkv, t_ssq) + MARGIN)
    t_qk = stage_rec('QK-norm / RoPE / v*r -> D2D q,k,v (DV)', list(range(3, 11)), q0, q0 + (qk_end - qk_c0),
                     P[3]['at'], P[10]['done'], 'dv_lower_vec qk (vec_ages.json measured)')
    a0 = edge('pre_attn', t_qk + gap(10, 11))
    if attn_cycles is None:
        t_att = stage_rec('attention (KV die native, PRICED)', [11], a0, a0 + P[11]['done'] - P[11]['at'], P[11]['at'],
                          P[11]['done'], 'ctlm plan price: the KV die step is QW-KVATTN (not composed from a measurement here)')
    else:
        t_att = stage_rec('attention (D2D C2K + KV die + K2C, MEASURED)', [11], a0, a0 + attn_cycles, P[11]['at'],
                          P[11]['done'], f'measured round trip {attn_cycles} (TOKSIM-QW; see cycles.json source)')
    # the attention result's first dr word is taken at the W5 return pin on the PRICED attention done (conservative:
    # the ctlm price already counts its own result landing, plan first landed word = done - 16)
    t_ret = stage_rec('attention return: dr words land (PORTS dd windows) + o_proj x stream (DV)', [11, 12], t_att,
                      t_att + at_span, P[11]['done'] - 16, P[11]['done'],
                      f'dv_lower_vec attn (owners {at_lw["attn_owners"]}): MEASURED first dr word at the W5 pin -> '
                      f'last x word at E5 ({ATTNRET_REC}); priced = the plan landing tail (done - 16 .. done)')
    o_at = edge('pre_o', t_ret + gap(11, 12))
    o_low, o_ch, o_xc, o_t0, o_first_out = mv_ar('o', o_at, o_at + P[12]['done'] - P[12]['at'])
    t_o = stage_rec('o_proj matvec L8 -> AR words + XC (column tiles + STN)', [12, 13], o_at, o_t0 + 255, P[12]['at'],
                    P[13]['done'], 'dv_lower_mat (stagger, XC dst 0)')
    t_ar1 = stage_rec('all-reduce 1 (TP8 collective)', [], o_t0, o_first_out, XCp[0]['at'], XCp[0]['done'] - 256,
                      Q8['source'] + ' : last in -> first out; priced = XC at -> done - 256')
    o_first_out = edge('pre_r1', o_first_out)
    r1_end = o_first_out + (rs_xend - rs_r0)
    t_r1 = stage_rec('residual 1: AR landing + post-scale + add + SSQ + x stream (DV)', [14, 15], o_first_out, r1_end,
                     XCp[0]['done'] - 256, P[15]['done'],
                     f'dv_lower_vec resid ar_order={ar_order} (first AR return word -> last x word at E5)')
    gu_at = edge('pre_gu', t_r1 + gap(15, 16))
    gu_low, gu_ch, gu_t0, gu_land = mv_land('gu', gu_at, gu_at + P[16]['done'] - P[16]['at'])
    t_gu = stage_rec('gate/up matvec L7 -> VM GU (column tiles + STN)', [16], gu_at, gu_land, P[16]['at'], P[16]['done'],
                     'dv_lower_mat STN; tile_first PARAMETER')
    s0 = edge('pre_silu', t_gu + MARGIN)
    t_sl = stage_rec('SiLU x up (GU*r, act stream) (DV)', [17, 18, 19], s0, s0 + (sl_end - sl_c0), P[18]['at'],
                     P[19]['done'], 'dv_lower_vec silu; r of PC17 = fused ROOT of PC15 (no command)')
    d_at = edge('pre_down', t_sl + gap(19, 20))
    d_low, d_ch, d_xc, d_t0, d_first_out = mv_ar('down', d_at, d_at + P[20]['done'] - P[20]['at'])
    t_d = stage_rec('down matvec L8 -> AR words + XC (column tiles + STN)', [20, 21], d_at, d_t0 + 255, P[20]['at'],
                    P[21]['done'], 'dv_lower_mat (stagger, XC dst 0)')
    t_ar2 = stage_rec('all-reduce 2 (TP8 collective)', [], d_t0, d_first_out, XCp[1]['at'], XCp[1]['done'] - 256,
                      Q8['source'])
    d_first_out = edge('pre_r2', d_first_out)
    r2_end = d_first_out + (rs_xend - rs_r0)
    p_end = P[23]['done']
    t_r2 = stage_rec('residual 2 + SSQ + x stream (DV)', [22, 23], d_first_out, r2_end, XCp[1]['done'] - 256, p_end,
                     f'dv_lower_vec resid ar_order={ar_order}')
    # chained: the next layer's qkv issue (its PC1 at) needs the x stream done (+ the plan's PC15 -> PC16 gap)
    period = t_r2 + gap(15, 16) - P[1]['at']
    p_period = rec['period']
    starts = rec['stage_starts_T']
    p_chained = starts[3]['cycle'] - starts[2]['cycle'] if len(starts) > 3 else p_period
    # cold L0: stage-0 embedding (256 words on the D2D return chain, PORTS em windows) before the layer's x exists
    ch0 = M.Chain(smap)
    emb = M.lower_embed(40, ch0)
    emb_cycles = 255 + 8                            # word 0 .. word 255 at the W5 return pin + the 8-edge landing tail
    xs_c0 = min(c['edge'] for c in rs['commands'] if c['label'].startswith('XS'))
    xs_span = rs_xend - xs_c0                       # the x stream of the landed residual (cold: after the embedding)
    l0_cold = emb_cycles + MARGIN + xs_span + gap(15, 16) + (t_r2 - P[1]['at'])
    p_emb = starts[1]['cycle'] - starts[0]['cycle']

    # ---------------- the spliced calendar: every family at its composed time
    ev = {}
    clash = []

    def put(w5, cmd, label, fam_):
        e = w5 - R['R_CMD']
        if e in ev:
            clash.append(dict(edge_w5=w5, a=ev[e][1], b=label))
            return
        ev[e] = (cmd, label, fam_)
    for c in ssq_cmds:
        put(P[0]['at'] + c['edge'] - ssq_e0, int(c['cmd'], 16), c['label'], 'ssq')
    for name, ch in (('qkv', qkv_ch), ('o', o_ch), ('gu', gu_ch), ('down', d_ch)):
        for e, (c, l) in ch.used.items():
            put(e, c, f'{name}: {l}', 'mat')
    shifts = dict(qk=q0 - qk_c0, attn=t_att - at_r0, resid1=o_first_out - rs_r0, silu=s0 - sl_c0,
                  resid2=d_first_out - rs_r0)
    occ = {}
    for key, (mode, dl) in dict(qk=('qk', shifts['qk']), attn=('attn', shifts['attn']),
                                resid1=('resid', shifts['resid1']),
                                silu=('silu', shifts['silu']), resid2=('resid', shifts['resid2'])).items():
        lw, S = fam[mode]
        for c in lw['commands']:
            put(c['edge'] + dl, int(c['cmd'], 16), f'{key}: {c["label"]}', key)
        for k, v in S.occ.items():
            kk = (k[0], k[1], k[2] + dl) if k[0] in ('sc', 'x') else (k[0], k[1] + dl)
            occ.setdefault(kk, []).extend((key,) + tuple(x) for x in v)
    occ_clash = sorted((str(k), v) for k, v in occ.items() if len({x[0] for x in v}) > 1)
    for p in plan:
        if p['kind'] == 'SEG':
            put(p['at'] - C['LOC_EDGES'] + R['R_CMD'], CI.cmdw(1, 2, p['base'], 14), f'SEG base {p["base"]}', 'ctlm')
    events = sorted((e, c, l) for e, (c, l, _) in ev.items())
    try:
        dec = CI.cal_entries(events, C['CAL_S'], C)
        issue = CI.cal_model(dec, C['CAL_S'])
        model = dict(ok=True, entries=len(dec), last_issue=issue[-1])
    except CI.CompileError as e:
        dec = None
        model = dict(ok=False, error=str(e))
    # image capacity: calendar entries (2 PW words each) + slice table words (16 PW words each, TLOAD) under CMD_CEIL
    vec_prog = sum(len(v) for v in rs['prog_stream'].values())
    btab_words = sum(len(v) for v in M.btab_stream(M.btab_layout(own), {n: [1.0] * (own[n]['blocks'][-1]['rows'][1])
                                                                    for n in ('qkv', 'o', 'gu', 'down')}).values())
    cr = V.crom_map(own)
    crom_layer = len(V.crom_table(own, cr, dict(ps1=[1.0] * 4096, ps2=[1.0] * 4096, q_norm=[1.0] * 128,
                                                  k_norm=[1.0] * 128)))
    crom_rope = len(V.crom_table(own, cr, dict(pos=1)))
    n_ent = (len(dec) if dec else len(events)) + len(ssq_boot) + 8
    meta_base = 480
    need_pw = meta_base + 2 * n_ent + 16 * (vec_prog + btab_words + crom_layer)
    cap = dict(cmd_ceil_pw=CI.CMD_CEIL, meta_base_pw=meta_base, decode_entries=len(dec) if dec else None,
               boot_entries_est=len(ssq_boot) + 8, table_words=dict(prog=vec_prog, btab=btab_words,
               crom_per_layer=crom_layer, crom_rope_per_token=crom_rope), pw_needed=need_pw,
               fits=need_pw <= CI.CMD_CEIL)
    if not cap['fits']:
        gaps.append(f'IMAGE CAPACITY: the full layer needs {need_pw} PW words (calendar {2 * n_ent} + tables '
                    f'{16 * (vec_prog + btab_words + crom_layer)} = (PROG {vec_prog} + BTAB {btab_words} + CROM '
                    f'{crom_layer}) x 16) > CMD_CEIL {CI.CMD_CEIL}: tt_ctlm cannot hold one layer\'s slice tables + '
                    'calendar; and CROM post-scales / norm gains differ per layer (36 x) -> a per-layer table stream '
                    '(ROM-resident slice tables or a table DMA) is needed')
    if clash:
        gaps.append(f'CALENDAR: {len(clash)} W5 command-edge clashes between families (first {clash[:2]})')
    if occ_clash:
        gaps.append(f'OCCUPANCY: {len(occ_clash)} shared-chain slots used by two families (first {occ_clash[:2]})')
    if not model['ok']:
        gaps.append(f'cmd_cal model: {model["error"]}')
    gaps += [
        'COLUMN-HEAD x CONSUMER: the qkv / gu / down / o matvecs read x from the slice x stream; the hr / xpf control '
        'that makes the column heads tap those words on the compiled edges is not lowered (QLB-C4b/3a left)',
        f'TILE DELIVERY: tile_first {tile_first} (ME issue -> first far cluster word) and the AR stagger (slice s gets '
        'block b at M0 + 8 b + j - 26 - 2 s) are a contract no tool compiles into the ME / xhead calendar',
        'PER-TOKEN RoPE ROW: cos / sin of the position must reach CROM ROPE every token; TLOAD plays static image '
        'blocks only (no producer of the per-token row on the die)',
        'AR TAG CONTRACT (dv_lower_mat RTL gap): io_collective needs tag == cmd tag on every word and last only on the '
        'message last word; slice2 sends tag = row address, last per STN op (fault_code[2])',
    ]
    # XC order: the production decode calendar is THIS spliced calendar (ctlm_image's XC after END is the priced plan
    # only and is not emitted here).  Check every lowered XC is in it, XC_TO_WORD0 + xc_cc edges before its word 0.
    xc_bad = []
    for name, x, t0 in (('o', o_xc, o_t0), ('down', d_xc, d_t0)):
        e = x['entry'] - R['R_CMD']
        if x['cc_edge'] != t0 - M.XC_TO_WORD0 or x['entry'] != x['cc_edge'] - ages['xc_cc'] or e not in ev \
                or not ev[e][1].startswith(f'{name}: XC'):
            xc_bad.append(dict(matvec=name, entry=x['entry'], cc_edge=x['cc_edge'], word0=t0))
    if xc_bad:
        gaps.append(f'XC ORDER: lowered XC not before word 0 in the spliced calendar {xc_bad}')
    else:
        notes.append('XC ORDER: CLOSED in the spliced calendar (o / down XC at word0 - XC_TO_WORD0 - xc_cc: '
                     f'{o_xc["entry"]} / {d_xc["entry"]} vs word0 {o_t0} / {d_t0}); ctlm_image XC-after-END is the '
                     'priced plan only and is not emitted')
    if ar_order == 'slice':
        gaps.append('AR RETURN ORDER: dv_lower_vec slice-major landing != io_collective message (row) order')
    out = dict(
        schema='opentallas.qwen.dv-layer-composition.v1', tool='tools/qwen_layerbench/dv_layer.py', stage=stage,
        qualification=dict(status='UNMEASURED', measured_layer_cycles=None,
                           reason='Analytic diagnostic only: unresolved native paths, image capacity, '
                                  'priced attention and tile delivery prevent a production layer run.'),
        die='dv2f14bi (lane ages ' + lane_ages + ')', tile_first=tile_first, ar_order=ar_order,
        composition=dict(
            rule='stages in dependency order; each lowered family span from its own compiled schedule (RTL-measured '
                 'ages, benched on its edges); the ctlm plan gaps between dependent ops kept; attention = ctlm price '
                 '(KV die); all-reduce = measured TP8 collective E (+2 LS 378); chained period = residual-2 x '
                 'stream end + PC15->PC16 gap - PC1 issue; L0 cold = stage-0 embedding + layer latency',
            stages=st, layer_latency=t_r2, chained_period=period, priced_chained_period=p_chained,
            priced_plan_period=p_period, l0_cold=l0_cold, l0_cold_rule='embedding 256 words landed + x stream (resid XS span) + PC15->PC16 gap + layer (qkv issue .. residual-2 x stream end)', l0_cold_priced=p_emb + p_end,
            embed_stage0=dict(cycles=emb_cycles, priced=p_emb, rule=emb['rule']), xs_span=xs_span, tile=tile_note, tile_mode=tile_mode,
            lowered_minus_priced=t_r2 - p_end),
        calendar=dict(model=model, entries=len(events), clashes=clash[:20], occupancy_clashes=occ_clash[:20],
                      shifts=shifts, families={k: sum(1 for v in ev.values() if v[2] == k)
                                               for k in ('ssq', 'mat', 'qk', 'attn', 'resid1', 'silu', 'resid2',
                                                         'ctlm')}),
        capacity=cap, gaps=gaps, notes=notes,
        events=[dict(edge_w5=e + R['R_CMD'], cmd=f'{c:029x}', label=l) for e, c, l in events])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--stage', type=int, default=1)
    ap.add_argument('--tile-first', type=int, default=40)
    ap.add_argument('--ar-order', default='row', choices=('row', 'slice'))
    ap.add_argument('--lane-ages', default=LANE_AGES)
    ap.add_argument('--tile-mode', default='priced', choices=('priced', 'first', 'measured'),
                    help='priced: the column-tile matvec time = the ctlm ME price (results no earlier than the priced '
                         'done); first: tile_first only (DV-side lower bound)')
    a = ap.parse_args()
    r = compose(a.stage, a.tile_first, a.ar_order, a.lane_ages, a.tile_mode)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(r, indent=1) + '\n')
    c = r['composition']
    print(json.dumps(dict(stage=a.stage, layer_latency=c['layer_latency'], chained=c['chained_period'],
                          priced_chained=c['priced_chained_period'], l0_cold=c['l0_cold'],
                          calendar=r['calendar']['model'], clashes=len(r['calendar']['clashes']),
                          capacity_fits=r['capacity']['fits'], gaps=len(r['gaps']))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
