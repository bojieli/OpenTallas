#!/usr/bin/env python3
"""Prepare the coll_ucie ABI/path/track/halo correction, held for parent re-packing.

This writes a PROPOSAL, never the canonical plan. The licensed PHY footprint
remains 777.6 square. Its selected native BB exports lclk, so its matching
nface_tall_g5_lclk_1020 LEF/TT/FF views replace the stale base views. A 36-nm
x phase aligns every native M5 signal pin with the kit's symmetric tracks.
The existing 777.6-wide slot cannot hold the macro plus the required channels;
the 803.52-wide proposal overlaps the two eastern peers and is NOT routable
until the parent event re-packs them and regenerates interfaces/clock/PG.
"""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan")
    ap.add_argument("out", type=Path)
    ap.add_argument("--proposal-only", action="store_true", required=True)
    a = ap.parse_args()
    raw = json.load(open(a.plan))
    t = raw["partition_types"]["coll_ucie"]
    assert t["outline_um"] == [777.6, 1641.6]
    c = next(c for c in t["contents"] if c["inst"] == "u_io_ucie")
    assert c["outline_um"] == [777.6, 777.6]
    c["physical_inst"] = "u_bound.u_io_ucie"
    c["physical_master"] = c["module"]
    prefix = "physical/qwen_missing_phy/nface_tall_g5_lclk_1020/ot_qfd_ucie_x64_phy/ot_qfd_ucie_x64_phy"
    c["lef"], c["lib"] = prefix + ".lef", prefix + "_tt.lib"
    c["origin_um"] = [12.996, 4.32]
    t["outline_um"][0] = 803.52
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "PROPOSAL_NOT_RELEASED.json").write_text(json.dumps(raw) + "\n")
    (a.out / "proposal.json").write_text(json.dumps(dict(
        verdict="HELD_PARENT_REPACK", type="coll_ucie", added_mission_cycles=0,
        old_width_um=777.6, proposed_width_um=803.52, macro_origin_um=c["origin_um"],
        west_channel_um=12.996, east_channel_um=12.924,
        blocking_peers=["coll_f2", "coll_core"], overlap_um=25.92,
        remaining=["parent re-pack and all affected interfaces/clock/PG",
                   "new GEN and actual geometry review before physical dispatch",
                   "licensed abstract remains assumption, physical_qualification_eligible=false"]), indent=1) + "\n")


if __name__ == "__main__":
    main()
