#!/usr/bin/env python3
"""Collect the remote QWEN-HBM-POWER outputs (ot-epyc1tb:/srv/opentallas-scratch/claude/qwen-hbm-power) into this
record directory: stages.json, activity/*.json, ports.json, power_<corner>.json, runs/<stage>/ (token_result, plan,
token.log STAGE/HBMSTAT/PASS lines).  Runs ON the remote host:  python3 collect.py <remote root> <out dir>."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

R, OUT = Path(sys.argv[1]), Path(sys.argv[2])
STAGES = ("L0", "L20", "head")
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "activity").mkdir(exist_ok=True)
stages = {}
for st in STAGES:
    run = R / "runs" / st
    tr = json.loads((run / "token_result.json").read_text())
    log = (run / "token.log").read_text()
    m = re.search(rf"STAGE {st} done cycles=(\d+) .*? me_busy=(\d+)/(\d+)", log)
    total = int(re.search(r"TOTAL (\d+)", (run / "plan.txt").read_text()).group(1))
    stages[st] = dict(cycles=int(m.group(1)), edges=int(m.group(2)), stream_words=total, status=tr["status"],
                      layer_x_mismatches={k: v["mismatches"] for k, v in tr.get("layer_x_checks", {}).items()},
                      rtl_token=tr.get("rtl_token"), oracle_token=tr.get("oracle_token"),
                      design_point=tr["design_point"], window_words=tr["memory_system"]["window_words"])
    d = OUT / "runs" / st
    d.mkdir(parents=True, exist_ok=True)
    for f in ("token_result.json", "plan.txt", "stages.txt"):
        shutil.copy(run / f, d / f)
    (d / "token.log").write_text("".join(l + "\n" for l in log.splitlines()
                                         if re.match(r"(STAGE|HBMSTAT|QWEN_HBMACC|RT_TILE|stream:|models|images)", l)))
    for a in sorted((R / "act").glob(f"{st}_t*/activity.json")):
        shutil.copy(a, OUT / "activity" / f"{a.parent.name}.json")
(OUT / "stages.json").write_text(json.dumps(stages, indent=1) + "\n")
acts = sorted(str(p) for p in (R / "act").glob("*_t*/activity.json"))
subprocess.run([sys.executable, str(R / "src/tools/qwen_hbm_tile_power.py"), "ports", "--act", *acts,
                "--out", str(OUT / "ports.json")], check=True)
for c in ("TT", "SS", "FF"):
    merged = {"corner": c, "sessions": {}, "values": {}}
    for st in STAGES:
        p = json.loads((R / "power" / f"{st}_{c}.json").read_text())
        merged["sessions"][st] = dict(results_dir=p["results_dir"], annotation_report=p["annotation_report"][:3],
                                      seconds=p["values"].get("session.seconds"))
        merged["values"].update({k: v for k, v in p["values"].items() if k != "session.seconds"})
    (OUT / f"power_{c}.json").write_text(json.dumps(merged, indent=1) + "\n")
print("collected", OUT)
