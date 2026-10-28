#!/usr/bin/env python3
"""HBM-CORES-REBAL-2 die-local plan delta: side_rest / side_softplus clk_side[2:0] (native aliases of one clock: the
plan tap '<inst>.clk_side' already replaces the 3 bits; SDC create_clock on [get_ports clk_side]) -> ONE scalar input
pin clk_side at the clk_side[1] site.  Non-clock pins byte-identical.  usage: side_oneclk.py PLANDIR(copy, edited)"""
import json, sys, hashlib
from pathlib import Path
d = Path(sys.argv[1]); p = json.loads((d / "die_plan.json").read_text())
MODS = ("ot_hbm_su_static_pgslice_lg__side_rest", "ot_hbm_su_static_pgslice_lg__side_softplus")
dig = lambda x: hashlib.sha256(json.dumps(x, sort_keys=True).encode()).hexdigest()
rep, done = [], {}
for tn, t in p["partition_types"].items():
    for h in t.get("hard_cores", []):
        if h["module"] not in MODS:
            continue
        old = h["pins_file"]
        new = old[:-5] + "__oneclk.json"
        if old not in done:
            pins = json.loads((d / old).read_text())
            ck = [v for v in pins if v["name"].startswith("clk_side[")]
            assert sorted(v["name"] for v in ck) == ["clk_side[0]", "clk_side[1]", "clk_side[2]"], ck
            data = [v for v in pins if not v["name"].startswith("clk_side[")]
            assert not any(v["name"] == "clk_side" for v in data)
            c = dict(next(v for v in ck if v["name"] == "clk_side[1]")); c["name"] = "clk_side"
            out = []
            for v in pins:                      # keep order: scalar replaces the first clock bit position
                if v["name"].startswith("clk_side["):
                    if v["name"] == "clk_side[0]":
                        out.append(c)
                    continue
                out.append(v)
            assert [v for v in out if v["name"] != "clk_side"] == data
            (d / new).write_text(json.dumps(out, indent=1) + "\n")
            done[old] = new
            rep.append(dict(module=h["module"], old=old, new=new, clock_bits_old=3, clock_bits_new=1, clk_site=c,
                            nonclock=len(data), nonclock_sha256=dig(data)))
        h["pins_file"] = done[old]
        h["note"] = h.get("note", "") + " | HBM-CORES-REBAL-2: clk_side[2:0] aliases -> scalar clk_side (oneclk pins)"
(d / "die_plan.json").write_text(json.dumps(p, indent=1) + "\n")
(d / "side_oneclk_report.json").write_text(json.dumps(rep, indent=1) + "\n")
print(json.dumps([(r["module"], r["nonclock"]) for r in rep]))
