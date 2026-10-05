#!/usr/bin/env python3
"""Lightweight SSH terminal collection; never launches or restarts a build/run."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

WT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "terminal"
HOST = "ot-epyc1tb"
REMOTE = "/srv/opentallas/jobs/ampere-qwen-hbm-final-tp4-20261005"
NOTES = Path("/tmp/claude-review-20261003/codex_notes.txt")


def note(text):
    fd = os.open(NOTES, os.O_APPEND | os.O_WRONLY)
    os.write(fd, ("\n" + datetime.datetime.now(datetime.timezone.utc).isoformat()
                  + " AMPERE finalaf266 TP4 " + text + "\n").encode())
    os.close(fd)


def git(*args):
    return subprocess.check_output(["git", "-c", "gc.auto=0", *args], cwd=WT, text=True).strip()


while True:
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", HOST,
                        f"test -f {REMOTE}/supervisor.exit"], capture_output=True)
    if p.returncode == 0:
        break
    if p.returncode not in (1, 255):
        note(f"collection SSH refusal rc{p.returncode}; source job untouched")
        raise SystemExit(p.returncode)
    time.sleep(60)
if OUT.exists():
    raise SystemExit("Existing terminal collection is immutable")
OUT.mkdir()
# Numerical output is collected only after the original recipe has terminated.
subprocess.run(["scp", f"{HOST}:{REMOTE}/supervisor.exit", f"{HOST}:{REMOTE}/supervisor.log",
                f"{HOST}:{REMOTE}/build.log", str(OUT)], check=True)
for name in ("terminal.json", "build_identity.json"):
    subprocess.run(["scp", f"{HOST}:{REMOTE}/{name}", str(OUT)], capture_output=True)
(OUT / "build").mkdir()
subprocess.run(["scp", f"{HOST}:{REMOTE}/build/*.log", f"{HOST}:{REMOTE}/build/build_params.json",
                str(OUT / "build")], capture_output=True)
for name in ("L5", "L20", "head"):
    subprocess.run(["scp", "-r", f"{HOST}:{REMOTE}/{name}", str(OUT)], capture_output=True)
stages = {}
for name in ("L5", "L20", "head"):
    path = OUT / name / "token_result.json"
    if path.exists():
        r = json.loads(path.read_text())
        stages[name] = {k: r.get(k) for k in ("status", "total_cycles", "binary_sha256", "source_stable",
                                              "rtl_token", "rtl_logit_bits", "oracle_token", "oracle_logit_bits")}
        stages[name]["stage_cycles"] = r["stages"][name]["cycles"]
        stages[name]["design_point"] = r["design_point"]
        stages[name]["layer_x_checks"] = r["layer_x_checks"]
rc = int((OUT / "supervisor.exit").read_text())
good = (rc == 0 and len(stages) == 3 and all(r["status"] == "pass" and r["source_stable"]
        and r["design_point"]["tp"] == 4 for r in stages.values())
        and len({r["binary_sha256"] for r in stages.values()}) == 1)
summary = {"status": "pass" if good else "fail", "actual_supervisor_exit": rc,
           "stages": stages, "full_token_measured": False, "SS_FF_qualified": False,
           "claim_boundary": "Three final-source TP4 representative stage runs with retained gold; no full-token rate or physical admission"}
(OUT / "measured_stage_cycles.json").write_text(json.dumps(summary, indent=2) + "\n")
pins = {str(p.relative_to(OUT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(OUT.rglob("*")) if p.is_file()}
(OUT / "artifact_pins.json").write_text(json.dumps(pins, indent=2) + "\n")
git("add", "--", str(OUT.relative_to(WT)))
git("commit", "-m", "Collect once-only final-source TP4 L5 L20 HEAD cycles and exactness")
frozen = git("rev-parse", "HEAD")
for attempt in range(5):
    try:
        git("fetch", "origin")
        git("merge", "--no-edit", "origin/main")
        git("push", "origin", "HEAD:main")
        note(f"actual TERMINAL {summary['status'].upper()} rc{rc}; frozen{frozen} selfmerged/pushedmain{git('rev-parse', 'HEAD')}; "
             f"cycles { {n: r['stage_cycles'] for n, r in stages.items()} }; "
             f"raw/receipt {OUT}; no numerical repeat/fulltoken-rate/physical claim. Source/build retained for consumers.")
        break
    except subprocess.CalledProcessError as exc:
        if git("ls-files", "-u"):
            note(f"terminal collected frozen{frozen}; merge conflict needs parent intake, no automatic resolution; {OUT}")
            raise SystemExit(1)
        if attempt == 4:
            note(f"terminal collected frozen{frozen}; publish unavailable rc{exc.returncode}, parent intake {WT}/{OUT.relative_to(WT)}")
            raise SystemExit(1)
