"""Private HBM p37 split-PHY as-built candidate; never edits a plan or source manifest."""
import argparse
import copy
import json
from pathlib import Path

PARENTS = {"u_lk_N0": "lk_N0", "u_lk_N2": "lk_N2", "u_lk_S0": "lk_S0",
           "u_lk_S1": "lk_S1", "u_lk_S3": "lk_S3"}
FILES = ["results/die_hbm_1106/rx_bm3_p37/ot_pdie_serdes__p37comp.sv",
         "rtl/hbm_accel/cores_split/reform_1104b/ot_pdie_serdes_split.sv",
         "rtl/hbm_accel/cores_split/reform_1106/ot_pdie_serdes_rx_bm3.sv"]


def candidate(plan, asbuilt, source):
    parents = set()
    for t in plan["partition_types"].values():
        for h in t.get("hard_cores", []):
            path = h.get("physical_inst", "")
            if ".u_fcore." in path and path.split(".u_fcore.")[0] in PARENTS:
                parents.add(path.split(".u_fcore.")[0])
    if parents != set(PARENTS):
        raise ValueError("candidate requires the exact five p37 split-PHY plan parents")
    files = [str((Path(source) / f).resolve()) for f in FILES]
    for f in files:
        if not Path(f).is_file():
            raise ValueError("missing split-PHY source: " + f)
    out = copy.deepcopy(asbuilt)
    out.setdefault("sub_core_leaf", {}).update(PARENTS)
    out.setdefault("substitute_inst", []).extend(
        dict(inst=leaf, module="ot_pdie_serdes__p37glue",
             reason="Real p37 split composition already named by this plan's hard-core paths; no new pin cycles")
        for parent, leaf in sorted(PARENTS.items()))
    out["files"] = list(dict.fromkeys(out.get("files", []) + files))
    out["prefer"] = list(dict.fromkeys(out.get("prefer", []) + files))
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan", required=True)
    p.add_argument("--asbuilt", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    result = candidate(json.loads(Path(a.plan).read_text()), json.loads(Path(a.asbuilt).read_text()), a.source)
    Path(a.out).write_text(json.dumps(result, indent=2) + "\n")
