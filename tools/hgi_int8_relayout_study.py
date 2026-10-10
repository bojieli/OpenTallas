#!/usr/bin/env python3
"""hbm-forks (2026-10-09, RQ-HF-7, OWNER rule ~11:05 PT): does the one-beat INT8 SM re-layout fit?

Owner rule: adopt the row-pair one-beat INT8 issue ONLY if the SM re-layout fits at <= 60 % utilisation, <= 858 mm2 and
<= 26 mm die height (the die's long axis stays <= 33 mm, the reticle); otherwise keep the two-beat INT8 front.

Inputs (all measured; nothing assumed except where marked):
  * the m3f SM tile (ot_hbm_accel_smh_tile_w) CTS instance area 108,103 um2 (results/uarch/hbm_smh_tile_headroom_20261007/
    measurement.json; OpenROAD 'Design area' counts the 8 x-store macros);
  * the same tile mapped by yosys 0.68 + ASAP7 RVT TT (physical/hbm_forks/int8_issue_area.sh, x-store SRAM as a black
    box) = 63,459.79 um2 -> the CALIBRATION yosys-mapped -> CTS growth g = (108,103 - 8 macros) / 63,459.79;
  * the BF16 MAC column ot_hbm_accel_smh_tc_col L = 16 mapped the same way = 15,974.40 um2 (one per leaf, RPT = 2
    leaves a tile); one-beat adds a SECOND column per leaf (row r + 1): +2 columns a tile, plus 32 INT8 -> BF16
    leaf converters a leaf (bounded above by the whole 64-lane front adapter, 1,174.27 um2 mapped, a tile).
Geometry: the SM element of tools/hbm_accel_smh_physical.floorplan (8 tile columns x 2 tile rows + the front; the fmt3
front is 138.24 um wider: R25G sm_wh 3,214.08 x 1,131.84) placed by tools/hbm_accel_die_fp.build(R25G) on its 3 x 3
site grid a stack (or the other legal grid, 4 x 2).  Die W grows by 6 x the element-width growth and H by 6 x the
element-height growth (two stack groups across, two up), checked by the generator itself for every fitting candidate.
  python3 tools/hgi_int8_relayout_study.py --out results/rtl/hbm_forks_20261009/int8_relayout_study.json
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import hbm_accel_die_fp as die
import hbm_accel_smh_physical as sm

ROOT = Path(__file__).resolve().parents[1]
MEAS = 'results/uarch/hbm_smh_tile_headroom_20261007/measurement.json'
MACRO_LEF = 'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.lef'
YOSYS_TILE_UM2 = 63459.785340      # int8_area2/tile.stat 'Chip area for top module' (x-store black box)
TC16_UM2 = 15974.402040            # int8_area/tc16.stat
LINE_UM2 = 1174.273200             # int8_area/line.stat (64 converters + 1,600 register bits: an upper bound)
N_MACROS = 8                       # 2 leaves x NXL 4 x-store macros (ot_hbm_accel_smh_leaf)
UTIL_MAX, AREA_MAX, H_MAX, W_MAX = 0.60, 858.0, 26000.0, 33000.0
FMT3_EXTRA_W = 3214.08 - 3075.84   # R25G FMT3_WIDE element vs the m3f floorplan element


def macro_um2():
    for ln in (ROOT / MACRO_LEF).read_text().splitlines():
        if ln.strip().startswith('SIZE'):
            t = ln.split()
            return float(t[1]) * float(t[3])
    raise RuntimeError('no SIZE')


def element(tw, th):
    g = dict(sm.GEOM, tile_w=tw, tile_h=th)
    w, h = sm.floorplan(g)[1]
    return round(w + FMT3_EXTRA_W, 3), h


def die_wh(base_geo, grid, ew, eh, base_e):
    cols, rows = grid
    dw = 2 * cols * (ew - base_e[0]) + (2 * (cols - 3) * 0)        # the 3 x 3 base; cols change handled below
    dh = 2 * rows * (eh - base_e[1])
    W, H = base_geo['W'], base_geo['H']
    if grid == (4, 2):     # one more column of sites (+ its channel) a group, one fewer row
        W += 2 * (base_e[0] + die.SHAVE + die.CH)
        H -= 2 * (base_e[1] + die.SHAVE + die.CH)
    return W + dw, H + dh


def core_util(inst, tw, th):
    return inst / ((tw - 2.16) * (th - 2.16))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    meas = json.loads((ROOT / MEAS).read_text())
    cts = float(meas['area_um2'])
    mac = macro_um2()
    g = (cts - N_MACROS * mac) / YOSYS_TILE_UM2
    base_e = element(sm.GEOM['tile_w'], sm.GEOM['tile_h'])
    base = die.build(die.R25G, geometry_only=True)['geo']
    base_area = base['W'] * base['H'] / 1e6
    rows = []
    out = dict(schema='opentallas.hbm_forks.int8_relayout_study.v1',
               owner_rule='adopt one-beat INT8 only if the SM re-layout fits: <= 60 % util, <= 858 mm2, <= 26 mm height',
               calibration=dict(tile_cts_instance_um2=cts, cts_receipt=MEAS, x_store_macros=N_MACROS,
                                macro_um2=round(mac, 3), tile_std_cell_cts_um2=round(cts - N_MACROS * mac, 1),
                                tile_yosys_mapped_um2=YOSYS_TILE_UM2,
                                yosys_to_cts_growth=round(g, 4),
                                note='growth = CTS std-cell area (instance area minus the x-store macros) / yosys mapped '
                                     'area of the same tile; it carries placement resizing, CTS and hold buffers'),
               base=dict(R25G_W_um=base['W'], R25G_H_um=base['H'], R25G_mm2=round(base_area, 2),
                         element_um=base_e, tile_um=[sm.GEOM['tile_w'], sm.GEOM['tile_h']],
                         tile_core_util=round(core_util(cts, sm.GEOM['tile_w'], sm.GEOM['tile_h']), 4)))
    for conv_label, conv in (('converters_0', 0.0), ('converters_upper_bound', LINE_UM2)):
        add_mapped = 2 * TC16_UM2 + conv
        inst = cts + g * add_mapped
        need_core = inst / UTIL_MAX
        best = None
        cands = []
        # sweep tile widths / heights on the 8.64 um grid: every shape at <= 60 % core utilisation, smallest die first
        for i in range(0, 80):
            tw = round(sm.GEOM['tile_w'] + i * sm.GRID, 3)
            th_min = need_core / (tw - 2.16) + 2.16
            th = round(max(sm.GEOM['tile_h'], math.ceil(th_min / sm.GRID - 1e-9) * sm.GRID), 3)
            ew, eh = element(tw, th)
            for grid in ((3, 3), (4, 2)):
                W, H = die_wh(base, grid, ew, eh, base_e)
                area = W * H / 1e6
                c = dict(grid=grid, tile_um=[tw, th], core_util=round(core_util(inst, tw, th), 4),
                         element_um=[ew, eh], die_W_um=round(W, 3), die_H_um=round(H, 3), die_mm2=round(area, 2),
                         fits=bool(W <= W_MAX and H <= H_MAX and area <= AREA_MAX),
                         over=dict(W_um=round(max(0, W - W_MAX), 1), H_um=round(max(0, H - H_MAX), 1),
                                   mm2=round(max(0, area - AREA_MAX), 2)))
                cands.append(c)
                key = (max(0, W - W_MAX) + max(0, H - H_MAX), area)
                if best is None or key < best[0]:
                    best = (key, c)
        fit = [c for c in cands if c['fits']]
        verified = None
        if fit:
            c = min(fit, key=lambda c: c['die_mm2'])
            v = dict(die.R25G, sm_wh=tuple(c['element_um']), sm_physical_grid=tuple(c['grid']))
            m = die.build(v, geometry_only=True)
            verified = dict(W=m['geo']['W'], H=m['geo']['H'])
        # the largest tile that fits the reticle on the R25G 3 x 3 grid (both axes at their limits)
        dw_max = (W_MAX - base['W']) / 6.0
        dh_max = (H_MAX - base['H']) / 6.0
        tw_max = sm.GEOM['tile_w'] + math.floor(dw_max / 8 / sm.GRID) * sm.GRID
        th_max = sm.GEOM['tile_h'] + math.floor(dh_max / 2 / sm.GRID) * sm.GRID
        cap_inst = UTIL_MAX * (tw_max - 2.16) * (th_max - 2.16)
        rows.append(dict(case=conv_label, added_mapped_um2_per_tile=round(add_mapped, 1),
                         projected_tile_cts_instance_um2=round(inst, 1),
                         projected_util_in_todays_slot=round(core_util(inst, sm.GEOM['tile_w'], sm.GEOM['tile_h']), 4),
                         core_area_needed_at_60pct_um2=round(need_core, 1),
                         added_tile_area_die_mm2_at_60pct=round(512 * (need_core - (sm.GEOM['tile_w'] - 2.16) *
                                                                       (sm.GEOM['tile_h'] - 2.16)) / 1e6, 2),
                         largest_tile_in_reticle_3x3=dict(tile_um=[round(tw_max, 3), round(th_max, 3)],
                                                          max_instance_um2_at_60pct=round(cap_inst, 1),
                                                          shortfall_pct=round(100 * (inst / cap_inst - 1), 1)),
                         n_candidates=len(cands), n_fit=len(fit), closest=best[1], generator_check=verified))
    out['cases'] = rows
    out['verdict'] = 'FIT' if any(r['n_fit'] for r in rows[:1]) else 'NO_FIT'
    out['decision'] = ('adopt one-beat INT8 (owner rule met)' if out['verdict'] == 'FIT' else
                       'keep the two-beat INT8 front (owner rule: the re-layout does not fit); the dense 1,024-bit fmt3 '
                       'line + per-row scales on the DMA stream stay adopted')
    out['source_sha256'] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in
                            ['tools/hbm_accel_die_fp.py', 'tools/hbm_accel_smh_physical.py',
                             'tools/hgi_int8_relayout_study.py', MEAS, 'physical/hbm_forks/int8_issue_area.sh']}
    p = ROOT / a.out
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: out[k] for k in ('calibration', 'base', 'verdict')}, indent=1))
    for r in rows:
        print(r['case'], r['projected_tile_cts_instance_um2'], r['largest_tile_in_reticle_3x3'], r['n_fit'], r['closest'])


if __name__ == '__main__':
    main()
