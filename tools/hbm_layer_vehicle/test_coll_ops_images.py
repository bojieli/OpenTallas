#!/usr/bin/env python3
"""VEH-FMT-COLL2: coll_ops_images on the committed DS fixtures -- GROUP_REDUCE_MCAST on-die phase emitted fixture-exact
(gather_record reconstructs O from the checked sectors), TOPK_MERGE / ROW_GATHER reported cross_die_only / unpriced."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "results/rtl/hbm_ds_layer_tput_1018/fixtures"
BND = ROOT / "results/rtl/hbm_ds_layer_tput_1018/slice_sw/boundary.json"


def run(L, out):
    subprocess.run([sys.executable, "-m", "hbm_layer_vehicle.coll_ops_images", "--fixtures", str(FIX / L), "--boundary",
                    str(BND), "--out", str(out)], check=True, cwd=ROOT / "tools", capture_output=True)
    return json.loads(next(out.glob("*_coll_ops_manifest.json")).read_text())


def main():
    with tempfile.TemporaryDirectory() as t:
        m = run("L02", Path(t) / "L02")
        st = {r["op"]: r["status"] for r in m["records"]}
        assert st == {"COLL.GROUP_REDUCE_MCAST": "emitted_on_die_phase", "COLL.TOPK_MERGE": "cross_die_only",
                      "COLL.ROW_GATHER": "cross_die_only"}, st
        g = next(r for r in m["records"] if r["op"] == "COLL.GROUP_REDUCE_MCAST")
        assert g["F"] == 384 and g["n_words"] == 12288 and len(g["replays"]) == 1 and g["replays"][0]["events"] < 6309
        rep = json.loads((Path(t) / "L02" / f"{g['replays'][0]['name']}.json").read_text())
        vm = [e for e in rep["events"] if e["k"] == "C" and e["port"].startswith("vm:")]
        assert len(vm) == 4 * 384, len(vm)
        m14 = run("L14", Path(t) / "L14")
        assert m14["counts"] == {"cross_die_only": 2, "emitted_on_die_phase": 1, "unpriced": 1}, m14["counts"]
    print("TEST_COLL_OPS_IMAGES PASS")


if __name__ == "__main__":
    main()
