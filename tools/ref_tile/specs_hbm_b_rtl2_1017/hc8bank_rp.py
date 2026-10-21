#!/usr/bin/env python3
"""HBM-HCBANK8 10-20 (H.STA.BLK.17): HC ring bank kits with PLACED regional clock pins (successors of the _rr kits).

_rr --cts gates (10-20, ot-epyc7) FAILED:
  b0_rr  CTS: glue root clk_r0 spread 154.2 ps TT (all_internal_only, 800 sinks; insertion 463 ps); b0_rh clk_r0 174.9 ps
  cb_rr / cb_rh  GPL-0305 divergence (routability inflation +260 %, overflow stuck at 0.12).
Evidence: every lane-row / CPO / stage root port was left to the IO placer (pins "ANY"): avg sink wire clk_q0 943 um vs
clk_q1 442 um, clk_c 1,267 um -- the root pin landed far from its own region, so each regional tree hung off a long
trunk (insertion 463..783 ps vs clk 367 ps) and its branches were unbalanced across the macro row.
Structural change (no RTL / netlist change: same _rr tops, ring witnesses ring_rr_*, census rr PASS max 32):
  * every regional root pin is PLACED on the face beside its own region, at the region's centre line:
      row root clk_r<r>  at the lane-row centre (y = 43.2 + 172.8 r + 67.5) on the free face beside the row
      CPO root clk_q<r>  on the same face, between row r and the out face
      clk_c              on the free face at the tile mid-height (stage control sits between the rows)
  * cb_rp: cb geometry (SRAMs W, leaves E) with the anchored scalar pin flops DROPPED (rc3 placed without them; the
    divergence appeared only with the 329 anchored W-face flops beside the x SRAM column).  Clock pins on the free E face.
  * cb_rw: (parallel fallback) leaves moved beside the chain faces (b0 geometry: leaves x 43.2 / 216, weight SRAMs x 432,
    x SRAMs x 648) so the 2,048-bit sum_in bus no longer crosses the SRAM column; clock pins on the free E face.
  * b0_rp: b0 geometry unchanged; clock pins on the free W face (leaf side).
Usage: python3 tools/ref_tile/specs_hbm_b_rtl2_1017/hc8bank_rp.py  (writes physical/ref_tile/hbm_hcq_bank_{cb_rp,cb_rw,b0_rp}/spec.json)
"""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("hcbank6_rc", HERE / "hcbank6_rc.py")
H6 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(H6)
RT = H6.RT
BRANCH = "claude/hcbank8-1020"
ROW_Y0 = [43.2 + 172.8 * r for r in range(4)]


def rng(c):
    return [round(c - 0.5, 3), round(c + 0.5, 3)]


def make(src, name, face, out_face, geometry_mirror=None, drop_anchor=False, why=""):
    s = json.loads((RT / src / "spec.json").read_text())
    s["name"] = name
    if geometry_mirror is not None:
        s["children"], s["macros"] = H6.geometry(geometry_mirror)
    pins = s["pins"]
    placed = ["clk_c"] + [f"clk_r{r}" for r in range(4)] + [f"clk_q{r}" for r in range(4)]
    pins["ANY"] = [p for p in pins["ANY"] if p not in placed]
    pins[face] = pins.get(face, []) + placed
    pr = s.setdefault("pin_ranges", {})
    for r in range(4):
        yc = ROW_Y0[r] + 67.5
        pr[f"clk_r{r}"] = rng(yc)
        # CPO sums of row r sit between the row and the out face (N: above the row, S: below it)
        pr[f"clk_q{r}"] = rng(yc + 95.0 if out_face == "N" else yc - 95.0 if r else yc - 50.0)
    pr["clk_c"] = rng(367.2 + 8.0)
    if drop_anchor:
        ov = dict(s.get("orfs_vars", {}))
        ov.pop("OT_OFLOP_PORT_RE", None)
        s["orfs_vars"] = ov
        s["io_flop_at_pins"] = False          # = the rc3 kit, which placed (no face anchoring at all)
    s["structural_change"] = (
        f"HBM-HCBANK8 10-20 successor of {src} (--cts gate FAILED: b0_rr clk_r0 spread 154.2 ps TT internal-only, "
        "cb_rr GPL-0305 divergence).  Every regional glue root pin (clk_r0..3, clk_q0..3, clk_c) is PLACED on the "
        f"{face} face beside its own region at the region centre line (the _rr pins were left to the IO placer: clk_q0 "
        "avg sink wire 943 um, clk_c 1,267 um, insertion 463..783 ps). " + why +
        " Same RTL top / netlist as the _rr kit (ring_rr witnesses, native census rr PASS max 32).")
    s["reroute_reason"] = {"kind": "structural", "failed_job": f"ref_gate {src} 10-20 (CTS spread / GPL-0305)",
                           "why": "regional root pins placed beside their regions" + ("; " + why if why else "")}
    j = s["job"]
    j["owner"] = "Claude:DRIVE-HBM/HBM-HCBANK8"
    j["branch"] = BRANCH
    j["purpose"] = f"HC ring bank {name}: lane-row regional roots with placed root pins ({why or 'pins only'})"
    j["views_to"] = f"physical/ref_tile/{name}/views"
    j["record_to"] = f"results/rtl/ref_tile/{name}"
    d = RT / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    print("wrote", d / "spec.json")


if __name__ == "__main__":
    make("hbm_hcq_bank_b0_rr", "hbm_hcq_bank_b0_rp", "W", "N")
    make("hbm_hcq_bank_cb_rr", "hbm_hcq_bank_cb_rp", "E", "S", drop_anchor=True,
         why="cb geometry kept; anchored scalar pin flops dropped (GPL-0305 appeared only with them)")
    make("hbm_hcq_bank_cb_rr", "hbm_hcq_bank_cb_rw", "E", "S", geometry_mirror=True,
         why="leaves moved beside the chain faces (leaves x 43.2 / 216, SRAMs x 432 / 648): sum_in no longer crosses the SRAM column")
