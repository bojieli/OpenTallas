#!/usr/bin/env python3
"""S81-LP-2 (2026-10-29): compact hard-child kit inputs for the LP coll lane dsfd_coll_lane_w_safe8_ntf (CORE_CRED 12),
COORD ruling 06:01 (lane cut adopted for s_0S_LP). Zero RTL / cycle / plan-pin change: same RTL + params as the closed
ref_tile dscoll_lane_w_s12h (sources, defines OT_COLL_NATIVE32{,_OFF}, 55 SRAM macros), only outline, macro sites and the
child pin table change.  Outline derived from the parent slot (s_0S_LP 1442.88 x 1226.88; 4 lanes side by side along
the S face, where the parent's coll_i0..3 / coll_o0..3 windows sit).  Two aspect variants (12.17(3)):
  A 'row4'  345.6 x 561.6 : 4 x 345.6 = 1382.4 (60.5 um left for edge/gaps), 6 big macros per row
  B 'chan'  302.4 x 630.72: 4 x 302.4 = 1209.6 (233 um left: ~58-um parent channels between lanes), 5 per row
Faces (link face S, core face N; the old tile used W/E): S rx[514:0] left (= parent coll_i0 window 6..117) + tx[511:0]
right; N lo_* (left) / li_* (right) toward the parent lnland with ck (M5 0.048x0.48, plan core clock 250 TT) at the N\ncentre; E mid-height rs/chb/flt.
Macro rows S->N follow the old W->E data order: u_gb (10 small) -> u_ep rb (18 big) -> u_ski (9 small) -> u_ep fifo
(18 big); every SRAM keeps its pins (M4, W edge) facing a >=21.6-um column gap.
    python3 lane_kit.py OUTDIR   # writes OUTDIR/{A,B}/{spec.json,plan_pins.json,lane.lef,kit_plan.json} + recipes.json
"""
import json, sys, copy, re, hashlib, os
from pathlib import Path
R = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]).resolve()
MOD = 'dsfd_coll_lane_w_safe8_ntf'
base = json.load(open(R / 'physical/ref_tile/dscoll_lane_w_s12h/spec.json'))
SM, BG = 'ot_sram_1r1w2c_32x64_m1', 'ot_sram_1r1w2c_256x64_m1'
SZ = {SM: (31.992, 17.304), BG: (34.584, 41.352)}
GROUPS = [('*u_gb.u_sf.g_bank?{i}?.u_m', SM, 10, 'MX'),
          ('*u_ep.g_rb_safe.u_m.g_bank?{i}?.g_depth?0?.g_256.u_m', BG, 18, 'MX'),
          ('*u_ski.u_head.g_bank?{i}?.u_m', SM, 9, 'R0'),
          ('*u_ep.g_fifo_safe.u_m.g_bank?{i}?.g_depth?0?.g_256.u_m', BG, 18, 'MX')]
# small macros share the big-macro column lattice (preflight macro_channels: >= 10.8-um vertical channel per column)
VAR = {'A': dict(w=345.6, h=561.6, per_big=6, per_small=6, big_pitch=(55.296, 56.16), small_pitch=(55.296, 25.92)),
       'B': dict(w=302.4, h=630.72, per_big=5, per_small=5, big_pitch=(56.16, 51.84), small_pitch=(56.16, 25.92))}
# old instance names: keep exactly the patterns the closed spec used (depth index included)
old_inst = {}
for m in base['macros']:
    k = re.sub(r'\?\d+\?', '?', m['inst'], count=1)
    old_inst.setdefault(re.sub(r'\?\d+\?', '?', m['inst']), []).append(m['inst'])
DIRS = dict(ck='INPUT', rs='INPUT', chb='INPUT', rx='INPUT', lo_v='INPUT', lo_d='INPUT', li_r='INPUT',
            tx='OUTPUT', lo_r='OUTPUT', li_v='OUTPUT', li_d='OUTPUT', flt='OUTPUT')
RECT = {'M4': (0.042, 0.012), 'M5': (0.012, 0.042)}


# Kit-local synthesis-attribute patch (zero logic change): the (* keep *) on the two 1-bit link output regs makes Yosys
# leave an unloaded BUFx2 to the kept internal alias (u.u_ski.l_credit / u.u_sko.l_valid) on the port net, which the RAW
# face_guard counts as a 'shared' output (lp2a/lp2b 06:2x: lo_r[0], li_v[0]).  The regs still drive the ports directly.
PATCHES = [dict(file='rtl/common/ot_link_credit_rx_b64.sv', why='S81-LP-2: drop (* keep *) on the 1-bit link output reg; Yosys otherwise leaves an unloaded BUFx2 to the kept alias on the port net (RAW face_guard shared FAIL). Zero logic change; the reg drives the port.', edits=[['(* keep *) output reg l_credit,', 'output reg l_credit,']]),
           dict(file='rtl/common/ot_link_credit_tx_rc.sv', why='S81-LP-2: drop (* keep *) on the 1-bit link output reg; Yosys otherwise leaves an unloaded BUFx2 to the kept alias on the port net (RAW face_guard shared FAIL). Zero logic change; the reg drives the port.', edits=[['(* keep *) output reg l_valid,', 'output reg l_valid,']])]


