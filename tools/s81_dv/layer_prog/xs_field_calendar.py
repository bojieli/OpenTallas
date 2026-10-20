#!/usr/bin/env python3
"""S81-CALPIPE (owner 10-20 03:04 "Go with the compiler schedule gaps immediately"): the PIPELINED multi-phase slice
x-streamer calendar of EVERY multi-phase field matvec of a layer, compiled by the S81-DV die compiler
(dv_layer_compile.py -> lower_xs -> xs_place.lower_placed / lower_placed_bf), plus the layer field image and the
static schedule checks (op level, layer level, multi-user slot calendar).

Generalises S81-RATEFIX xs_calendar.compile_pipeline / S81-WQBP xs_wqb_die.wqb_calendar (attn.wq_b P126) to all
ops: phase n+1's operand stream is issued while phase n reduces (phase n launched at tg0 + n * P, element configuration
double-buffered on tags 0/2, cfg = launch - cfg_lead, accept = cfg - 10, retire = last stream row + ADDR_LEAD + 6).
The period of each op is its MEASURED floor on the release frame RTL (tb_toksim_fgu_seq / fullsix, Verilator 5.050,
release 19bf4121e frame exes); a period below it is a COMPILE FAULT (CalendarFault), never a runtime stall:

  op                fam   floor  first FAIL      measured span law (go0 -> last frame-root RET)      evidence
  attn.wq_b         fp8   126    124 (Q_LIFETIME) (n-1) P + 223 (capture->RET, fullsix)             S81-RATEFIX / WQBP
  attn.idx.q        fp8   126    125 (FAULT 11)  (n-1) P + 295                                     TOKSIM-S81C/FSEQ
  attn.wo_b         fp8   127    126 (4 words)   (n-1) P + 320  (u_f_0L01 P127 701, L00 699)       S81-CALPIPE wob
  ffn.shared_gu     fp8   146    145 (FAULT)     (n-1) P + 360                                     TOKSIM-S81B/FGU
  ffn.experts_gu    fp8   145    144 (FAULT)     (n-1) P + 345                                     TOKSIM-S81B/FGU, S81C/FSGU
  ffn.down          fp8   130    125 (FAULT 11)  (n-1) P + 289                                     TOKSIM-S81B/FDOWN, S81C/FSDN
  attn.wo_a         bf16  231    230 (seg label) (n-1) P + 352  (12 ph, P231 2893)                 S81-WQBP pipe3
  ffn.router        bf16  231    230 (seg label) (n-1) P + 345  (5 ph, P231 1269)                  TOKSIM-S81C/FSEQ
  attn.cmp.wk       bf16  --     single phase a layer (nothing to pipeline)
BF16 ops carry a second hard rule: a BF go < 231 edges after the previous BF go relabels the previous phase's open
segment (the return word carries the LATEST configuration's segment index; RTL schedule constraint, FSEQ 10-19 NOTICE):
BF_SEG_LABEL_FLOOR, checked on every BF calendar.  Widening that tag is RTL (rate-gap F4, owner LEAD4-S81 frame).

Operand buffers (the brief's STOP condition): every op above already HAS the second operand buffer the overlap needs --
the element configuration banks are double-buffered (tags 0/2, cfg7 swap) and the x of the op stays resident in the
slice xs / frame VM for all its phases (FP8: one x for every phase; BF16: one K segment per phase, all segments of the
op's x resident, PHASE_VM reload at go measured).  No RTL change is needed for any op here.

STATIC CHECKS (every emission; a failed check raises CalendarFault):
  op level     rows time-ordered / unique / <= 4096, t < 2^24; one stream request an edge, stream windows of consecutive
               phases disjoint; tag reuse only after its retire; stream addresses inside the stream ROM; is_d delay
               line <= ND; period >= the op's measured floor; launch spacing == period; FP8 element constraints of
               compile_pipeline (P >= 88, 2 P >= 195 + cfg_lead, cfg_lead >= 48); BF: spacing >= BF_SEG_LABEL_FLOOR.
  layer level  the op segments of one slice field in execution order: an op's first accept after the previous op's
               last retire (tags / element banks / stream port / CAP domain never shared by two ops); calendar ROM
               rows of all segments <= 4096; is_d words on distinct edges, delay line <= ND over the whole layer.
  multi-user   (mu_check) the MU slot calendar (dv_mu_calendar, 46 AR / 10+1 MTP): user k runs the layer at
               shift_k; every field window of every user, expanded modulo the period, must be disjoint from every other
               user's on the same die field (brute force), and every user's field busy span <= the slot spacing.

    xs_field_calendar.py die --fixtures-root D --die-src S --out DIR [--layers L0 L2 L14 L20] [--slice u_s_0S]
                             [--period OP=P ...] [--allow-below-floor] [--mu-cal CAL.json ...] [--schedule SCHED.json]
    xs_field_calendar.py selftest     # the negative controls of the static checker (no fixtures needed)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault('HDC_V41_ARITH', 'chunk8')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import xs_calendar as XC  # noqa: E402

CFG_LEAD = 52
BF_SEG_LABEL_FLOOR = 231
FLOORS = {     # op: (family, measured floor period, first FAIL, span tail (go0 -> last RET beyond (n-1) P), evidence)
    'attn.wq_b': ('fp8', 126, 124, 223, 'claude/s81-ratefix-1019@ff8fa3745 p126c52 PASS / p124c50 FAIL; claude/s81-wqbp-1020'),
    'attn.idx.q': ('fp8', 126, 125, 295, 'claude/toksim-s81c-fseq-1019 (lanes/TOKSIM-S81C-FSEQ.md: 6-phase PASS 8/8 to P126, P125 FAULT)'),
    'attn.wo_b': ('fp8', 127, 126, 320, 'results/rtl/s81_calpipe_1020/wob (u_f_0L00 / 0L01 P127 PASS 699 / 701, P126 FAIL 4 words)'),
    'ffn.shared_gu': ('fp8', 146, 145, 360, 'results/rtl/toksim_s81b_fgu_1019/job5 P146 PASS 798, job4 P145 FAIL'),
    'ffn.experts_gu': ('fp8', 145, 144, 345, 'TOKSIM-S81B/FGU + S81C/FSGU: 24 phases P145 3680, P144 FAULT'),
    'ffn.down': ('fp8', 130, 125, 289, 'TOKSIM-S81B/FDOWN + S81C/FSDN: 21 phases P130 2889, P125 FAULT 11'),
    'attn.wo_a': ('bf16', 231, 230, 352, 'results/rtl/s81_wqbp_1020/pipe3: 12 phases P231 2893 / 2886 PASS, P230 FAIL'),
    'ffn.router': ('bf16', 231, 230, 345, 'TOKSIM-S81C/FSEQ: 5 phases P231 1269 PASS 6/6 frames, P230 FAIL'),
}
SERIAL_ONLY = {'attn.cmp.wk': 'one BF phase a layer: nothing to overlap', 'eng.wkv': 'not a field matvec calendar here'}
# execution order of the field ops inside a layer (DAG order; the field is one resource)
EXEC_ORDER = ['attn.wq_b', 'attn.idx.q', 'attn.cmp.wk', 'attn.wo_a', 'attn.wo_b', 'ffn.router', 'ffn.shared_gu',
              'ffn.experts_gu', 'ffn.down']


class CalendarFault(AssertionError):
    pass


def _t(w):
    return w >> 75


def op_calendar(op, phase, stream, phases, slc=0, period=None, cfg_lead=CFG_LEAD, allow_below_floor=False):
    """the pipelined slice xs calendar of one op's field phases (global field phase indices `phases` into the phase
    ROM words `phase` / stream ROM words `stream`).  Returns rows, segment-relative is_d words, per-phase records,
    static checks and the predicted span."""
    fam, floor, _fail, tail, _ev = FLOORS[op]
    P = floor if period is None else period
    try:
        pipe = XC.compile_pipeline(phase, stream, list(phases), slc, P, cfg_lead=cfg_lead)
    except AssertionError as e:          # compile_pipeline's own structural asserts (stream overlap, tag reuse)
        raise CalendarFault(('compile_pipeline refused', op, P, str(e)[:200]))
    per = []
    for p in pipe['phases']:
        pw = XC.phase_word(phase, p['phase'])
        if bool(pw['bf']) != (fam == 'bf16'):
            raise CalendarFault(('phase family differs from the op family', op, p['phase'], pw['bf']))
        per.append(dict(p, sbase=pw['sbase']))
    cal = dict(op=op, fam=fam, mode='pipeline', period=P, cfg_lead=cfg_lead, packed=list(pipe['packed']),
               iss=dict(pipe['iss']), phases=per, stream_words=len(stream), nphases=len(per), cal_rows=pipe['cal_rows'],
               floor=floor)
    cal['static'] = static_checks(cal, allow_below_floor)
    cal['predicted_span'] = (len(per) - 1) * P + tail
    return cal


def static_checks(cal, allow_below_floor=False):
    P, per, op = cal['period'], cal['phases'], cal['op']
    out, bad = {}, []

    def need(name, ok, detail=None):
        out[name] = bool(ok)
        if not ok:
            bad.append((name, detail))
    ts = [_t(w) for w in cal['packed']]
    need('rows_le_4096', len(ts) <= 4096, len(ts))
    need('rows_time_ordered_unique', all(a < b for a, b in zip(ts, ts[1:])) and ts and ts[-1] < (1 << 24))
    st = sorted((p['stream'][0], p['stream'][1]) for p in per)
    need('streams_disjoint', all(a[1] + XC.ADDR_LEAD < b[0] for a, b in zip(st, st[1:])), st[:3])
    live = {}
    for p in per:
        live.setdefault(p['tag'], []).append((p['accept'], p['retire']))
    need('tag_reuse_after_retire', all(a[1] < b[0] for iv in live.values() for a, b in zip(sorted(iv), sorted(iv)[1:])))
    need('tag0_even_x_parity', all(p['tag'] & 1 == 0 for p in per))
    need('stream_addr_in_rom', all(p['sbase'] + p['nb'] <= cal['stream_words'] for p in per) and cal['stream_words'] <= 16384)
    its = sorted(cal['iss'])
    need('isd_delay_line_le_ND', all(len([j for j in its if j <= i < j + XC.OFF + 2]) <= XC.ND for i in its))
    need('launch_spacing_eq_period', all(b['launch'] - a['launch'] == P for a, b in zip(per, per[1:])))
    need('pipe_replay_period_ge_88', P >= 88)
    need('pipe_cfg_window_2P_ge_195_plus_cfg_lead', 2 * P >= 195 + cal['cfg_lead'])
    need('pipe_cfg_lead_ge_48', cal['cfg_lead'] >= 48)
    need('period_ge_measured_floor', P >= cal['floor'], (op, P, cal['floor']))
    if cal['fam'] == 'bf16':
        need('bf_go_spacing_ge_seg_label_floor_231', P >= BF_SEG_LABEL_FLOOR, P)
    soft = {'period_ge_measured_floor', 'bf_go_spacing_ge_seg_label_floor_231'}
    hard = [b for b in bad if not (allow_below_floor and b[0] in soft)]
    if hard:
        raise CalendarFault((op + ' calendar compile fault', hard))
    return dict(checks=out, PASS=not bad, below_floor_negative_control=bool(bad) and not hard)


def layer_calendar(cals, starts=None, gap=0):
    """one slice field image of a layer: op segments in EXEC_ORDER, each started by its own is_d PRIME/START at the
    op start (starts[op], edges; default ASAP = the previous op's last retire + 1 + gap, the field-limited packing).
    Checks: segment windows disjoint and ordered (first accept > previous last retire), total rows <= 4096, is_d
    edges unique, delay line <= ND over the layer.  Returns the packed rows, absolute issuers and per-op windows."""
    order = [c for o in EXEC_ORDER for c in cals if c['op'] == o]
    nrows = sum(len(c['packed']) for c in order)
    segmented = os.environ.get('OT_XS_CAL_SEGMENT', '0') == '1'
    if nrows > 4096 and not segmented:      # ot_s81sl_xs pq_calendar ROM = one ot_rom_4096x72_m8 pair; is_d base field 12 b
        raise CalendarFault(('layer calendar compile fault', [('layer_rows_le_4096', nrows,
                             {c['op']: len(c['packed']) for c in order})]))
    packed, iss, win, bad = [], {}, [], []
    t_free = None
    for n, c in enumerate(order):
        a0 = min(p['accept'] for p in c['phases'])
        r1 = max(p['retire'] for p in c['phases'])
        if starts and c['op'] in starts:
            S = starts[c['op']]
        else:
            S = 0 if t_free is None else t_free - a0 + 1 + gap
        base = len(packed)
        packed.extend(c['packed'])
        for t, v in c['iss'].items():
            if t == XC.T_OFFCFG and n:
                continue
            if t in (XC.TS - 20, XC.TS):
                v = XC.isd(**({'prime': 1} if t == XC.TS - 20 else {'start': 1}), base=base, length=len(c['packed']))
            T = S + t
            if T in iss:
                bad.append(('isd_edge_reused', c['op'], T))
            iss[T] = v
        abs_a0, abs_r1 = S + XC.TS + XC.GO_LAT + a0, S + XC.TS + XC.GO_LAT + r1
        if t_free is not None and not abs_a0 > t_free_abs:
            bad.append(('op_segments_overlap', order[n - 1]['op'], c['op'], t_free_abs, abs_a0))
        win.append(dict(op=c['op'], start=S, base=base, rows=len(c['packed']), first_accept=abs_a0, last_retire=abs_r1,
                        nphases=c['nphases'], period=c['period']))
        t_free, t_free_abs = S + r1, abs_r1
    if len(packed) > 4096 and not segmented:
        bad.append(('layer_rows_le_4096', len(packed)))
    its = sorted(iss)
    if not all(len([j for j in its if j <= i < j + XC.OFF + 2]) <= XC.ND for i in its):
        bad.append(('layer_isd_delay_line_le_ND',))
    if bad:
        raise CalendarFault(('layer calendar compile fault', bad))
    if segmented:
        from xs_calendar_pack import pack_layer
        try:
            result = pack_layer(order, {w['op']: w['start'] for w in win})
        except AssertionError as e:
            raise CalendarFault(('segmented calendar compile fault', str(e))) from e
        return dict(result, windows=win)
    return dict(packed=packed, iss=iss, windows=win, rows=len(packed), PASS=True)


def mu_check(windows, shifts, period, slot):
    """brute force: user k's field windows = windows moved by shift_k, modulo period; disjoint across users on the
    same field; every user's field busy span <= slot spacing (the shift lemma's premise)."""
    iv = []
    for k, s in enumerate(shifts):
        for w in windows:
            a, b = (w['first_accept'] + s) % period, (w['last_retire'] + s) % period
            iv += [(a, b, k, w['op'])] if a <= b else [(a, period - 1, k, w['op']), (0, b, k, w['op'])]
    iv.sort()
    coll = [(x, y) for x, y in zip(iv, iv[1:]) if y[0] <= x[1] and x[2] != y[2]]
    busy = max(w['last_retire'] for w in windows) - min(w['first_accept'] for w in windows)
    return dict(users=len(shifts), period=period, slot=slot, windows=len(iv), field_busy_span=busy,
                premise_busy_le_slot=busy <= slot, collisions=len(coll), first=coll[:2],
                PASS=not coll and busy <= slot)


def write_layer_images(lc, phase, stream, out):
    from pq_calendar import viamap
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    cw = lc['packed']
    (out / 'pq_calendar_action.viamap.hex').write_text(viamap([w & ((1 << 72) - 1) for w in cw] + [0] * (4096 - len(cw))))
    (out / 'pq_calendar_time.viamap.hex').write_text(viamap([w >> 72 for w in cw] + [0] * (4096 - len(cw))))
    (out / 'pq_phase0.viamap.hex').write_text(viamap(list(phase)[:4096] + [0] * (4096 - min(4096, len(phase)))))
    s = list(stream) + [0] * (16384 - len(stream))
    for b in range(4):
        (out / f'pq_stream{b}.viamap.hex').write_text(viamap(s[b * 4096:(b + 1) * 4096]))
    (out / 'is_d.txt').write_text(''.join(f'{t} {v:040x}\n' for t, v in sorted(lc['iss'].items())))
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file()}


def record(cal):
    keep = ('op', 'fam', 'mode', 'period', 'cfg_lead', 'floor', 'nphases', 'cal_rows', 'stream_words', 'static',
            'predicted_span')
    r = {k: cal[k] for k in keep if k in cal}
    r['phases'] = [{k: p[k] for k in ('phase', 'tag', 'accept', 'cfg', 'launch', 'stream', 'retire', 'nb', 'stall_edges')}
                   for p in cal['phases']]
    r['floor_evidence'] = FLOORS[cal['op']][4]
    r['predicted_span_definition'] = ('spine go of the first phase -> last frame-root RET word = (nphases - 1) x period + '
                                      f'{FLOORS[cal["op"]][3]} (measured law); die wire / CAP tail not included')
    return r


# ------------------------------------------------------------------------------------------------ field of a frame
_FIELD = {}


def frame_field(die, frame, fixd, ops, iters=None):
    """the frame's multi-phase field (xs_place.compile_frame, every phase legalised as compiled): phase ROM words,
    stream ROM words, per-op global phase indices.  Cached per (frame, fixtures, ops)."""
    import xs_place as XP
    import v41_die_images_w17w10 as I
    import lower_xs as LX
    key = (frame, str(fixd), tuple(ops))
    if key not in _FIELD:
        rec, field = XP.compile_frame(die, frame, fixd, list(ops), iters=iters or LX.ITERS)
        phase = []
        for ph in field.phases:
            phase += list(I.phase_words(ph))
        if os.environ.get('OT_XS_CAL_SEGMENT', '0') == '1':
            from xs_calendar_pack import dedup_stream
            phase, stream = dedup_stream(phase, list(field.stream))
        else:
            stream = list(field.stream)
        by_op = {}
        for p in rec['phases']:
            by_op.setdefault(p['op'], []).append(p['phase'])
        _FIELD[key] = (phase, stream, by_op, rec)
    return _FIELD[key]


def compile_ops(die, sl, fixd, layer, periods=None, allow_below_floor=False, iters=None):
    import xs_place as XP
    ops = XP.XS_OPS.get(layer, XP.XS_OPS['L0']) + XP.BF_OPS.get(layer, XP.BF_OPS['L0'])
    fr0 = die.frames_of(sl)[0]
    phase, stream, by_op, rec = frame_field(die, fr0, fixd, ops, iters)
    g = __import__('lower_xs').slice_index(die, sl)
    cals, skipped = [], {}
    for op in ops:
        phs = by_op.get(op, [])
        if op not in FLOORS:
            skipped[op] = SERIAL_ONLY.get(op, 'no measured floor') + f' ({len(phs)} phases)'
            continue
        if len(phs) < 2:
            skipped[op] = f'{len(phs)} phase(s): nothing to overlap'
            continue
        cals.append(op_calendar(op, phase, stream, phs, slc=g, period=(periods or {}).get(op),
                                allow_below_floor=allow_below_floor))
    return dict(ops=ops, frame=fr0, phase=phase, stream=stream, by_op=by_op, cals=cals, skipped=skipped,
                field_phases=len(rec['phases']))


def emit_files(die, op, ctx, sl):
    """lower_placed / lower_placed_bf hook: the op's pipelined calendar (compiled with the layer's whole frame field so
    the phase indices / stream bases are the die-true global ones) -> {file: text}, nphases; None when the op has no
    multi-phase calendar (single phase / no floor).  CalendarFault propagates (a compile fault)."""
    from pq_calendar import viamap
    name = op['op']
    if name not in FLOORS:
        return None, SERIAL_ONLY.get(name, 'no measured floor')
    r = compile_ops(die, sl, ctx['fixtures'], ctx.get('layer', 'L0'), ctx.get('field_periods'))
    cal = next((c for c in r['cals'] if c['op'] == name), None)
    if cal is None:
        return None, r['skipped'].get(name, 'not compiled')
    try:
        lc = layer_calendar(r['cals'])
        lw, lfault = next(w for w in lc['windows'] if w['op'] == name), None
    except CalendarFault as e:       # the whole-layer image exceeds the 4096-row calendar ROM: op segment stands alone
        lc, lw, lfault = dict(rows=sum(len(c['packed']) for c in r['cals']), PASS=False), None, str(e)[:600]
    rec = dict(record(cal), schema='opentallas.s81_dv.xs_field_calendar.op.v1', layer=ctx.get('layer'), slice=sl,
               compiler_emitted=True, layer_window=lw, layer_rows=lc['rows'], layer_static_PASS=lc['PASS'],
               layer_fault=lfault)
    cw = cal['packed']
    files = {f'prog/xs/{op["id"]}.calendar.json': json.dumps(rec, indent=1) + '\n',
             f'prog/xs/{op["id"]}/pq_calendar_action.viamap.hex': viamap([w & ((1 << 72) - 1) for w in cw] + [0] * (4096 - len(cw))),
             f'prog/xs/{op["id"]}/pq_calendar_time.viamap.hex': viamap([w >> 72 for w in cw] + [0] * (4096 - len(cw))),
             f'prog/xs/{op["id"]}/is_d.txt': ''.join(f'{t} {v:040x}\n' for t, v in sorted(cal['iss'].items()))}
    return files, cal


def cmd_die(a):
    import dv_layer_compile as C
    out = Path(a.out)
    if out.exists():
        raise SystemExit('REFUSE_EXISTING_RUN_DIR')
    die = C.Die(C.die_tree(a.die_ref, a.die_src))
    periods = dict((k, int(v)) for k, v in (x.split('=') for x in a.period))
    summary = dict(schema='opentallas.s81_dv.xs_field_calendar.v1', slice=a.slice, periods_override=periods, layers={})
    mu = [json.loads(Path(f).read_text()) for f in a.mu_cal]
    rc = 0
    for L in a.layers:
        try:
            r = compile_ops(die, a.slice, str(Path(a.fixtures_root) / L), L, periods, a.allow_below_floor, a.iters)
        except CalendarFault as e:
            print('XS_FIELD_CAL_FAULT', L, str(e)[:400])
            summary['layers'][L] = dict(fault=str(e)[:2000])
            rc = 1
            continue
        d = out / L
        d.mkdir(parents=True, exist_ok=True)
        ops_rec = {c['op']: record(c) for c in r['cals']}
        try:
            lc = layer_calendar(r['cals'])
        except CalendarFault as e:
            # op calendars are valid one by one; the WHOLE layer image does not fit (ROM capacity): reported, and
            # each op segment is emitted on its own (one segment resident at a time)
            print('XS_FIELD_LAYER_FAULT', L, str(e)[:400])
            rc = 1
            (d / 'field_calendar.json').write_text(json.dumps(dict(layer=L, slice=a.slice, frame=r['frame'], ops=ops_rec,
                                                                   skipped=r['skipped'], layer_fault=str(e)), indent=1) + '\n')
            win, t = [], 0
            for c in [c for o in EXEC_ORDER for c in r['cals'] if c['op'] == o]:       # ASAP windows, per segment
                a0 = min(p['accept'] for p in c['phases']); r1 = max(p['retire'] for p in c['phases'])
                win.append(dict(op=c['op'], first_accept=t, last_retire=t + r1 - a0)); t += r1 - a0 + 1
            lc = dict(rows=sum(len(c['packed']) for c in r['cals']), PASS=False, windows=win, fault=str(e)[:600])
        else:
            shas = write_layer_images(lc, r['phase'], r['stream'], d)
            (d / 'field_calendar.json').write_text(json.dumps(dict(layer=L, slice=a.slice, frame=r['frame'], ops=ops_rec,
                                                                   skipped=r['skipped'], layer_windows=lc['windows'],
                                                                   rows=lc['rows'], images=shas), indent=1) + '\n')
        mus = []
        for m in mu:
            shifts = [s['shift'] for s in m['slots']]
            mus.append(dict(mode=m['mode'], **mu_check(lc['windows'], shifts, m['period'], m['slot'])))
        summary['layers'][L] = dict(frame=r['frame'], field_phases=r['field_phases'], skipped=r['skipped'],
                                    ops={o: dict(nphases=v['nphases'], period=v['period'], floor=v['floor'],
                                                 predicted_span=v['predicted_span'],
                                                 serial_span=FLOORS[o][3] * v['nphases'],
                                                 static_PASS=v['static']['PASS'],
                                                 negative_control=v['static']['below_floor_negative_control'])
                                         for o, v in ops_rec.items()},
                                    layer=dict(rows=lc['rows'], PASS=lc['PASS'], windows=lc['windows'],
                                               fault=lc.get('fault')), mu=mus)
        print('XS_FIELD_CAL', L, json.dumps({o: (v['nphases'], v['period'], v['predicted_span']) for o, v in ops_rec.items()}),
              'layer_rows', lc['rows'], 'mu', [(m['mode'], m['PASS'], m['collisions']) for m in mus])
    out.mkdir(parents=True, exist_ok=True)
    (out / 'die_field_calendar.json').write_text(json.dumps(summary, indent=1) + '\n')
    print('XS_FIELD_CAL_DONE rc', rc)
    return rc


# ------------------------------------------------------------------------------------------------ selftest
def _synthetic(op, n, nb=24):
    """a synthetic phase / stream ROM of n phases of nb stream words (q family: unit u word = 1 | u << 1, sv 3)"""
    fam = FLOORS[op][0] == 'bf16'
    phase, stream = [], []
    for k in range(n):
        sb = len(stream)
        for i in range(nb):
            stream.append(1 | (1 << 4) | (min(i, 7) << 8) if fam else 1 | (3 << 12))
        K = 1024 if fam else 64 * nb
        phase += [int(fam) | K << 1 | nb << 14 | sb << 30 | 6 << 46, 0]
    return phase, stream


def cmd_selftest(a):
    res = {}

    def expect(name, fn, fault):
        try:
            v = fn()
            ok = not fault
            res[name] = dict(expected='FAULT' if fault else 'PASS', got='PASS', ok=ok, info=v)
        except CalendarFault as e:
            res[name] = dict(expected='FAULT' if fault else 'PASS', got='FAULT', ok=fault, info=str(e)[:300])
    cals = {}
    for op in FLOORS:
        ph, st = _synthetic(op, 6)
        cals[op] = (ph, st)
        expect(f'{op}@floor', lambda op=op, ph=ph, st=st: op_calendar(op, ph, st, range(6))['predicted_span'], False)
        expect(f'{op}@floor-1', lambda op=op, ph=ph, st=st: op_calendar(op, ph, st, range(6), period=FLOORS[op][1] - 1), True)
    ph, st = cals['attn.wo_a']
    expect('wo_a@230_allow_below_floor_still_flags', lambda: op_calendar('attn.wo_a', ph, st, range(6), period=230,
                                                                         allow_below_floor=True)['static']['PASS'], False)
    ph, st = _synthetic('attn.wo_b', 6, nb=140)
    expect('wo_b@floor_stream_longer_than_period', lambda: op_calendar('attn.wo_b', ph, st, range(6)), True)
    ph, st = cals['attn.wo_b']
    expect('wo_b_family_mismatch_as_bf', lambda: op_calendar('attn.wo_a', ph, st, range(6)), True)
    c1 = op_calendar('attn.wo_b', *cals['attn.wo_b'], range(6))
    c2 = op_calendar('ffn.down', *cals['ffn.down'], range(6))
    expect('layer_asap', lambda: layer_calendar([c1, c2])['rows'], False)
    expect('layer_overlap_injected', lambda: layer_calendar([c1, c2], starts={'attn.wo_b': 0, 'ffn.down': 300}), True)
    lc = layer_calendar([c1, c2])
    expect('mu_46_slot_spacing', lambda: (lambda m: m if m['PASS'] else (_ for _ in ()).throw(CalendarFault(m)))(
        mu_check(lc['windows'], [k * 21504 for k in range(46)], 989260, 21505.7)), False)
    expect('mu_shift_collision_injected', lambda: (lambda m: m if m['PASS'] else (_ for _ in ()).throw(CalendarFault(m)))(
        mu_check(lc['windows'], [0, 400] + [k * 21504 for k in range(2, 46)], 989260, 21505.7)), True)
    ok = all(v['ok'] for v in res.values())
    for k, v in res.items():
        print('SELFTEST', 'ok ' if v['ok'] else 'BAD', k, 'expected', v['expected'], 'got', v['got'])
    if a.out:
        Path(a.out).write_text(json.dumps(dict(PASS=ok, cases=res), indent=1, default=str) + '\n')
    print('SELFTEST', 'PASS' if ok else 'FAIL', len(res))
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('die')
    p.add_argument('--fixtures-root', required=True)
    p.add_argument('--die-src', default=None)
    p.add_argument('--die-ref', default='origin/main')
    p.add_argument('--out', required=True)
    p.add_argument('--layers', nargs='+', default=['L0', 'L2', 'L14', 'L20'])
    p.add_argument('--slice', default='u_s_0S')
    p.add_argument('--period', nargs='*', default=[], help='OP=P overrides (negative controls)')
    p.add_argument('--allow-below-floor', action='store_true')
    p.add_argument('--mu-cal', nargs='*', default=[])
    p.add_argument('--iters', type=int, default=None)
    s = sp.add_parser('selftest')
    s.add_argument('--out', default=None)
    a = ap.parse_args(argv)
    return {'die': cmd_die, 'selftest': cmd_selftest}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
