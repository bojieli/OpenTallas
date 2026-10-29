#!/usr/bin/env python3
"""Copy a HEAD plan and replace its existing KP4 Chien child by supplied views.

No RTL is rewritten, no physical view is fabricated, and no cycles are added.
The extracted child is the original ``ot_s81_kp4_dchn`` at its existing path.
The parent source profile selects the existing OT_KP4_DEC_HARD spelling so
the child is instantiated without a parameter override. Other KP4 children
and the two SRAM macros remain unchanged.
"""
import argparse
import copy
import json
import os
from pathlib import Path

MODULE = "ot_s81_kp4_dchn"
INST = "u_phy.u_link.u_dec.u_chn"


def apply(plan, core):
    required = ("module", "lef", "lib", "origin_um", "outline_um", "pins_file", "obs_max")
    missing = [k for k in required if k not in core]
    if missing:
        raise ValueError(f"real extracted child descriptor missing {missing}")
    if core["module"] != MODULE:
        raise ValueError(f"expected existing child {MODULE}, got {core['module']}")
    if core.get("inst", INST) != INST:
        raise ValueError(f"child instance must remain {INST}")
    if core.get("params"):
        raise ValueError("hard child uses unchanged default MUT=0; no parameter override")
    if core["obs_max"] not in ("M4", "M5", "M6", "M7"):
        raise ValueError("core signal layers must stay <=M7")
    out = copy.deepcopy(plan)
    t = out["partition_types"]["hd_serdes"]
    contents = [c for c in t["contents"] if c["inst"] == "u_phy"]
    if len(contents) != 1 or contents[0]["module"] != "ot_s81hd_serdes_link":
        raise ValueError("HEAD SerDes source must remain the real KP4 link adapter")
    if any(c["inst"] == INST for c in t.get("hard_cores", [])):
        raise ValueError("Chien child is already extracted")
    x, y = core["origin_um"]
    w, h = core["outline_um"]
    tw, th = t["outline_um"]
    if min(x, y) < 0 or min(w, h) <= 0 or x + w > tw or y + h > th:
        raise ValueError("extracted child must fit the existing SerDes outline")
    for other in t.get("hard_cores", []):
        ox, oy = other["origin_um"]
        ow, oh = other["outline_um"]
        if x < ox + ow and ox < x + w and y < oy + oh and oy < y + h:
            raise ValueError(f"extracted child overlaps {other['inst']}")
    c = copy.deepcopy(core)
    c["inst"] = INST
    t.setdefault("hard_cores", []).append(c)
    defines = t.setdefault("verilog_defines", [])
    if "OT_KP4_DEC_HARD" not in defines:
        defines.append("OT_KP4_DEC_HARD")
    # Old cells=0 was a PHY-glue estimate. Avoid inventing the new synthesized
    # count: the measured parent cap must be established after extraction.
    t["note"] = t.get("note", "") + "; existing KP4 Chien child extracted, zero added cycles; parent synth count pending"
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--core", required=True, help="descriptor of the actual supplied physical child view")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    source, dest = Path(a.plan).resolve(), Path(a.out).resolve()
    if source == dest:
        raise SystemExit("write a candidate copy; do not overwrite the input plan")
    corefile = Path(a.core).resolve()
    p = apply(json.loads(source.read_text()), json.loads(corefile.read_text()))
    # Pin tables are plan-relative, unlike repo-relative LEF/lib/source paths.
    # Keep existing hk3/hk4 assets pointing at their original files when the
    # candidate is written to a new result directory. New child tables are
    # relative to the supplied child descriptor.
    for name, t in p["partition_types"].items():
        for c in t.get("hard_cores", []):
            if not c.get("pins_file") or Path(c["pins_file"]).is_absolute():
                continue
            base = corefile.parent if name == "hd_serdes" and c["inst"] == INST else source.parent
            c["pins_file"] = os.path.relpath((base / c["pins_file"]).resolve(), dest.parent)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(p, indent=2) + "\n")
    print(json.dumps(dict(status="CANDIDATE", module=MODULE, added_cycles=0,
                          physical_signoff="NOT_CLAIMED", parent_cell_count="PENDING_SYNTH")))


if __name__ == "__main__":
    main()
