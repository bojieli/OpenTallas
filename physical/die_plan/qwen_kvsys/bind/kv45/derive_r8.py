#!/usr/bin/env python3
"""Derive native KV45 landing pads from its actual metadata bind, never a digest relabel."""
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
seed = root / "runs" / sys.argv[2]
tree = root / "t45"
base = Path("physical/die_plan/qwen_kvsys")
target = base / "bind/kv45/tables"
(tree / target).mkdir(parents=True, exist_ok=True)


def run(*args):
    subprocess.run([sys.executable, *map(str, args)], cwd=tree, check=True)


run(base / "r8/r8_fault_exempt.py", seed / "bus_groups.json", target / "fault_exempt.json")
run(base / "r8/r8_invariant_split.py", base / "die_plan.json", target / "fault_exempt.json", target / "invariant_groups.json")
run("tools/die_plan/r8.py", "pads", base / "die_plan.json", target / "invariant_groups.json",
    "--out", target / "r8", "--bus", "leaf", "--replica", "type")
landing = target / "r8/qwen_kvsys_r8_landing.json"
run("tools/die_plan/r8.py", "check", base / "die_plan.json", target / "invariant_groups.json",
    "--landing", landing, "--bus", "leaf", "--replica", "type", "--json", target / "r8_check.json")
a = json.loads((tree / base / "bind/kv45/asbuilt_native_pass0.json").read_text())
a["land_align"] = "r8"
a["land_r8"] = str(landing)
a["note"] = "Native KV45 fresh R8 pass; PV entry/row/W-request extras and regenerated schedule parameters still required."
(tree / base / "bind/kv45/asbuilt_native_r8.json").write_text(json.dumps(a, indent=1) + "\n")
print("fresh native R8 recipe ready; final bind gate not yet evaluated")