def tr5(x):   # M5 track (vertical) x = 0.012 + k*0.048
    return round(round((x - 0.012) / 0.048) * 0.048 + 0.012, 4)


def tr4(y):
    return round(round((y - 0.012) / 0.048) * 0.048 + 0.012, 4)


def build(v, p):
    w, h = p['w'], p['h']
    d = OUT / v
    d.mkdir(parents=True, exist_ok=True)
    # ---- macros (rows S->N)
    macros, y, rows = [], 21.6, []
    byname = {}
    for m in base['macros']:
        byname.setdefault(m['view'].split('/')[-1], []).append(m)
    for pat, view, n, orient in GROUPS:
        mw, mh = SZ[view]
        per = p['per_big'] if view == BG else p['per_small']
        px, py = p['big_pitch'] if view == BG else p['small_pitch']
        span = (per - 1) * px + SZ[BG][0]   # column lattice = big-macro width
        x0 = round(round((w - span) / 2 / 0.216) * 0.216, 3)
        assert x0 - 4.32 >= 12.0 and w - 4.32 - (x0 + span) >= 12.0 and px - SZ[BG][0] >= 12.0, (v, x0, span)
        # the group's instance patterns, in the closed spec's order
        insts = [m['inst'] for m in base['macros'] if re.sub(r'\?\d+\?', '?', m['inst'], count=1).split('?')[0] ==
                 pat.split('?')[0] and m['view'].endswith(view)]
        assert len(insts) == n, (pat, len(insts))
        for i, inst in enumerate(insts):
            r, c = divmod(i, per)
            macros.append(dict(view=f'physical/asap7_memory_macros_v2/{view}', count=1, inst=inst,
                               at=[round(x0 + c * px, 3), round(y + r * py, 3)], orient=orient))
        nrow = (n + per - 1) // per
        rows.append((pat.split('.')[0] + '.' + pat.split('.')[1], y, y + (nrow - 1) * py + mh))
        y = y + (nrow - 1) * py + mh + 12.96
    top_macro = max(m['at'][1] + SZ[m['view'].split('/')[-1]][1] for m in macros)
    assert top_macro <= h - 40.0, (v, top_macro, h)
    for m in macros:
        mw, mh = SZ[m['view'].split('/')[-1]]
        assert m['at'][0] >= 4.32 + 5.4 and m['at'][0] + mw <= w - 4.32 and m['at'][1] >= 4.32, (v, m)
    # ---- pins
    pins = []

    def pin(n, L, x, y_):
        pins.append(dict(name=n, layer=L, x=x, y=y_))
    st = 0.24
    xs = tr5(6.156)
    for i in range(515):
        pin(f'rx[{i}]', 'M5', round(xs + i * st, 4), 0.042)
    xt = tr5(w - 4.32 - 1.2 - 511 * st)
    assert xt > xs + 514 * st + 5, (v, 'S face overlap')
    for i in range(512):
        pin(f'tx[{i}]', 'M5', round(xt + i * st, 4), 0.042)
    yn = round(h - 0.042, 4)
    xl = tr5(6.156)
    for i in range(553):
        pin(f'lo_d[{i}]', 'M5', round(xl + i * st, 4), yn)
    # [0:0] ports are named x[0] (plan-table convention, = the Yosys netlist port bits face_guard compares)
    pin('lo_v[0]', 'M5', round(xl + 553 * st, 4), yn)
    pin('lo_r[0]', 'M5', round(xl + 554 * st, 4), yn)
    xr = tr5(w - 4.32 - 1.2 - 554 * st)
    assert xr > xl + 554 * st + 3, (v, 'N face overlap', xr, xl + 554 * st)
    pin('li_v[0]', 'M5', xr, yn)
    pin('li_r[0]', 'M5', round(xr + st, 4), yn)
    for i in range(553):
        pin(f'li_d[{i}]', 'M5', round(xr + (i + 2) * st, 4), yn)
    # clock: M5 pin (>= 0.048 x 0.48, GEOM-21) at the N-face centre, in the gap between the lo and li blocks
    xc = tr5(w / 2)
    assert xl + 554 * st + 2 < xc < xr - 2, (v, 'clock gap')
    pin('ck[0]', 'M5', xc, round(h - 0.24, 4))
    ye = tr4(h / 2)
    xe = round(w - 0.042, 4)
    for k, n in enumerate(['flt[0]', 'flt[1]', 'flt[2]', 'chb[0]', 'rs[0]']):
        pin(n, 'M4', xe, round(ye + (k - 4) * 0.48, 4))
    assert len(pins) == 2143 and len({p_['name'] for p_ in pins}) == 2143
    assert len({(q['layer'], q['x'], q['y']) for q in pins}) == 2143
    (d / 'plan_pins.json').write_text(json.dumps(dict(module=MOD, outline_um=[w, h], pins=pins), indent=0) + '\n')
    # ---- LEF (pin contract shapes/directions)
    ls = ['VERSION 5.8 ;', 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', f'MACRO {MOD}', ' CLASS BLOCK ;', ' ORIGIN 0 0 ;',
          f' SIZE {w} BY {h} ;', ' SYMMETRY X Y ;']
    for q in pins:
        n, L, x, y_ = q['name'], q['layer'], q['x'], q['y']
        dx, dy = (0.024, 0.24) if n == 'ck[0]' else RECT[L]
        ls += [f' PIN {n}', f'  DIRECTION {DIRS[n.split("[")[0]]} ;', '  USE CLOCK ;' if n == 'ck[0]' else '  USE SIGNAL ;',
               '  PORT', f'   LAYER {L} ;', f'   RECT {x-dx:.4f} {y_-dy:.4f} {x+dx:.4f} {y_+dy:.4f} ;', '  END', f' END {n}']
    ls += [f'END {MOD}', 'END LIBRARY']
    (d / 'lane.lef').write_text('\n'.join(ls) + '\n')
    # ---- spec (closed ref_tile spec, new outline + macro sites + faces)
    s = copy.deepcopy(base)
    s['name'] = f'dscoll_lane_w_lp2{v.lower()}'
    s['outline'] = dict(w=w, h=h)
    s['macros'] = macros
    s['pins'] = dict(S=['rx', 'tx'], N=['lo_v', 'lo_r', 'lo_d', 'li_v', 'li_r', 'li_d'], E=['flt', 'chb', 'rs'])  # ck: N-face centre M5
    s['structural_change'] = (f'S81-LP-2 compact LP hard child variant {v} ({w} x {h}) of dscoll_lane_w_s12h: same RTL/params/'
                              'defines/macros, outline from the s_0S_LP slot (4 across 1442.88), faces S link / N core / E '
                              'clock; zero RTL or cycle change.')
    s.pop('slot_change_request', None)
    (d / 'spec.json').write_text(json.dumps(s, indent=1) + '\n')
    # ---- pseudo plan (die/clock from the main S81 plan, one source type holding the hard core)
    mp = json.load(open(R / 'physical/die_plan/s81/die_plan.json'))
    typ = f'source_coll_lane_w_lp2{v.lower()}'
    rel = d.relative_to(R)
    plan = dict(schema=mp.get('schema'), die=mp['die'], clock=mp['clock'], partition_types={typ: dict(
        module=MOD, outline_um=[w, h], contents=[dict(inst='u_ln', module=MOD, status='rework')],
        hard_cores=[dict(inst='u_ln', module=MOD, origin_um=[0, 0], outline_um=[w, h], orient='R0',
                         track_offset_um=[0.108, 0.012], pins_file=os.path.relpath(d / 'plan_pins.json', R / 'physical/die_plan/s81'), lef=str(rel / 'lane.lef'),
                         obs_max='M5')])}, partitions=[])
    (d / 'kit_plan.json').write_text(json.dumps(plan, indent=1) + '\n')
    area = w * h
    mac = sum(SZ[m['view'].split('/')[-1]][0] * SZ[m['view'].split('/')[-1]][1] for m in macros)
    return dict(variant=v, outline_um=[w, h], area_um2=round(area, 1), macro_area_um2=round(mac, 1),
                std_area_um2_est=11927.2, fill_incl_macros=round((mac + 11927.2) / area, 3),
                four_across_um=round(4 * w, 2), parent_width_left_um=round(1442.88 - 4 * w, 2),
                rows=rows, top_macro_um=round(top_macro, 2), n_band_um=round(h - top_macro, 2),
                clock_pin_um=[xc, h], clock_reach_max_um=round(w / 2 + h, 1), plan_type=typ,
                pins=len(pins), face_pins=dict(S=1027, N=1111, E=5), pin_pitch_um=st)


rep = [build(v, p) for v, p in VAR.items()]
recs = {}
for r in rep:
    v = r['variant']
    rel = (OUT / v).relative_to(R)
    recs[f'{MOD}__{v}'] = dict(ref_tile=str(rel), plan=str(rel / 'kit_plan.json'), plan_module=MOD,
                               io_hold='sender_min', suffix=f'lp2{v.lower()}', rtl_patches=PATCHES)
(OUT / 'recipes.json').write_text(json.dumps(recs, indent=1) + '\n')
(OUT / 'lane_estimate.json').write_text(json.dumps(rep, indent=1) + '\n')
print(json.dumps(rep, indent=1))
