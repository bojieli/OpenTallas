"""Declare the already bound SD PHY abstracts without changing logical interfaces.

Run on a copy of the KV plan of record. This is a declaration repair only:
clock/reset, bands, ports, outline and all other types are preserved.
"""
import argparse
import copy
import json
from pathlib import Path


def apply(raw):
    out = copy.deepcopy(raw)
    for tn, width in (("kv3_sys_SD", 522), ("kv3_sys_SD_v1", 521)):
        contents = out["partition_types"][tn]["contents"]
        matches = [c for c in contents if c["inst"] == "serdes"]
        if len(matches) != 1 or matches[0]["module"] != "ot_qfd_serdes_112g_x6_phy":
            raise ValueError(f"{tn}: expected exactly one logical serdes content")
        c = matches[0]
        master = f"ot_qfd_serdes_112g_x6_phy_w{width}"
        prefix = f"physical/die_plan/qwen_kvsys/sd_phy/{master}"
        c.update(physical_inst="u_bound.u_core.u_phy.g_native.u_macro",
                 physical_master=master, origin_um=[17.28, 54.0],
                 outline_um=[1848.96, 972.0], orient="R0",
                 lef=prefix + ".lef", lib=prefix + "_tt.lib")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    raw = json.loads(args.plan.read_text())
    args.output.write_text(json.dumps(apply(raw), indent=1) + "\n")
