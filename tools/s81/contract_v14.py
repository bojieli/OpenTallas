#!/usr/bin/env python3
"""S81 hierarchy contract v13 -> v14 (one-shot, idempotent): relay masters as real hard tiles, the HC POST accept /
dispatch station at the corridor midpoint (coordinator 2026-10-13 03:40), crooty Y clock entry at the SE corner (v4
routes), and the open ces / bgr / sm items carried as explicit rules.  Reads tools/ref_tile/specs/s81_rly_*.json and the
c5 census; rewrites results/arch/hier_contract_1011/s81.json and marks the request ledger.

Usage: contract_v14.py [--check]
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "results/arch/hier_contract_1011/s81.json"
LED = ROOT / "results/arch/hier_contract_1011/s81_v14_requests.json"
CEN = ROOT / "results/physical/die_iter_1012/s81/real_view_census_20261013/c5_census.json"
POST_C = (18220.68, 13327.2)          # reserved centre, die um (results/arch/s81_native_20261013/README.md)
POST_WH = (518.4, 216.0)              # reserved keep-out; the real outline comes from the station kit
CRY_Y_KIT = {"w": 369.36, "h": 300.24, "ctl_x": [367.356, 368.7]}   # claude/s81hc-1013 65a659a58, tag v4-ctl-east


def relay_section() -> dict:
    inst = {m["master"]: m["instances"] for m in json.loads(CEN.read_text())["masters"]}
    ms = []
    for p in sorted(glob.glob(str(ROOT / "tools/ref_tile/specs/s81_rly_*.json"))):
        s = json.loads(Path(p).read_text())
        f = {port: face for face, ports in s["pins"].items() for port in ports}
        w = int(s["top"].split("_")[2])
        ms.append({"master": s["top"], "kit": f"physical/ref_tile/{s['name']}", "w": w, "in_face": f["i"], "out_face": f["o"],
                   "ctl_face": f["ck"], "outline": s["outline"], "instances": inst[s["top"]],
                   "view": f"physical/ref_tile/{s['name']}/views/{s['top']}", "status": "kit + bench + mutant; route pending"})
    ms.sort(key=lambda m: (-m["instances"], m["master"]))
    return {
        "rule": "every dsfd_rly_<W>_<in><out> is a real hard tile (tools/ref_tile), bound by master name; no generated outline "
                "or interim timing model once its view qualifies (tools/s81/native_view_qualify.py)",
        "function": "one register stage, asynchronous active-low clear rs, scalar ck / rs on the third face (rtl/dsrom_sys/s81_glue/ot_s81_rly.sv)",
        "layers": {"layer_cap": "M5", "pg_layer": "M5", "strap_layer": "M6", "pins": "M4 on E/W faces, M5 on N/S faces, 2 tracks (0.096 um) a bit"},
        "outline_classes_um": {"w<=2": [8.64, 8.64], "w<=15": [10.8, 10.8], "w<=68": [15.12, 15.12],
                               "w>=266 N/S": [34.56, 19.44], "w>=266 E/W": [21.6, 30.24]},
        "outline_basis": "from content after the pre-route gate (2026-10-13): flops + BUF-HB4-BUF per output at ~0.5 util, data face >= W x 0.096 um; "
                         "the 17.256 generated slot does not hold W 266 / 283 (PPL-0111) and is 18.6% utilised at W 63",
        "generator": "place at the kit outline on the site grid (not the 17.256 placeholder), pins from the routed LEF, R0 only "
                     "unless mirrored pins stay on track; W 266 / 283 need the wider column slot (34.56 x 19.44 or 21.6 x 30.24)",
        "min_delay": {"element": "outhold BUF-HB4-BUF FIRM at every output pin",
                      "accept": "routed FF ETM: L - H >= 50 ps + skew, L = min clock-to-output - max insertion, H = hold - min insertion",
                      "pre_route_cts": "9 masters over every width / outline class gated --cts, 0 fail: FF insertion 0 (W 1) .. 64.5 ps (W 283), spread <= 3.2 ps, "
                                       "pre-route hold WNS +132..+193 ps (results/rtl/ref_tile/s81_rly_gate_20261013/gates.json)"},
        "jobs": "27 closure-loop jobs s81_rly_<w>_<ff>-v1-05805dc84 submitted 2026-10-13 (no host list)",
        "bench": "rtl/dsrom_sys/s81_glue/test/bench_rly.sh pass (20,000 words exact) + mut (bit 0 inverted, must fail), in every job spec",
        "instances_total": sum(m["instances"] for m in ms),
        "masters": ms,
    }


def apply(d: dict) -> dict:
    if d["version"] >= 14:
        return d
    d["version"], d["updated"] = 14, "2026-10-13"
    d["relay_masters"] = relay_section()
    d["seam_rules"]["relays"] = ("longer seams get die-top relay stations (last segment <= ~100 um at a die pin); v14: relays are the "
                                 "real hard tiles of relay_masters, bound by name")
    d["seam_rules"]["min_delay"] = ("every abutted or short seam: sender L - receiver H >= 50 ps + capture-minus-launch clock skew, measured "
                                    "on the routed FF ETMs (L = min clock-to-output - max insertion, H = hold - min insertion); a deficient "
                                    "master is fixed physically at its own pins (outhold / inhold), never by a Liberty offset")
    # HC POST midpoint station (coordinator 03:40): WITHDRAWN by the coordinator the same day -- HC POST accepted with cost
    # (2.542x unit, 1.653 % end-to-end); the v13 accept position stands, no slot is reserved
    # crooty Y tiles: clock / control entry SW -> SE (v4 routes)
    for s in d["slots"]:
        if s.get("cell") == "ot_s81_hc_crooty_y":
            mir = s["origin"].get("orient") == "MY"
            s["clock_entry"] = {"pin": "sk", "face": "S", "layer": "M5", "offset": CRY_Y_KIT["ctl_x"][0],
                                "width": round(CRY_Y_KIT["ctl_x"][1] - CRY_Y_KIT["ctl_x"][0], 3), "corner": "SE (tile frame)"}
            s["version"] = 14
            s["notes"] = (s.get("notes", "") + " | v14: clock / control (sk, srs) enter on S at tile x 367.356..368.7 (M5, E edge = SE corner; "
                          "was SW) per the v4-ctl-east kits (claude/s81hc-1013 65a659a58; W channel GRT-0116 relieved)"
                          + ("; this instance is MY, so the entry is at the region's W side in the die frame" if mir else "")
                          + "; kit outline 369.36 x 300.24 inside the 369.792 slot; the die clock plan targets this pin.")
    # carried open items (not adopted by this version)
    d["clock_pin_rules"]["dsfd_vm_bgr"] = {"ck": "scalar", "rst": "scalar", "view": "OPEN: bgr28 r5 declares ck / rst [0:0]",
                                          "note": "v14: bind bgr28 only from a view whose LEF clock pin is scalar ck (qualify gate 'scalar'); pin ranges are the v13 v4c record"}
    d["open_items"] = {
        "coll_ces": "ces0 / cesn slot 302.4 x 341.28 stands (v13); a closing route at that outline is still owed by the collective lead",
        "vm_bgr28": "pin ranges recorded v13; scalar ck / rst view owed (clock_pin_rules.dsfd_vm_bgr)",
        "su_sm": "8 SM stop regions 1,231.2 x 1,058.4 stand (v13); sub_layouts.ot_s81_su_sm (smt + 2 x (16 sml + smc + smr + 8 smd)) is owed by the SU lead; no layout is guessed here",
        "su_sw": "dsfd_su_t_sw 572.4 x 637.2 wrapper slots stand until the swt / swe / qbe layout is supplied and fit-checked",
        "hc_cth_growth": "cth 740.88 -> 771.12 NOT adopted: fit check against the corridor and the 26,000 die height pending",
        "hc_tail_crossing": "hc_s t_tf / f_tr and hc_t f_sf / t_sr widen to 3,056 forward / 2,164 return when dsfd_sp_hc_t lands on main",
        "min_delay_gaps": {"ot_s81_hc_ctfn": "L 32.0 / H 19.0 (insertion spread 106 ps): -37.0 same-master zero-wire; needs L - H >= 50 + skew",
                           "cfifo cr": "-59.8; needs L - H >= 50 + skew"},
    }
    d["changelog"].append({"version": 14, "when": "2026-10-13 PT", "change":
        "s81-die: (1) relay_masters: 27 dsfd_rly_<W>_<in><out> masters (29,184 instances, 68% of the generated placeholders) become real "
        "hard tiles bound by name; outlines from content (8.64 / 10.8 / 15.12 sq; W 266 / 283: 34.56 x 19.44 N/S, 21.6 x 30.24 E/W), M5 cap, "
        "scalar ck / rs, outhold BUF-HB4-BUF as the physical minimum-delay element; seam_rules.min_delay (L - H >= 50 ps + skew on routed FF "
        "ETMs). (2) NEW slot hc_post_stn: HC POST accept / dispatch / completion station reserved at the corridor midpoint (coordinator "
        "03:40; ~115 cycles estimated vs 124.19, to be measured). (3) ot_s81_hc_crooty_y clock / control entry SW -> SE (sk, srs on S at x "
        "367.356..368.7, M5; v4-ctl-east). (4) clock_pin_rules.dsfd_vm_bgr scalar; open_items carries ces route, bgr scalar view, SU sm / sw "
        "layouts, cth growth fit check, hc tail crossing width and the two min-delay gaps (ctfn, cfifo cr). No slot grew; no price changed."})
    return d


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    d = apply(json.loads(CON.read_text()))
    names = [s["name"] for s in d["slots"]]
    assert len(names) == len(set(names)), "duplicate slot name"
    rm = d["relay_masters"]
    assert len(rm["masters"]) == 27 and rm["instances_total"] == 29184, (len(rm["masters"]), rm["instances_total"])
    assert not any(s["name"] == "hc_post_stn" for s in d["slots"]), "midpoint station was withdrawn"
    if a.check:
        print("v14 check OK:", len(d["slots"]), "slots,", len(rm["masters"]), "relay masters")
        return 0
    CON.write_text(json.dumps(d, indent=1) + "\n")
    led = json.loads(LED.read_text())
    led["status"] = "contract v14 published 2026-10-13 (tools/s81/contract_v14.py); requests not listed as folded stay open in s81.json open_items"
    for q in led["requests"]:
        if q["id"] in ("relay-masters", "vm-bgr28-pins-and-clock", "coll-ces-outline", "abut-min-delay-and-etm-reference"):
            q["v14"] = "FOLDED"
        if q["id"] == "relay-masters":
            q["status"] = "KITS GATED (9 of 27 pre-route --cts, 0 fail), 27 ROUTE JOBS SUBMITTED"
            q["geometry"]["outline_um"] = "superseded by s81.json relay_masters.outline_classes_um (content-sized; 17.28 failed PPL-0111 at W 283)"
    LED.write_text(json.dumps(led, indent=1) + "\n")
    print("wrote", CON.relative_to(ROOT), "version", d["version"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
