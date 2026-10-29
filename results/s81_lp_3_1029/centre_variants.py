#!/usr/bin/env python3
"""S81-LP-3 (2026-10-29, COORD ruling (c) on S81-LP-2 ASK): centre clock-entry PARALLEL variants (12.17(3)) of the
compact LP lane kits A / B.  Same outline, macros, RTL, plan pins and LEF as results/s81_lp_2_1029/lane/{A,B}; only a
single-root master-plan CORE slice is added (precedent physical/die_plan/s81/delta_hcpl_clkentry_1027.py, S81-CORES-R27):
one 4.32-um island carrying the M5 clock entry in the macro column channel nearest the lane centre, empty pushdown
(in-core tree = the kit's standard CTS from the entry; no new script).  The plan pin table / LEF keep ck[0] on the N face
(HCPL precedent); gen_core_kit_legacy --master-slice rewrites the kit io.tcl ck[0] to the entry.
    python3 centre_variants.py   # writes results/s81_lp_3_1029/lane/{AC,BC}/... + recipes.json
"""
import json, math, shutil, sys, os
from pathlib import Path
R = Path(__file__).resolve().parents[2]
SRC = R / 'results/s81_lp_2_1029/lane'
OUT = R / 'results/s81_lp_3_1029/lane'
MOD = 'dsfd_coll_lane_w_safe8_ntf'
BG_W = 34.584
ISL = 4.32
M5_OFF, M5_PITCH = 0.012, 0.048
sys.path.insert(0, str(R / 'tools/die_plan'))
import master_slice as MS

recs = {}
rep = []
for v in ('A', 'B'):
    s = json.load(open(SRC / v / 'spec.json'))
    w, h = s['outline']['w'], s['outline']['h']
    cx, cy = w / 2, h / 2
    # big-macro column lattice (x of every macro column, from the spec)
    cols = sorted({m['at'][0] for m in s['macros']})
    chans = [(a + BG_W, b) for a, b in zip(cols, cols[1:])]
    inside = [c for c in chans if c[0] + ISL / 2 + 4.32 <= cx <= c[1] - ISL / 2 - 4.32]
    if inside:
        ex = cx
        ch = inside[0]
    else:
        ch = min(chans, key=lambda c: abs((c[0] + c[1]) / 2 - cx))
        ex = (ch[0] + ch[1]) / 2
    x = round(M5_OFF + math.floor((ex - M5_OFF) / M5_PITCH + 0.5) * M5_PITCH, 4)
    y = round(cy, 4)
    # no macro (with its 4.32 halo) may overlap the island
    SZ = {'ot_sram_1r1w2c_32x64_m1': (31.992, 17.304), 'ot_sram_1r1w2c_256x64_m1': (34.584, 41.352)}
    isl = [round(x - ISL / 2, 4), round(y - ISL / 2, 4), round(x + ISL / 2, 4), round(y + ISL / 2, 4)]
    for m in s['macros']:
        mw, mh = SZ[m['view'].split('/')[-1]]
        x0, y0 = m['at'][0] - 4.32, m['at'][1] - 4.32
        x1, y1 = m['at'][0] + mw + 4.32, m['at'][1] + mh + 4.32
        assert x1 <= isl[0] or x0 >= isl[2] or y1 <= isl[1] or y0 >= isl[3], (v, m['inst'], isl)
    d = OUT / (v + 'C')
    (d / 'slices').mkdir(parents=True, exist_ok=True)
    for f in ('spec.json', 'plan_pins.json', 'lane.lef'):
        shutil.copyfile(SRC / v / f, d / f)
    sp = json.load(open(d / 'spec.json'))
    sp['name'] = f'dscoll_lane_w_lp3{v.lower()}c'
    sp['structural_change'] += f' S81-LP-3: centre clock entry (master slice island at ({x}, {y})).'
    (d / 'spec.json').write_text(json.dumps(sp, indent=1) + '\n')
    plan = json.load(open(SRC / v / 'kit_plan.json'))
    (typ, pt), = plan['partition_types'].items()
    typ2 = typ.replace('lp2', 'lp3') + 'c'
    hc = pt['hard_cores'][0]
    hc['pins_file'] = os.path.relpath(d / 'plan_pins.json', R / 'physical/die_plan/s81')
    hc['lef'] = str((d / 'lane.lef').relative_to(R))
    plan['partition_types'] = {typ2: pt}
    (d / 'kit_plan.json').write_text(json.dumps(plan, indent=1) + '\n')
    sl = {"schema": MS.SCHEMA, "kind": "core", "die": "s81", "type": MOD, "module": MOD, "instances": [],
          "master_plan_sha256": "TRIAL-no-frozen-master-plan", "frozen": False, "outline_um": [w, h],
          "latency": {"common_clock_latency_ps": {"TT": 250, "FF": 202.5}, "tol_ps": 20, "early_taps": False},
          "keepouts": [], "bays": [], "entry_pins": [], "hard_cores": [], "corridors": [], "gates": {},
          "core_clock_port": "ck[0]",
          "islands": [{"name": "ck_entry", "rect_um": isl, "centre_um": [x, y], "use": "clock_driver",
                       "via_stack": ["M7", "M5"], "clock_pin": {"layer": "M5", "xy_um": [x, y]},
                       "note": "S81-LP-3 centre clock entry (COORD ruling (c) 10-29: parallel variant, standard CTS)"}],
          "pushdown": {"islands": [], "clock_repeaters": [],
                       "note": "in-core clock tree built by CTS from the centre entry; no feedthrough ports"},
          "event": "S81-LP-3 results/s81_lp_3_1029/centre_variants.py"}
    errs = MS.validate(sl)
    assert not errs, errs
    (d / 'slices' / f'{MOD}.json').write_text(json.dumps(sl, indent=1) + '\n')
    recs[f'{MOD}__{v}C'] = dict(ref_tile=str(d.relative_to(R)), plan=str((d / 'kit_plan.json').relative_to(R)),
                                plan_module=MOD, io_hold='sender_min', suffix=f'lp3{v.lower()}c',
                                rtl_patches=json.load(open(SRC / 'recipes.json'))[f'{MOD}__{v}']['rtl_patches'])
    far = max(abs(x - px) + abs(y - py) for px in (0, w) for py in (0, h))
    nc = max(abs(w / 2 - px) + abs(h - py) for px in (0, w) for py in (0, h))
    rep.append(dict(variant=v + 'C', outline_um=[w, h], entry_um=[x, y], channel_um=[round(ch[0], 3), round(ch[1], 3)],
                    island=isl, reach_max_um=round(far, 1), n_centre_reach_max_um=round(nc, 1)))
(OUT / 'recipes.json').write_text(json.dumps(recs, indent=1) + '\n')
(OUT / 'centre_estimate.json').write_text(json.dumps(rep, indent=1) + '\n')
print(json.dumps(rep, indent=1))
