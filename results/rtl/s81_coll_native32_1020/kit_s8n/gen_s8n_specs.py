#!/usr/bin/env python3
"""DRIVE-S81-NTF (10-20) MU-die COLL lane kits dscoll_lane_{w,e}_s8n (TritonCTS) / dscoll_lane_{w,e}_s8nk (k-means K=16):
the tf-less lane tiles of the lepe_mu / lepw_mu landed parents (release die), ported from the DRIVE-S81-COLL s8 kits.

Top dsfd_coll_lane_{w,e}_safe8_ntf = ot_s81ph_coll_lane_safe4 REACH = 2 (s7 relay hops + endpoint RX FIFO write landing,
the s8 structural fix of the s7 GRT reach FAIL: 5,379 pairs > 405 um from c_diff / c_crc_ok / xp_v fanned across the tile),
CH_BOARD 700, TF_CLEANUP 1, NO tf pin and NO parameters (a default-parameter die bind is this view).  Same outline, macro map,
pins (minus tf), PDN, layer contract and clock recipe as s8 / s8k; K=16 fallback for both sides.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BR = "claude/s81-ntf-1020"
BENCH = "results/rtl/s81_coll_native32_1020/reach8n/bench"


def make(side, km):
    if not (km and side == "w"):
        s = json.loads((ROOT / f"physical/ref_tile/dscoll_lane_{side}_s8{'k' if km else ''}/spec.json").read_text())
    else:   # no W s8k: take the E s8k clock recipe onto the W s8 spec
        e = json.loads((ROOT / "physical/ref_tile/dscoll_lane_e_s8k/spec.json").read_text())
        s = json.loads((ROOT / "physical/ref_tile/dscoll_lane_w_s8/spec.json").read_text())
        s["pre_cts_extra"] = e["pre_cts_extra"]
        s["orfs_vars"] = e["orfs_vars"]
    tag = "s8n" + ("k" if km else "")
    name = f"dscoll_lane_{side}_{tag}"
    s["name"] = name
    s["top"] = f"dsfd_coll_lane_{side}_safe8_ntf"
    s["params"] = {}
    for face in s["pins"].values():
        if "tf" in face:
            face.remove("tf")
    s["pin_ranges"].pop("tf", None)
    s["sdc_extra"] = [x for x in s.get("sdc_extra", []) if "tf_fwdclk" not in x]
    s["structural_change"] = __doc__.strip() + "\n\n--- s8 base ---\n" + s["structural_change"]
    j = s["job"]
    for b in j["benches"]:
        if b["name"].startswith("lane_reach8_m"):
            m = b["name"].rsplit("m", 1)[1]
            b["name"] = f"lane_reach8n_m{m}"
            b["cmd"] = b["cmd"].replace("OT_COLL_REACH8=1", "OT_COLL_REACH8N=1")
            for k in ("pass_witness", "fail_witness"):
                if k in b:
                    b[k] = f"{BENCH}/m{m}.log"
    j["extra_paths"] = sorted((set(j["extra_paths"]) - {"results/rtl/s81_coll_native32_1020/reach8/bench"}) | {BENCH})
    j.update(owner="Claude:DRIVE-S81-NTF", branch=BR, tag=tag,
             views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}",
             purpose="DRIVE-S81-NTF: MU-die tf-less param-free lane top (lepe_mu/lepw_mu), s8 REACH=2 fix (RX FIFO write "
                     "landing + s7 relay hops)" + ("; k-means regional CTS K=16" if km else "; TritonCTS") +
                     ". SAFE checklist in kit README.")
    return name, s


if __name__ == "__main__":
    for side in ("w", "e"):
        for km in (False, True):
            name, s = make(side, km)
            d = ROOT / "physical/ref_tile" / name
            d.mkdir(parents=True, exist_ok=True)
            (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
            print("wrote", d / "spec.json")
