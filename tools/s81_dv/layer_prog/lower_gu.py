#!/usr/bin/env python3
"""LB2-S81/CC-GU (10-18): lowering of the G-unit (dsdv_gunit, die instance u_gunit) ops of one layer.

Ops (dv_layer_price names):  (attn|ffn).hc.(sumsq|fn|rsqrt|pre_post|sinkhorn)  -> one HC job per prefix
                             ffn.(top6|top6_order|weights)                      -> one router job
NOT claimed here (owned by the vs fork): ffn.softplus_sqrt (vs op 10 RA), ffn.bias (vs op 11 RB).  The G-unit router adds
the gate bias itself inside its select (dsdv_gunit_l1 u_sel ot_dsrom_su_bias_select), so the router job only needs the
post-allgather sqrt(softplus) scores as SC beats; vs RB's scores + bias row is not an input of the gunit.

Every encoding below is read from the BUILT RTL of record (origin/main; rtl/dsrom_sys/s81_dv/unit, byte-identical here):
  cw table row  (a10, d256) via host CSR 0x14 (dsdv_seq_host.sv:31-33 header, :130 csr_g, :126-127 cf_o -> :328-329 cw)
    a = {0, set, 2'b00, row 6}  (a[9] = 0 table write; set = a[8])
    rows 0..55   d[32 j +: 32] = gate bias[8 row + j]                                 dsdv_gunit_l1.sv:58-59
    rows 56..61  56 + 3 w + i: d[32 j +: 32] = hc_<w>_base[8 i + j] (w 0 attn, 1 ffn) dsdv_gunit_l5.sv:58-60
    row 62       [255:224] norm eps (L4)                                              dsdv_gunit_l4.sv:76-77
                 [223:192] route_scale (L1)                                           dsdv_gunit_l1.sv:60
                 [191:96] ffn scales 2..0, [95:0] attn scales 2..0 (L5)               dsdv_gunit_l5.sv:61
  gunit job     calendar engine 2, arg = {kind [7], template [6:0]} -> cw {1, {2'b10, 7'b0, kind}, {214'b0, tmpl[41:0]}}
                (dsdv_seq_host.sv:21-22, :311 rg_t, :328-329)
    router job  kind 0: {set [40], ne [39:31], row [30:21], lmask [20:16], smask [15:0]}  dsdv_gunit_l1.sv:65, :96
    HC job      kind 1: {which [41], set [40], row [30:21], lmask [20:16], smask [15:0]}  dsdv_gunit_l0.sv:74, :101
  HP beat (slice -> gunit, kind 7)   [0] 1, [3:1] 7, [12:9] src sid, [40 +: 5] acc (0..23 fn row, 24 sum of squares),
                [45 +: 4] g = slice sid, [49] h, [51:50] 0, [52 + 32 j +: 32] j 0..2 copy 2h roots, 3..5 copy 2h+1
                (dsdv_gunit_l0.sv:6-14, :77-79 decode, :103 reserved check); = ot_s81sl_xr send config kind 7 with dst
                row {h, g, acc} and pairs 1 (ot_s81sl_xr.sv:139-151: [40 +: 10] = dst row, [50 +: 2] = pairs - 1 = 0).
  SC beat (kind 5)  [3:1] 5, [40 +: 10] score row r < 64 ([49:46] = 0), scores 7 r + j at [52 + 32 j +: 32]
                (dsdv_gunit_l1.sv:9-11 header, :53 kind, :69-72 store, :91 reserved check).
  CTL rows out  target 5 row writes {a 10 [26 +: 10], m 4 [36 +: 4], d 128 [40 +: 128]} of the payload at beat [21 +: 186],
                src = gunit sid (dsdv_gunit_l1.sv:150-163 ids row R, m 0011; weights R+1 m 1111, R+2 m 0011 from L3;
                dsdv_gunit_l5.sv:79-101 HC rows R..R+5, m 1111: pre 0..3, post 0..3, comb rows 0..3), injected both ways
                by the L2 stop (dsdv_gunit_l2.sv:50-54).
Static plan (no ready / credit anywhere): the HP / SC beats are a fixed arrival plan the slice send lowering must meet
(one N-tier beat on vi_n and one S-tier beat on vi_s per stop edge; S beats 2 edges later at the pin because the rung
crosses L1 / L3 (4 edges) below the stop and L5 / L4 / L0 (6) above it: dsdv_gunit.sv:14-16); HP windows of 32 beats
every HP_PERIOD = 20 edges (dsdv_gunit_l0.sv:11-13: completions >= 20 edges apart); the job reaches the gunit cw pin
>= JOB_LEAD edges before the first beat.  Output edges = last beat + the unit's fixed latency (constants below, measured
by tools/s81_dv/layer_prog/gu/run_gu_bench.sh on this RTL and asserted there).

Dependencies (not lowered here): the slice-side HP partial roots (frames fn . flat chunk sums + vn sum of squares,
subtree roots, ot_s81sl_xr send config CTL target 4 kind 7) and the SC send / relay of the allgathered scores
(ot_s81sl_xr send config bit 43 SC relay, vs op 10 RA scores) -> hc.fn / hc.sumsq are PARTIAL (only the gunit's top
tree + finish is this unit); the leaf-store row map of the coefficient / router rows (consumers vp POST / NORM imm,
frames) is the default GU_ROWS below, overridable through ctx['gu_rows'].
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np

OPS = [r'(attn|ffn)\.hc\.(sumsq|rsqrt|fn|pre_post|sinkhorn)$', r'^ffn\.(top6|top6_order|weights)$']

ENG_GUNIT = 2
SEQ_GUNIT_TO_CW = 3             # dsdv_seq_host.sv:41-42: gunit job command register -> cw pin + 3
CW_LINK = 'cw_seqhost'          # bind9 die.v: u_seqhost.cw_* -> st_cw_seqhost_* -> ld_cw_seqhost -> u_gunit.cw_*
LINK_VI_N, LINK_VI_S = 'tvS_s_3N', 'tvN_s_3S'
LINK_VO_N, LINK_VO_S = 'tvN_gunit', 'tvS_gunit'
FT_N, FT_S = 6, 4               # rung edges above / below the L2 stop (dsdv_gunit.sv:14-16)
HP_PERIOD = 20                  # window completion spacing (dsdv_gunit_l0.sv:12-13, fault at gap < 19)
JOB_LEAD = 8                    # job at the cw pin this many edges before the first beat (cw -> L0 / L1 job flop: 4)
NE, NEMAX, K = 384, 448, 6
# fixed latencies, measured on the RTL of record by run_gu_bench.sh (asserted there: any drift fails the bench)
#   from the edge the LAST beat is on vi_n (the matching S beat is on vi_s 2 edges later; both reach the stop together)
HC_LAT_BASE_N, HC_LAT_BASE_S = 1019, 1017  # -> first coefficient row on vo_n / vo_s (rows i = 1..5 follow one an edge; S81-RF1 11-03: +1, l0r RE-FORM RF 1)
# DIE-S81-51/RF-D 11-03: the HC latency follows the gunit FORM selected in the RTL of record (the default parameter / define
# of each leaf), so whichever conservative form signs off first carries its schedule with it (no second edit):
#   dsdv_gunit_l4 RF >= 2   every adder LAT 4 -> 5 (f12_l5x)   +9  (golden run_gunit_bench hc_lat 1008 -> 1017)
#   dsdv_gunit_l5 RFD >= 1  Sinkhorn fault LOOP cut            +1  (1008 -> 1009)
#   dsdv_gunit_tail_fs on ot_hdc_sinkhorn_fsr (row-pipelined Sinkhorn, gl5 rfd2; not with `OT_S81_GUNIT_SKFS)
#                                                              +120 (LAT 642 -> 762; gl5 rfd2 total +121, 1008 -> 1129)
# A new form adds its row here with the delta measured by rtl/dsrom_sys/s81_dv/unit/test/run_gunit_bench.sh;
# run_gu_bench.sh asserts the total (any drift fails).
HC_FORM_DELTAS = (('dsdv_gunit_l4.sv', r'parameter\s+integer\s+RF\s*=\s*(\d+)', 2, 9),
                  ('dsdv_gunit_l5.sv', r'`define\s+OT_S81_GUNIT_RFD\s+(\d+)', 1, 1),
                  ('dsdv_gunit_tail_fs.sv', r'^\s*ot_hdc_sinkhorn_fsr\b', None, 120))


def hc_form_delta(unit_dir=None):
    """Sum of the HC latency deltas of the gunit leaf forms the RTL at unit_dir selects by default."""
    d = Path(unit_dir) if unit_dir else Path(__file__).resolve().parents[3] / 'rtl/dsrom_sys/s81_dv/unit'
    tot = 0
    for fn, rx, at, delta in HC_FORM_DELTAS:
        f = d / fn
        m = re.search(rx, f.read_text(), re.M) if f.exists() else None
        if m and (at is None or int(m.group(1)) >= at):
            tot += delta
    return tot


HC_LAT_N, HC_LAT_S = HC_LAT_BASE_N + hc_form_delta(), HC_LAT_BASE_S + hc_form_delta()
# TOK-ALL-16 10-27: re-measured on current main (gunit parent with the bound native-32 L5 127356adf2 + 10-24 pin-register
# stations; identical with and without the GUNIT_* defines): HC 759/757 -> 1018/1016 (+259), router ids 68/66 -> 50/48
# (-18), RW_GAP 121 -> 101; every value bit-exact (results/token_pass/tok16_dsl0_1027/gu)
RT_LAT_BASE_N, RT_LAT_BASE_S = 62, 60  # -> ids row on vo_n / vo_s with the bf core in form gf2 (no bf define)
#                                  (S81-CORE-LAT-R17: +1, l1c order sort CPS 3 -> 2; S81-RF1 11-03: +12, l1c RE-FORM RF 1 =
#                                  one exchange per stage, 4 accumulators)
# DIE-S81-89 11-13: like HC_LAT, the router latency follows the FORM of record of the hard core dsdv_gunit_l1f_bf (its
# recipe defines, physical/die_plan/s81/cores/legacy/recipes.json): whichever bf view binds carries its schedule (no second
# edit).  Every bf output o_* (-> u_l1c -> u_l1 -> ids row on vo_n / vo_s) moves by the define's delta; the gather reply
# moves with it for the M1REG/C1REG forms. GF5 SVREG shifts only select: its paired A bias snapshot
# preserves the old read edge; gather feedback is separate and keeps the gf4 RW_GAP.
# No die lane (plan latency.lanes) changes (GUNIT-CORE-1 11-13 trace).
#   OT_GUNIT_BF_M1REG  gf3: u_m1 first exchange registered (c1r)                    +1  (DIE-S81-80 11-08)
#   OT_GUNIT_BF_C1REG  gf4: fold / candidate compares registered at the compare site +1  (GUNIT-CORE-1 11-13)
#   OT_GUNIT_BF_SVREG gf5: local SV/CTL cut + paired A bias snapshot; select +1, gather +0
# run_gu_bench.sh compiles the bench with the same define set (bf_defines()) and asserts the total.  An OT_GUNIT_BF_*
# define without a row here fails closed: a new bf form adds its row with the delta its bench measures.
RT_FORM_DELTAS = (('OT_GUNIT_BF_M1REG', 1), ('OT_GUNIT_BF_C1REG', 1), ('OT_GUNIT_BF_SVREG', 1))
# GF5 SV/paired-bias stage is on the select path, not the independent gather reply.
# Keep the feedback budget separate: gf2/3/4 remain byte-for-byte the same prices.
RW_FORM_DELTAS = (('OT_GUNIT_BF_M1REG', 1), ('OT_GUNIT_BF_C1REG', 1), ('OT_GUNIT_BF_SVREG', 0))
BF_RECIPE = 'physical/die_plan/s81/cores/legacy/recipes.json'
BF_CORE = 'dsdv_gunit_l1f_bf'
BF_DEFINES_ENV = 'OT_GUNIT_BF_DEFINES'   # bench / what-if override: comma or space separated, "" = gf2 (no define)


def bf_defines(recipes=None):
    """the define set of the bf form of record: $OT_GUNIT_BF_DEFINES if set, else recipes.json[dsdv_gunit_l1f_bf].defines"""
    import os
    ov = os.environ.get(BF_DEFINES_ENV)
    if ov is not None:
        return tuple(sorted(d for d in re.split(r'[\s,]+', ov) if d))
    f = Path(recipes) if recipes else Path(__file__).resolve().parents[3] / BF_RECIPE
    return tuple(sorted(json.loads(f.read_text())[BF_CORE].get('defines', [])))


def rt_form_delta(defines=None):
    """sum of the router latency deltas of the bf define set (default: the form of record); unknown bf define -> raise"""
    defs = bf_defines() if defines is None else tuple(defines)
    known = dict(RT_FORM_DELTAS)
    bad = [d for d in defs if d.startswith('OT_GUNIT_BF_') and d not in known]
    if bad:
        raise ValueError(f'{BF_CORE} define(s) {bad} have no RT_FORM_DELTAS row (measure the form with run_gu_bench.sh)')
    return sum(known.get(d, 0) for d in defs)


def rw_form_delta(defines=None):
    """Response-class-specific gather feedback delta; unknown BF forms fail closed."""
    defs = bf_defines() if defines is None else tuple(defines)
    rt_form_delta(defs)
    known = dict(RW_FORM_DELTAS)
    bad = [d for d in defs if d.startswith('OT_GUNIT_BF_') and d not in known]
    if bad:
        raise ValueError(f'{BF_CORE} define(s) {bad} have no RW_FORM_DELTAS row')
    return sum(known.get(d, 0) for d in defs)


RT_LAT_N, RT_LAT_S = RT_LAT_BASE_N + rt_form_delta(), RT_LAT_BASE_S + rt_form_delta()
RW_GAP_BASE = 101               # gf2 IDs -> first weights row (L3 ot_s81_su_rw, measured)
RW_GAP = RW_GAP_BASE + rw_form_delta()  # gf3 102, gf4 103; GF5 SV does not traverse this reply
import sys as _sys                                  # noqa: E402
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from leaf_rows import GU_ROWS                       # noqa: E402  (TOK-S81-GAPS/GU: the allocated leaf-store rows)
SMASK, LMASK = 0xFFFF, 0x1F                        # every slice / every leaf takes the rows


def _f32(x):
    return int(np.asarray(x, dtype=np.float32).view(np.uint32))


def cw_addr(set_, row):
    """table write address a10 = {0, set, 00, row 6}"""
    assert 0 <= row < 64
    return (set_ & 1) << 8 | row


def job_router(set_, ne, row, lmask, smask):
    """dsdv_gunit_l1.sv:96 {set [40], ne [39:31], row [30:21], lmask [20:16], smask [15:0]}"""
    return (set_ & 1) << 40 | (ne & 0x1FF) << 31 | (row & 0x3FF) << 21 | (lmask & 0x1F) << 16 | (smask & 0xFFFF)


def job_hc(which, set_, row, lmask, smask):
    """dsdv_gunit_l0.sv:101 {which [41], set [40], row [30:21], lmask [20:16], smask [15:0]}"""
    return (which & 1) << 41 | (set_ & 1) << 40 | (row & 0x3FF) << 21 | (lmask & 0x1F) << 16 | (smask & 0xFFFF)


def table_rows(set_, bias, hc_base, hc_scale, eps32, route_scale32):
    """the 63 boot rows of one table set (a10, d256); bias [<= 448] f32 bits, hc_base[w] [24], hc_scale[w] [3]"""
    rows = []
    b = list(bias) + [0] * (NEMAX - len(bias))
    for r in range(56):
        rows.append((cw_addr(set_, r), sum(b[8 * r + j] << (32 * j) for j in range(8))))
    for w in range(2):
        for i in range(3):
            rows.append((cw_addr(set_, 56 + 3 * w + i), sum(hc_base[w][8 * i + j] << (32 * j) for j in range(8))))
    d = (eps32 << 224) | (route_scale32 << 192)
    for w in range(2):
        for j in range(3):
            d |= hc_scale[w][j] << (96 * w + 32 * j)
    rows.append((cw_addr(set_, 62), d))
    return rows


def ctl_row_beat(row, m, d128, smask, lmask, src):
    """gunit CTL row beat (dsdv_gunit_l1.sv:150-158 / dsdv_gunit_l5.sv:79-85)"""
    p = (smask & 0xFFFF) | 5 << 16 | (lmask & 0x1F) << 21 | (row & 0x3FF) << 26 | (m & 0xF) << 36 | (d128 & ((1 << 128) - 1)) << 40
    return 1 | (src & 0xF) << 9 | p << 21


def hp_beat(acc, g, h, roots6, src):
    b = 1 | 7 << 1 | (src & 0xF) << 9 | (acc & 0x1F) << 40 | (g & 0xF) << 45 | (h & 1) << 49
    for j, w in enumerate(roots6):
        b |= (w & 0xFFFFFFFF) << (52 + 32 * j)
    return b


def sc_beat(r, scores7, src):
    b = 1 | 5 << 1 | (src & 0xF) << 9 | (r & 0x3FF) << 40
    for j, w in enumerate(scores7):
        b |= (w & 0xFFFFFFFF) << (52 + 32 * j)
    return b


def tiers(die):
    """N-tier / S-tier slice sids (die.v sid straps; G2 sid = 2 c + r kept a parameter of the die, not of this file)"""
    sl = die.slices()
    n = sorted(v['sid'] for k, v in sl.items() if k.endswith('N'))
    s = sorted(v['sid'] for k, v in sl.items() if k.endswith('S'))
    return n, s


def hp_plan(die, t0):
    """HP arrival plan of one HC job: 25 windows (sum of squares first, then fn rows 0..23), window a at t0 + 20 a:
    edge c = 0..15 of the window: vi_n = (N sid c // 2, h c % 2) at t0 + 20 a + c, vi_s = (S sid c // 2, h c % 2) 2 later"""
    n, s = tiers(die)
    assert len(n) == 8 and len(s) == 8
    out = []
    for a, acc in enumerate([24] + list(range(24))):
        for c in range(16):
            t = t0 + HP_PERIOD * a + c
            out.append(dict(cycle=t, port='vi_n', acc=acc, g=n[c // 2], h=c % 2))
            out.append(dict(cycle=t + FT_N - FT_S, port='vi_s', acc=acc, g=s[c // 2], h=c % 2))
    return out


def sc_plan(t0, ne=NE):
    nsc = -(-ne // 7)
    out = []
    for r in range(nsc):
        c = r // 2
        if r % 2 == 0:
            out.append(dict(cycle=t0 + c, port='vi_n', row=r))
        else:
            out.append(dict(cycle=t0 + c + FT_N - FT_S, port='vi_s', row=r))
    return out


def _op_end(sched, name):
    for o in sched['ops']:
        if o['op'] == name:
            return o
    return None


def _owner(sched, prefix_rx):
    """the first scheduled op matching prefix_rx owns the job rows (one job per HC prefix / router per layer)"""
    for o in sched['ops']:
        if re.search(prefix_rx, o['op']):
            return o['id']
    return None


def _table_owner(sched):
    for o in sched['ops']:
        if any(re.search(rx, o['op']) for rx in OPS):
            return o['id']
    return None


def _load_tables(fx, set_):
    rd = lambda p, dt='<f4': np.fromfile(fx / p, dtype=dt)  # noqa: E731
    cfg = json.loads((Path(__file__).resolve().parents[3] / 'compiler/models/deepseek-v4.1-flash/inference_config.json')
                     .read_text())
    bias = [int(x) for x in rd('weights/gate.bias.bin').view(np.uint32)]
    base = [[int(x) for x in rd(f'weights/hc_{w}_base.bin').view(np.uint32)] for w in ('attn', 'ffn')]
    scale = [[int(x) for x in rd(f'weights/hc_{w}_scale.bin').view(np.uint32)] for w in ('attn', 'ffn')]
    return table_rows(set_, bias, base, scale, _f32(cfg['norm_eps']), _f32(cfg['route_scale']))


W276 = (1 << 276) - 1
W267 = (1 << 267) - 1
_VALS = {}


def _vals(fx_dir):
    """fixture values of every gunit boundary word of the layer (cached per fixture dir); None when the dir lacks them"""
    key = str(fx_dir)
    if key not in _VALS:
        try:
            _sys.path.insert(0, str(Path(__file__).resolve().parent / 'gu'))
            import gu_values as V
            fx = V.Fx(fx_dir)
            _VALS[key] = dict(roots={w: V.hc_roots(fx, w) for w in ('attn', 'ffn')},
                              coef={w: V.hc_coef(fx, w) for w in ('attn', 'ffn')}, router=V.router_vals(fx), read=fx.read)
        except (FileNotFoundError, AssertionError) as x:
            _VALS[key] = dict(error=f'{type(x).__name__}: {x}')
    return _VALS[key]


def cw_word(kind, jw):
    """ports cw_v, cw_a[9:0], cw_d[255:0] LSB-first; a = {1 job, 8'b0, kind} = 0x200 | kind (dsdv_seq_host.sv:328-329)"""
    return 1 | (0x200 | kind) << 1 | jw << 11


def encode(res, fx_dir, sid, row, which=None):
    """TOK-S81-GAPS/GU: attach `words` / `ports` (the dv_cut_replay word convention) to every gunit boundary event of one
    job, from the fixture values: CW in at the gunit cw pins, HP / SC in at vi_n / vi_s (landed edge), CTL rows out on
    vo_n / vo_s (the gunit output register edge).  Returns an error string when the fixtures lack a value."""
    if fx_dir is None:
        return 'no fixtures'
    v = _vals(fx_dir)
    if 'error' in v:
        return v['error']
    sc, rv = v['router']
    for e in res['events']:
        k = e['kind']
        if k == 'CW':
            jw = int(e['payload'], 16)
            e.update(ports=['cw_v', 'cw_a', 'cw_d'], valid_bit=0,
                     words=[[e['cycle'], f'{cw_word(1 if which is not None else 0, jw):x}', f'{W267:x}']])
        elif k == 'HP':
            m = re.search(r'acc(\d+)\.g(\d+)\.h(\d+)$', e['tag'])
            acc, gs, h = map(int, m.groups())
            b = hp_beat(acc, gs, h, v['roots'][which](acc, gs, h), gs)
            e.update(ports=[e['port']], valid_bit=0, words=[[e['cycle'], f'{b:x}', f'{W276:x}']],
                     payload='slice partial roots (fixture slice model: golden chunk-8 tree)')
        elif k == 'SC':
            r = int(e['tag'].rsplit('sc', 1)[1])
            b = sc_beat(r, sc[7 * r:7 * r + 7], r % 16)
            e.update(ports=[e['port']], valid_bit=0, words=[[e['cycle'], f'{b:x}', f'{W276:x}']],
                     payload='allgathered sqrt(softplus) scores (fixture)')
        elif k == 'CTL' and e['dir'] == 'out':
            t = e['tag']
            if which is not None:
                i = int(t[-1])
                c = v['coef'][which]
                b = ctl_row_beat(row + i, 0xF, sum(c[4 * i + j] << (32 * j) for j in range(4)), SMASK, LMASK, sid)
            else:
                dr, mm, d = rv[t.rsplit('.', 1)[1]]
                b = ctl_row_beat(row + dr, mm, d, SMASK, LMASK, sid)
            e.update(ports=[e['port']], valid_bit=0, words=[[e['cycle'], f'{b:x}', f'{W276:x}']])
    return None


def lower(die, op, ctx):
    sched, layer = ctx['sched'], ctx['layer']
    name = op['op']
    rows_map = dict(GU_ROWS, **(ctx.get('gu_rows') or {}))
    lidx = int(re.sub(r'\D', '', layer) or 0) if layer.startswith('L') else 0
    set_ = lidx & 1                                  # two table sets: layer parity (the next layer boots beside)
    cw_age = die.links[CW_LINK]['age_edges']
    sid_gu = die.strap('u_gunit', 'sid')
    bench = 'results/rtl/s81_layer_tput_1018/compiler/bench_gu'
    res = dict(status='LOWERED', unit='dsdv_gunit', insts=['u_gunit', 'u_seqhost'], gap=None, rows=[], templates=[],
               gunit_rows=[], svc_jobs=[], files={}, events=[], bench=bench, deps=[])
    if op['id'] == _table_owner(sched):
        fx = ctx.get('fixtures')
        if fx is None:
            return dict(res, status='PARTIAL', gap=dict(module='lower_gu', port='0x14 table rows',
                                                        missing='no fixture / weight dir in ctx: bias, HC bases / scales'))
        res['gunit_rows'] = _load_tables(Path(fx), set_)
    m = re.search(r'(attn|ffn)\.hc\.(\w+)$', name)
    if m:
        pre = name[:m.start(2) - len('hc.')]          # e.g. 'attn.' / 'mtp.attn.'
        w = 0 if m.group(1) == 'attn' else 1
        fn = _op_end(sched, pre + 'hc.fn') or op
        t0 = int(math.ceil(fn['end']))               # the slices' partial roots exist after the fn matvec
        if op['id'] == _owner(sched, re.escape(pre) + r'hc\.'):
            issue = max(0, t0 - JOB_LEAD - SEQ_GUNIT_TO_CW - cw_age)
            row = rows_map[m.group(1)]
            res['templates'] = [(f'{pre}hc.job', job_hc(w, set_, row, LMASK, SMASK))]
            res['rows'] = [dict(eng=ENG_GUNIT, issue=issue, arg=1 << 7 | 0, what=f'gunit HC job which {w} set {set_} row {row}')]
            res['events'].append(dict(cycle=issue + SEQ_GUNIT_TO_CW + cw_age, inst='u_gunit', port='cw', dir='in',
                                      kind='CW', tag=f'{pre}hc.job', payload=f'{job_hc(w, set_, row, LMASK, SMASK):011x}'))
            plan = hp_plan(die, t0)
            res['events'] += [dict(cycle=p['cycle'], inst='u_gunit', port=p['port'], dir='in', kind='HP',
                                   tag=f"{pre}hc.acc{p['acc']}.g{p['g']}.h{p['h']}",
                                   payload='slice partial roots (fixture-derived; slice HP send = dependency)')
                              for p in plan]
            tl = max(p['cycle'] for p in plan if p['port'] == 'vi_n')
            for i in range(6):
                for port, lat in (('vo_n', HC_LAT_N), ('vo_s', HC_LAT_S)):
                    res['events'].append(dict(cycle=tl + lat + i, inst='u_gunit', port=port, dir='out', kind='CTL',
                                              tag=f'{pre}hc.coef_row{i}', payload=f'row {row + i} m f (coefficients)'))
            res['files'][f'prog/gu/{pre}hc.plan.json'] = json.dumps(dict(
                t_issue=issue, t_hp0=t0, t_last_hp=tl, which=w, set=set_, row=row, sid_gunit=sid_gu,
                cw_age=cw_age, beats=plan), indent=0) + '\n'
            err = encode(res, ctx.get('fixtures'), sid_gu, row, which=m.group(1))
            if err:
                res['encode_gap'] = err
        if m.group(2) in ('sumsq', 'fn'):
            res['status'] = 'PARTIAL'
            res['gap'] = dict(module='ot_s81sl_xr / frames cfg7 / ot_s81sl_vn',
                              port='send config (CTL target 4) kind 7 HP beats {acc, g, h, 6 subtree roots}',
                              missing='the slice-side chunk sums / maximal aligned subtree roots of fn . flat and of the '
                                      'sum of squares (frames + vn) and their kind-7 send are not lowered (frames: GAP_XS_ROM);'
                                      ' the gunit top tree above the slice roots is lowered and bit-exact (bench_gu)')
        res['deps'].append('slice HP send (kind 7) at the hp_plan edges')
        return res
    # router (top6 / top6_order / weights): one job per layer
    ag = _op_end(sched, 'ffn.router_allgather')
    t0 = int(math.ceil(ag['end'])) if ag else int(math.ceil(op['start']))
    if op['id'] == _owner(sched, r'^ffn\.(top6|top6_order|weights)$'):
        issue = max(0, t0 - JOB_LEAD - SEQ_GUNIT_TO_CW - cw_age)
        row = rows_map['router']
        jw = job_router(set_, NE, row, LMASK, SMASK)
        res['templates'] = [('ffn.router.job', jw)]
        res['rows'] = [dict(eng=ENG_GUNIT, issue=issue, arg=0 << 7 | 0, what=f'gunit router job set {set_} ne {NE} row {row}')]
        res['events'].append(dict(cycle=issue + SEQ_GUNIT_TO_CW + cw_age, inst='u_gunit', port='cw', dir='in', kind='CW',
                                  tag='ffn.router.job', payload=f'{jw:011x}'))
        plan = sc_plan(t0)
        res['events'] += [dict(cycle=p['cycle'], inst='u_gunit', port=p['port'], dir='in', kind='SC',
                               tag=f"ffn.router.sc{p['row']}", payload='scores 7 r .. 7 r + 6 (allgathered; dependency)')
                          for p in plan]
        tl = max(p['cycle'] for p in plan if p['port'] == 'vi_n')
        outs = [('ids', 0, 0)] + [(f'w{i}', i + 1, RW_GAP + i) for i in range(2)]
        for tag, dr, extra in outs:
            for port, lat in (('vo_n', RT_LAT_N), ('vo_s', RT_LAT_S)):
                res['events'].append(dict(cycle=tl + lat + extra, inst='u_gunit', port=port, dir='out', kind='CTL',
                                          tag=f'ffn.router.{tag}', payload=f'row {row + dr}'))
        res['files']['prog/gu/ffn.router.plan.json'] = json.dumps(dict(
            t_issue=issue, t_sc0=t0, t_last_sc=tl, set=set_, row=row, ne=NE, sid_gunit=sid_gu, cw_age=cw_age,
            rw_gap=RW_GAP, rt_lat=[RT_LAT_N, RT_LAT_S], bf_defines=list(bf_defines()), beats=plan), indent=0) + '\n'
        err = encode(res, ctx.get('fixtures'), sid_gu, row)
        if err:
            res['encode_gap'] = err
    if name == 'ffn.top6':
        res['note'] = 'the gunit emits the 6 ids in id order (top6_order); the rank order is not materialised (consumers use id order)'
    res['deps'].append('allgathered sqrt(softplus) scores as SC beats (vs RA + xr SC relay) at the sc_plan edges')
    return res


if __name__ == '__main__':      # run_gu_bench.sh: the bf define set + router latency this lowering schedules
    print(json.dumps(dict(bf_defines=list(bf_defines()), rt_lat=[RT_LAT_N, RT_LAT_S], rt_lat_base=[RT_LAT_BASE_N, RT_LAT_BASE_S],
                          hc_lat=[HC_LAT_N, HC_LAT_S], rw_gap=RW_GAP)))
