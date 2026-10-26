#!/usr/bin/env python3
"""COORD 2026-10-25 11:31 (PATH-QC-PHYB): the Qwen compute die-edge PHY partitions are the BARE hard macro.

phy_ucie_kv (777.6 x 777.6, ot_qkvd_ucie_x64_phy) and phy_serdes / phy_serdes_b (1563.84 x 2324.16 filled by the
1563.57 x 2320.056 ot_qfd_serdes_112g_x12_phy_s597): the macro's REGISTERED FDI pins are the partition's boundary
registers (standard hard-PHY practice), so the binder emits no ot_dp_st station on the PHY side (the neighbour keeps
its station; tools/die_plan/hard_pinreg.py, tools/die_plan/bind.py reg_hard).  This plan delta, applied by gen_plan.py
after bind_leaves and usable on an existing die_plan.json:

  * the single hard core of a hard type whose module is a PHY below gets "registered_pins": true and its corner lib
    (the checker also reads the sibling _ff/_ss views);
  * the plan boundary block u_pstn (boundary registers etc.) leaves the type -- there is no std-cell room and nothing
    left to put in it -- and the buses bind to the core (leaf <core inst>.<bus>; bus names, widths and pins unchanged).

No other type, bus, lane, port or latency entry changes.

    python3 physical/die_plan/qwen_compute/apply_registered_phy.py PLAN.json     # in place
"""
import argparse
import json
from pathlib import Path

PHY_LIBS = {
    "ot_qkvd_ucie_x64_phy": "physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_tt.lib",
    "ot_qfd_serdes_112g_x12_phy_s597":
        "physical/qwen_missing_phy/nface_tall_1017/ot_qfd_serdes_112g_x12_phy_s597/ot_qfd_serdes_112g_x12_phy_s597_tt.lib",
}


def apply_types(types):
    """types: {name: partition type} (die_plan partition_types / gen_plan P.types), changed in place -> [type names]"""
    done = []
    for tn, t in sorted(types.items()):
        if not t.get("hard"):
            continue
        cores = [c for c in t.get("contents", []) if c.get("inst") != "u_pstn"]
        if len(cores) != 1 or cores[0].get("module") not in PHY_LIBS:
            continue
        if t.get("ft_slots") or t.get("hard_cores"):
            raise ValueError(f"{tn}: registered-pin PHY type with ft slots / hard_cores: not a bare macro")
        c = cores[0]
        c["registered_pins"] = True
        c["lib"] = PHY_LIBS[c["module"]]
        c["note"] = (c.get("note", "") + "; COORD 10-25 11:31: bare macro, its registered FDI pins are the boundary "
                     "registers (no plan stations on this side)").lstrip("; ")
        t["contents"] = [c]
        for b in t.get("buses", []):
            if b.get("leaf", "").split(".")[0] in ("u_pstn", ""):
                b["leaf"] = f"{c['inst']}.{b['name']}"
        done.append(tn)
    return done


def apply(raw):
    if raw.get("die", {}).get("name") != "qwen_compute":
        raise ValueError("registered-pin PHY delta is scoped to qwen_compute")
    return apply_types(raw["partition_types"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("plan", type=Path)
    a = ap.parse_args()
    raw = json.loads(a.plan.read_text())
    print(json.dumps(apply(raw)))
    a.plan.write_text(json.dumps(raw, indent=1) + "\n")


if __name__ == "__main__":
    main()
