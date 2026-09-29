#!/usr/bin/env python3
"""V4.1 ROM layer-die re-fit with the PLACED ROM-array element pair (W10; W1 pack generator in REFIT mode).

    python3 tools/v41_floorplan_refit.py \
        --q-pair results/physical_abi3/asap7/chip/v41_w10_elem/<fp8/fp4 pair>.json \
        --bf-pair results/physical_abi3/asap7/chip/v41_w10_elem/<bf16 pair>.json \
        --output results/floorplan/v41_pack_refit_w10.json

What changes against W1's pack (results/floorplan/v41_pack_expanded_woa.json):
* MAC strip of a pair column = the logic strip the placed pair was routed in (its die minus two ROMs, the
  capture channels and margins), for the FP8/FP4 pair; BF16-capable pairs (1,024 = 2,048 BF16 macros / 2) get
  their own columns at the BF16 pair's strip width.
* Hub partitions sized from the microarchitecture model's area ledger (tools/uarch_model.py area_ledger,
  results/uarch/v41_rom.json proposal: attention + indexer, stream unit + SFU) instead of the analytical
  ledger; VM, collective, gather and HC keep W1's reservations.
* Stage power gating (W14 model, main 76053c23): every gated region carries header/footer switch area
  SWITCH_FRACTION of its logic (ASSUMED, see SWITCH_BASIS); the VM (retention), the wake controller and the
  SerDes control form an always-on island in the hub's VM column (AON_MM2 ASSUMED for the controller and
  isolation cells).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import v41_floorplan_pack as P  # noqa: E402
import v41_w10_elem_pnr as E  # noqa: E402

SWITCH_FRACTION = 0.05
SWITCH_BASIS = ("ASSUMED 5% of gated logic area for coarse-grain (ring/column) header/footer switches: "
                "coarse-grain gating carries less switch area than fine-grain (K. Shi, D. Howard, 'Challenges in "
                "sleep transistor design and implementation in low-power designs', DAC 2006, "
                "doi:10.1145/1146909.1146943; M. Keating et al., Low Power Methodology Manual, Springer 2007, "
                "ch. 5); no ASAP7 switch cell is characterised, so the fraction is not measured")
AON_MM2 = 0.10          # ASSUMED: wake controller, isolation and SerDes low-power control (VM itself is retained)
BF16_PAIRS = 1024


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def placed_strip(rec: dict) -> dict:
    """The logic strip of a placed pair: die width minus two ROMs, four capture channels and two margins."""
    pr = rec["place_and_route"]
    m = pr["metrics"]
    die_w = pr["floorplan"]["die_area_um"][2]
    nrom = 2 if "NB=2" in rec["runner"]["argv"] else 1
    rom_w = E.ROM[1]
    strip = die_w - nrom * rom_w - 2 * nrom * E.CH - 2 * E.MARGIN
    logic_um2 = m["standard_cell_area_um2"]
    logic_region_um2 = strip * (E.ROM[2] + 2 * E.GAP)
    return dict(macros=nrom, strip_um=round(strip, 3), die_w_um=die_w, standard_cell_um2=logic_um2,
                logic_utilisation=round(logic_um2 / logic_region_um2, 3),
                setup_wns_ns=m.get("setup_wns_ns"), fmax_hz=m.get("fmax_hz"), drc=m.get("drc_errors"),
                closed=bool(m.get("setup_wns_ns", -1) >= 0 and m.get("hold_wns_ns", -1) >= 0
                            and m.get("drc_errors", 1) == 0))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--q-pair", type=Path, required=True)
    ap.add_argument("--bf-pair", type=Path, required=True)
    ap.add_argument("--model", type=Path, default=ROOT / "results/uarch/v41_rom.json")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--svg-dir", type=Path, default=ROOT / "results/floorplan")
    a = ap.parse_args(argv)
    q = placed_strip(json.loads(a.q_pair.read_text()))
    b = placed_strip(json.loads(a.bf_pair.read_text()))
    model = next(r for r in json.loads(a.model.read_text())["rows"] if r["design"] == "proposal")
    ar = model["area"]
    g = 1 + SWITCH_FRACTION
    hub = {"ATTENTION": (ar["attention"] + ar["indexer"]) * g,
           "SU_VECTOR": (ar["su_lanes"] + ar["sfu_lanes"]) * g}
    P.REFIT = dict(strip_q_um=q["strip_um"] * g, strip_bf_um=b["strip_um"] * g, bf_pairs=BF16_PAIRS,
                   hub_mm2=hub, basis="W10 placed pairs + model hub + power switches")
    rec = P.run("expanded_woa", a.svg_dir, write_views=False)
    rec["schema"] = "opentallas.v41.floorplan_pack_refit.v1"
    rec["refit"] = dict(
        q_pair=dict(record=str(a.q_pair), sha256=sha(a.q_pair), **q),
        bf16_pair=dict(record=str(a.bf_pair), sha256=sha(a.bf_pair), **b),
        hub_mm2_from_model=hub, model_record_sha256=sha(a.model),
        power_gating=dict(switch_fraction=SWITCH_FRACTION, basis=SWITCH_BASIS, always_on_island_mm2=AON_MM2,
                          always_on=["VM (state retention)", "wake controller (staggered 1 us wake)",
                                     "SerDes low-power-idle control (5 us pre-wake)"],
                          gated=["ROM field element strips (region clock gating + switches)",
                                 "hub dedicated units", "HBM PHY (powered down)"],
                          token_path="no wake on the single-user token path: stage idle >= 219 us between "
                                     "tokens (W14 model)"),
        tool_sha256=sha(Path(__file__).resolve()))
    a.output.write_text(json.dumps(rec, separators=(",", ":")) + "\n")
    cap = rec["capacity"]
    geo = rec["geometry"]
    print(json.dumps(dict(strip_q=geo["strip_w_um"], strip_bf=geo["strip_bf_w_um"], pitch_q=geo["pair_pitch_um"],
                          pitch_bf=geo["pair_pitch_bf_um"], columns=geo["pair_columns"], bf_columns=geo["bf_columns"],
                          hub=geo["hub"], slots=cap["pair_row_slots"], used=cap["used_pair_rows"],
                          spare=cap["spare_pair_rows"], bf_slots=cap["bf_pair_row_slots"],
                          bf_used=cap["bf_pair_rows_used"], closes=cap["closes"], bf_closes=cap["bf_closes"],
                          legal=rec["legality"]["legal"], q=q, bf=b), indent=1))


if __name__ == "__main__":
    main()
