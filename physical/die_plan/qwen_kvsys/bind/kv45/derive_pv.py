#!/usr/bin/env python3
"""Regenerate the PV entry pads from the actual native KV45 landed graph."""
import json
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
seed = root / "runs" / sys.argv[2]
tree = root / "t45"
base = Path("physical/die_plan/qwen_kvsys")
bind = base / "bind"
tables = bind / "kv45/tables"
landing = tables / "r8/qwen_kvsys_r8_landing.json"
rules = tables / "native_r8_parameter_rules.json"
env = dict(os.environ, PYTHONPATH=str(root / "python"))


def run(*args, check=True):
    return subprocess.run([sys.executable, *map(str, args)], cwd=tree, env=env, check=check)


# The PV optimizer precedes the full parameter checker: the latter correctly
# needs uniform trunk/flag legs, which this pass is constructing. Only its
# independent vport W/RT rules are inputs to the entry-table boot calculation.
spec = importlib.util.spec_from_file_location("kv45_vport_rules", tree / bind / "kv_param_regen_check.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
vport = module.r_vport(module.Bind(seed))
(tree / rules).write_text(json.dumps(dict(schema="opentallas.die_plan.kv_param_rules.v1",
    note="PV bootstrap inputs only; full trunk/flag checker follows the newly padded bind", rules=vport), indent=1) + "\n")
run(bind / "kv_pv_pads_plan.py", seed, landing, tables / "pv_lp.json",
    "--option", "bound", "--entry", "--tie-types", base / "die_plan.json", "--tie-only", "cross")
run(bind / "kv_pv_entry_table.py", seed, tables / "pv_lp.json", base / "die_plan.json",
    landing, rules, tables / "pv_entry.json")
run(bind / "kv_pv_entry_to_r8.py", tables / "pv_entry.json", landing, tables / "pv_extra.json")
a = json.loads((tree / bind / "kv45/asbuilt_native_r8.json").read_text())
a["land_r8_extra"] = [str(tables / "pv_extra.json")]
a["note"] = "Native KV45 R8 + newly derived PV entry pads; kg rows/W-request and final schedule follow."
(tree / bind / "kv45/asbuilt_native_pv.json").write_text(json.dumps(a, indent=1) + "\n")
print("native PV entry recipe ready; final gate remains pending")
