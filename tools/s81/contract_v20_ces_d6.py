#!/usr/bin/env python3
"""S81 contract v20 item D6 (die lead r7, 2026-10-14): the collective ces0 / cesn wires-only parents are DISSOLVED.

Each sp_collective/ce_s<k> slot (432 x 345.6) stays as a keep-out frame with NO parent cell; its 10 CLOSED children stand
directly in sp_collective at slot origin + the child 'at' of tools/ref_tile/specs_dscoll_ces/dscoll_ces{0,n}_pc.json, one
clock entry per child (die delivers phi - (entry wire + R_child) independently; R_child = the child view's measured TT
boundary mean from its insertion.json, the pc clock maps), child pins adopted as routed (no re-pin), 0 added cycles.
Why: cesn_pc pc3 EARLY_FAIL_SETUP -429.7 and ces0_pc pc2b native audit FAIL had one structural cause -- a wires-only
parent adds face routing after every child's own launch (245-355 ps vs the 220 budget), el1013-s81-pqroot.log 17:18.

Writes c['v20_ces_d6'] (idempotent; contract version is bumped by the v20 revision, not here).
Usage: contract_v20_ces_d6.py [--check]
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "results/arch/hier_contract_1011/s81.json"
SPEC = ROOT / "tools/ref_tile/specs_dscoll_ces"


def build(c):
    slots = {s["name"]: s for s in c["slots"] if s.get("name", "").startswith("sp_collective/ce_s")}
    assert len(slots) == 4, sorted(slots)
    out = {"decision": "D6 option A (el1011-s81die.log 2026-10-14 18:06, confirmed r7 21:2x): no ces parent cell; children "
                       "die-placed inside sp_collective; per-child clock entry phi - R_i; child pins adopted",
           "owner_rules": "static cycle schedule (owner 10-14 18:59): the ces sources include rtl/common/ot_link_credit.sv; "
                          "credit seams must become compiler-scheduled static slots before native qualification. Children "
                          "whose CLOSED view fails the native pin audit (cesc0: launch cr_o 290 ps) are bound only after "
                          "their re-route (dscoll_cesc0_ln-pr1) closes and passes the native audit.",
           "slots": {}}
    for name, s in sorted(slots.items()):
        pc = "dscoll_ces0_pc" if s["cell"] == "dsfd_coll_ces0" else "dscoll_cesn_pc"
        spec = json.loads((SPEC / f"{pc}.json").read_text())
        cmap = json.loads((SPEC / f"{pc}_clock_map.json").read_text())
        assert (spec["outline"]["w"], spec["outline"]["h"]) == (s["outline"]["w"], s["outline"]["h"]), (name, spec["outline"])
        assert s["origin"].get("orient", "R0") == "R0", name
        ents = {e["child_instance_pattern"]: e for e in cmap["entries"]}
        ox, oy = s["origin"]["x"], s["origin"]["y"]
        kids = []
        for ch in spec["children"]:
            e = ents[ch["inst"]]
            ins = ROOT / e["insertion_source"]
            sha = hashlib.sha256(ins.read_bytes()).hexdigest()
            r_tt = json.loads(ins.read_text())["tt"]["boundary"]["mean"]
            kids.append({"inst": ch["inst"], "view": ch["view"], "master": e["child_master"],
                         "origin_in_sp_collective_um": [round(ox + ch["at"][0], 3), round(oy + ch["at"][1], 3)],
                         "orient": "R0", "clock_entry": f"ck_{name.split('/')[1]}_{e['entry'][3:]}",
                         "child_clock": e["child_clock"],
                         "R_child_tt_ps": r_tt, "insertion_sha256": sha,
                         "insertion_current": sha == e["insertion_sha256"]})
        out["slots"][name] = {"frame": {"origin": [ox, oy], "w": s["outline"]["w"], "h": s["outline"]["h"],
                                        "keepout": True, "parent_cell": None},
                              "replaces": s["cell"], "spec": f"tools/ref_tile/specs_dscoll_ces/{pc}.json",
                              "children": kids}
    out["children_total"] = sum(len(v["children"]) for v in out["slots"].values())
    out["clock_entries_total"] = out["children_total"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    c = json.loads(CON.read_text())
    rec = build(c)
    stale = [k["inst"] + "@" + n for n, v in rec["slots"].items() for k in v["children"] if not k["insertion_current"]]
    print(f"v20_ces_d6: {rec['children_total']} children in {len(rec['slots'])} frames; stale clock-map R: {stale or 'none'}")
    if a.check:
        return 0 if c.get("v20_ces_d6") == rec else 1
    c["v20_ces_d6"] = rec
    CON.write_text(json.dumps(c, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
