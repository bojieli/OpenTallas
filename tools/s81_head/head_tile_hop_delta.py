#!/usr/bin/env python3
"""DIE-HEAD-70 (COORD 11-05 12:12, OWNER 11-03 'pin cycles are the lever'): one-block HEAD plan delta for hd_tile only.

Sets the u_core (ot_s81hd_tile_native) long-hop options in partition_types.hd_tile.contents and republishes the hd_tile
wrapper (published/ot_s81hd_tile_p.sv) with the tools root's gen.py, exactly as head_cland_stage_delta.py --republish.
No outline, pin, bus, macro, strap, clock or reset key changes; every other type's wrapper is copied byte-equal.

  ROW_IN_REG 1  row_in = row0 + 32q registered per A core (row0 = ID strap: 0 data cycles)
  TEN_HOP    1  kept ten hop register by the control / compare logic (ten = static strap: 0 data cycles)
  FLT_XHOP   1  third sticky fault hop (0 result cycles)
  BST        3  x / go broadcast depth 2 -> 3: +1 cycle on the tile's own result, +1 once per lm-head position

usage: head_tile_hop_delta.py SRC_PREPARED_DIR OUT_DIR --republish TOOLS_ROOT
"""
import argparse, json, shutil, sys
from pathlib import Path

PARAMS = {"ROW_IN_REG": "1", "TEN_HOP": "1", "FLT_XHOP": "1", "BST": "3"}
TYPE = "hd_tile"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src", type=Path); ap.add_argument("out", type=Path)
    ap.add_argument("--republish", type=Path, required=True, help="tools root whose gen.py regenerates published/")
    a = ap.parse_args(argv)
    root = a.republish.resolve()
    sys.path[:0] = [str(root / "tools/s81_head")]
    import head_cland_stage_delta as D
    plan = json.loads((a.src / "source_plan.json").read_text())
    T = plan["partition_types"][TYPE]
    core = [c for c in T["contents"] if c.get("inst") == "u_core"]
    assert len(core) == 1 and core[0]["module"] == "ot_s81hd_tile_native", core
    old = dict(core[0]["params"])
    assert not set(PARAMS) & set(old), ("already set", old)
    core[0]["params"].update(PARAMS)
    if a.out.exists():
        D.writable(a.out)
        shutil.rmtree(a.out)
    shutil.copytree(a.src, a.out, symlinks=True)
    D.writable(a.out)
    (a.out / "source_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
    D.republish(a.out, root, [TYPE], a.out / "source_sidecar.json")
    report = dict(event="l48uf-tilehop", tool="tools/s81_head/head_tile_hop_delta.py", type=TYPE,
                  params_before=old, params_after=core[0]["params"], sidecar_changed=False,
                  data_cycles_added={"ROW_IN_REG": 0, "TEN_HOP": 0, "FLT_XHOP": 0,
                                     "BST": "+1 on the tile own result, +1 once per lm-head position"})
    (a.out / "tilehop_report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
