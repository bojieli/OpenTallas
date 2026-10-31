#!/usr/bin/env python3
"""DIE-HBM-44 one-block (COORD 20:43 (6), option B): HBM SU exp0 (ot_hbm_su_static_pgslice_lg__lane_exp0_id) gets ONE
core clock pin `clk` at its existing plan centre clock entry (clock_entries.json, 12.8a), replacing the 19 clock-root
pins (clk_bank, clk_insert[0..3], clk_bank_macro[0..5], clk_lane[0..7]; one domain, fed by one merged tap). The type
wrapper fans clk out to the 19 internal roots (kit lane); one core_tree is built by the kit lane. Data pins, outline,
tap xy, entry island and latency targets are unchanged (asserted).  usage: exp0clk.py SRC_PLAN_DIR OUT_DIR"""
import json, sys, os, hashlib
from pathlib import Path
src, out = Path(sys.argv[1]), Path(sys.argv[2])
MOD = "ot_hbm_su_static_pgslice_lg__lane_exp0_id"
CLK = {"clk_bank"} | {f"clk_insert[{i}]" for i in range(4)} | {f"clk_bank_macro[{i}]" for i in range(6)} | {f"clk_lane[{i}]" for i in range(8)}
def dg(x): return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
p = json.loads((src / "die_plan.json").read_text()); ce = json.loads((src / "clock_entries.json").read_text())
rep = {"schema": "opentallas.die_hbm_44.exp0clk.v1", "base_sha256": hashlib.sha256((src / "die_plan.json").read_bytes()).hexdigest(),
       "module": MOD, "old_clock_bits": len(CLK), "new_clock_bits": 1, "data_cycle_delta": 0, "outline_delta_um": [0, 0],
       "clock_tree_rerun_required": True, "uses": []}
new_files = {}
for tn, t in p["partition_types"].items():
    for h in t.get("hard_cores", []):
        if h["module"] != MOD: continue
        e = ce[tn][h["inst"]]
        assert e["port"] is None and set(e["merged_clock_ports"]) == {"clk_bank", "clk_bank_macro", "clk_insert", "clk_lane"}
        old = json.loads((src / h["pins_file"]).read_text()); assert isinstance(old, list)
        clocks = [v for v in old if v["name"] in CLK]; data = [v for v in old if v["name"] not in CLK]
        assert {v["name"] for v in clocks} == CLK and not any(v["name"] == "clk" for v in data)
        assert not any(v["name"].startswith("clk") for v in data), [v["name"] for v in data if v["name"].startswith("clk")]
        x, y = e["xy_um"]
        clk = {"name": "clk", "layer": "M5", "x": round(x + 0.024, 3), "y": y}   # M5 track (0.048 pitch, 0.024 offset), as the q_b000 hc_bank centre clk pins
        isl = e["island_um"]; assert isl[0] < clk["x"] < isl[2] and isl[1] <= clk["y"] <= isl[3]
        new = data + [clk]
        name = str(Path(h["pins_file"]).with_name(Path(h["pins_file"]).stem + "__oneclk.json"))
        assert new_files.get(name, new) == new; new_files[name] = new
        rep["uses"].append({"type": tn, "inst": h["inst"], "old_pins_file": h["pins_file"], "pins_file": name, "clk": clk,
                            "entry_xy_um": e["xy_um"], "nonclock_bits": len(data), "nonclock_sha256": dg(data)})
        h["pins_file"] = name
        h["note"] = h.get("note", "") + " | DIE-HBM-44 (COORD 20:43 (6) option B): ONE core clock pin clk at the plan centre entry replaces the 19 clock roots; wrapper fans out, one core_tree (kit)"
        e["port"] = "clk"; e["merged_clock_ports"] = []
        e["source"] = e["source"] + " | DIE-HBM-44 option B: single core clock pin clk at the entry"
assert len(rep["uses"]) == 4, len(rep["uses"])
out.mkdir(parents=True); (out / "cores").mkdir()
for f in os.listdir(src):
    if f in ("die_plan.json", "clock_entries.json", "cores"): continue
    os.symlink(os.path.realpath(src / f), out / f)
for f in os.listdir(src / "cores"):
    os.symlink(os.path.realpath(src / "cores" / f), out / "cores" / f)
for name, x in new_files.items(): (out / name).write_text(json.dumps(x, indent=1) + "\n")
(out / "clock_entries.json").write_text(json.dumps(ce, indent=1) + "\n")
(out / "die_plan.json").write_text(json.dumps(p, indent=1) + "\n")
rep["plan_sha256"] = hashlib.sha256((out / "die_plan.json").read_bytes()).hexdigest()
rep["clock_entries_sha256"] = hashlib.sha256((out / "clock_entries.json").read_bytes()).hexdigest()
rep["pins_sha256"] = {n: hashlib.sha256((out / n).read_bytes()).hexdigest() for n in new_files}
(out / "exp0clk_report.json").write_text(json.dumps(rep, indent=1) + "\n")
print(json.dumps({k: rep[k] for k in ("plan_sha256", "clock_entries_sha256", "pins_sha256")}), len(rep["uses"]))
