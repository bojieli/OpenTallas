#!/usr/bin/env python3
"""Check the exact compiler delta and fail-closed native tail source contract."""
import argparse
import copy
import json
import tempfile
from pathlib import Path
from hbm_layer_vehicle import hc_layer_lower_1021 as H
from hbm_layer_vehicle.native_hc_tail_profile import load

a = argparse.ArgumentParser()
a.add_argument("profile", type=Path)
args = a.parse_args()
p = {"base": [0] * 24, "scale": [0] * 3}
baseline = H.root_rows(p, 39)
selected = H.root_rows(p, 39, native_tail_profile=args.profile)
assert selected[0] == baseline[0]
assert selected[1][:-1] == baseline[1][:-1]
assert selected[1][-1] - baseline[1][-1] == 7
b, s = baseline[2], selected[2]
for key in ("root_apply_origin", "gather_row0_at", "tail_launch_after", "gather_period", "npos"):
    assert b[key] == s[key], key
for key in ("result_after", "emit_after_row0", "tail_latency"):
    assert s[key] - b[key] == 7, key
assert H.root_rows(p, 39) == baseline  # no ambient state leaked
mutants = 0
with tempfile.TemporaryDirectory() as td:
    for section, key, value in (("tail", "selected_result_latency", 496),
                                ("kernel", "SYS_LAT", 146), ("parameters", "NQ", 4)):
        doc = copy.deepcopy(json.loads(args.profile.read_text()))
        doc[section][key] = value
        path = Path(td) / "mutant.json"
        path.write_text(json.dumps(doc))
        try:
            load(path)
        except ValueError:
            mutants += 1
        else:
            raise AssertionError(f"missed {section}.{key} mutant")
print(json.dumps(dict(status="PASS", scope="compiler_source_contract_only", mutants_caught=mutants,
                     added_tail_core_cycles=7, default_tail_latency=b["tail_latency"],
                     selected_tail_latency=s["tail_latency"], launch=b["tail_launch_after"],
                     native_contract=s["native_tail_contract"])))
