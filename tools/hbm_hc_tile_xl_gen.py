#!/usr/bin/env python3
"""conservative-1011 [B hfd_hc] 2026-10-11: hfd_hc_tile_xl = one closed ot_dsrom_su_hcpost_lane_pr lane + its
broadcast / capture / accumulate registers in a strip beside it, with physical falling-edge output lockups for the
clock-root hop to the next tile (the hfd_su_tile_xl structure that closed TT +17.28 / FF +13.26, hfd_su superseded).

Why (structural, not a patch): every R25GQ quarter route of hfd_hc failed at CTS (-589 / -1,633 ps): one quarter-wide
clock tree with 22 group ICGs and 5,000-sink roots over 2,033 x 1,499 um.  Tiled, each lane and its boundary registers
close as a 117 x 117 um hard macro with registered pins, its own clock insertion and half-cycle lockups between
adjacent tiles' roots; the quarter becomes tile-to-tile chains (no wide logic, no block-wide clock tree).

Same lane arithmetic and same receiving-edge values as the positive-edge tile; outputs visible half a cycle later;
no whole-cycle latency added.

    python3 tools/hbm_hc_tile_xl_gen.py --out physical/hbm_accel_die_views/hcp/rtl_tile_xl
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hbm_hub_quarter_gen as H

PORTS = 'physical/hbm_accel_die_views/hcp/r25gq/ports/hfd_hc/ports.json'
STRIP = 30.24          # 70 x 0.432: 162 bc pins / edge over M5 0.096 + M7 0.128 slots (~5.4 b/um); ~870 flops
LANE_W, LANE_H = 85.32, 115.02
TILE_W = round(STRIP + LANE_W + 1.512, 3)      # 117.072 = 2,168 sites
TILE_H = 120.96                                 # 448 rows; core 119.88 = 1.08 mod 5.4 = the su tile PDN phase (pdn_tile_xl.tcl: a VDD M6 strap below the lane, a VSS strap above it, PSM-0069)


def rename(s):
    return s.replace('hfd_su_tile', 'hfd_hc_tile').replace('OT_SU_TILE_MUT_NOLOCKUP', 'OT_HC_TILE_MUT_NOLOCKUP')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True); ap.add_argument('--ports', default=PORTS)
    a = ap.parse_args()
    H.TILE_SW = STRIP
    q = dict(H.QUARTERS['hcp']); p = H.Plan(q, json.loads(Path(a.ports).read_text())); p.tiled = True
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / 'hfd_hc_tile_xl.sv').write_text(rename(H.emit_tile_xl(p)))
    (out / 'hfd_hc_tile.sv').write_text(rename(H.emit_tile(p)))
    (out / 'ot_dsrom_su_hcpost_lane_pr_simstub.sv').write_text(H.emit_stub(p))
    (out / 'io_place.tcl').write_text(rename(H.emit_tile_io(p, TILE_W, TILE_H)))
    (out / 'macro_place.tcl').write_text(f'place_macro -macro_name {{u_lane}} -location {{{STRIP:.3f} {H.TILE_LANE_Y:.3f}}} -orientation R0 -exact\n')
    (out / 'tile.json').write_text(json.dumps(dict(
        master='hfd_hc_tile_xl', lane=q['lane'], lane_params=q['params'], w_um=TILE_W, h_um=TILE_H, strip_w=STRIP,
        lane_xy=[STRIP, H.TILE_LANE_Y], LB=p.LB, LO=p.LO, WCT=p.WCT, RB=p.RB, RA=p.RA,
        quarter=dict(tiles=p.N, chains=p.KC, tiles_per_chain=p.NT),
        registered_bits=p.LB + 1 + p.LO + p.WCT, lockup_bits=p.LB + 1 + p.WCT,
        data_cycles_added=0, visibility_half_cycles_added=1), indent=1) + '\n')


if __name__ == '__main__':
    main()
