#!/usr/bin/env python3
"""DIE-KV-67 11-04: qkd_kvs_pcf_h_head_p = the PCF RTL under its own master name.

kv3_pc__cl254f2e73 and kv3_pc__cl5a95b461 hold both PCF pin tables (kvpc0_f on fMY, the others on fMX) and a parent kit
takes one LEF per master.  The two tables differ only in grp pins of the N face, so the body stays identical and only
the top module name changes.

    rf_kv3_pcf_fmy.py REPO
"""
import json
import re
import shutil
import sys
from pathlib import Path

SRC, DST = "qkd_kvs_pcf", "qkd_kvs_pcf_h_head_p"
ROOT = "results/kv_host_regen_1/rtl_rf3"
PINS = "physical/die_plan/qwen_kvsys/plan_of_record/pins/qkd_kvs_pc_h_head_p_pins_fMY_r25_rf1_rf3f.json"


def main(repo):
    repo = Path(repo).resolve()
    a, b = repo / ROOT / SRC, repo / ROOT / DST
    if b.exists():
        shutil.rmtree(b)
    b.mkdir()
    for f in a.glob("*.sv"):
        if f.name != f"{SRC}.sv":
            shutil.copy(f, b / f.name)
    top, n = re.subn(rf"\bmodule {SRC}\b", f"module {DST}", (a / f"{SRC}.sv").read_text())
    assert n == 1, n
    (b / f"{DST}.sv").write_text(top)
    cj = json.loads((a / f"{SRC}_core.json").read_text())
    pins = json.loads((repo / PINS).read_text())
    assert pins["core"] == DST, pins["core"]
    names = {p["name"] for p in pins["pins"]}
    assert names == set(cj["pin_class"]), sorted(names ^ set(cj["pin_class"]))[:5]
    cj["module"] = DST
    cj["files"] = [f.replace(f"/{SRC}/{SRC}.sv", f"/{DST}/{DST}.sv").replace(f"/{SRC}/", f"/{DST}/") for f in cj["files"]]
    cj["report"]["pins_file"] = PINS
    cj["report"]["note"] = f"{SRC} body under its own master name (rf_kv3_pcf_fmy.py); pins = this table"
    (b / f"{DST}_core.json").write_text(json.dumps(cj, indent=1) + "\n")
    print("RF_KV3_PCF_FMY", DST, len(cj["files"]), len(names))


if __name__ == "__main__":
    main(sys.argv[1])
