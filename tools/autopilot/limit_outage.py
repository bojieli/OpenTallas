#!/usr/bin/env python3
"""limit_outage: LIMIT-GUARD-1116 (FABLE-FLOW-1113 #3), no LLM.  Run by cron on intel2 every 15 min:
  python3 -I tools/autopilot/limit_outage.py [--coord ~/coord]
Counts the distinct lanes that posted in COORD-REVIEW-QUEUE.md in the last 15 min.  Fewer than 3 for 2 samples in a row = LIMIT-OUTAGE:
it writes lanes/handoff/LIMIT-OUTAGE.md (every open pending action, every die hold without one) and keeps the wave launching: when the
last autopilot tick is older than 20 min it starts autopilot.service (the tick is the no-LLM runner of pending_actions.json).  Never edits config."""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

POST_RE = re.compile(r"^- (\d{4}-\d\d-\d\d \d\d:\d\d) \w+ (?:[A-Z-]+ )?\[([A-Za-z0-9_-]+)")
MIN_LANES = 3


def lanes_posting(lines, now, window_s=900):
    out = set()
    for ln in lines[-4000:]:
        m = POST_RE.match(ln)
        if not m:
            continue
        try:
            t = time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M"))
        except ValueError:
            continue
        if 0 <= now - t <= window_s:
            out.add(m.group(2))
    return out


def holds_without_action(cfg, actions):
    acted = {(s["delete_hold"].get("die"), s["delete_hold"].get("key")) for a in actions for s in a.get("do") or [] if "delete_hold" in s}
    out = []
    for die, d in (cfg.get("dies") or {}).items():
        for k in (d.get("hold_items") or {}):
            if (die, k) not in acted:
                out.append(f"{die}/{k}")
    return out


def run(coord, now=None, start=lambda: subprocess.run(["systemctl", "--user", "start", "--no-block", "autopilot.service"], timeout=60)):
    now = time.time() if now is None else now
    coord = Path(coord)
    q = (coord / "lanes/COORD-REVIEW-QUEUE.md").read_text(errors="replace").splitlines()
    n = len(lanes_posting(q, now))
    sp = coord / "autopilot/limit_outage_state.json"
    try:
        s = json.loads(sp.read_text())
    except (OSError, ValueError):
        s = {}
    s["low"] = s.get("low", 0) + 1 if n < MIN_LANES else 0
    outage = s["low"] >= 2
    msg = f"LIMIT-OUTAGE lanes posting in 15 min: {n} (< {MIN_LANES}) for {s['low']} samples" if outage else f"lanes posting in 15 min: {n}"
    if outage:
        try:
            cfg = json.loads((coord / "autopilot/kit_wave.json").read_text())
        except (OSError, ValueError):
            cfg = {}
        try:
            acts = json.loads((coord / "autopilot/pending_actions.json").read_text()).get("actions") or []
        except (OSError, ValueError):
            acts = []
        body = [f"# LIMIT-OUTAGE {time.strftime('%Y-%m-%d %H:%M', time.localtime(now))}", msg, "",
                "## open pending actions (the tick runs them without a lane)"] + [f"- {a.get('id')}: when {a.get('when')}" for a in acts] + \
               ["", "## die holds with no pending action (wait for a lane)"] + [f"- {h}" for h in holds_without_action(cfg, acts)]
        (coord / "lanes/handoff").mkdir(parents=True, exist_ok=True)
        (coord / "lanes/handoff/LIMIT-OUTAGE.md").write_text("\n".join(body) + "\n")
        log = coord / "autopilot/log.txt"
        age = now - log.stat().st_mtime if log.exists() else 1e9
        if age > 1200:
            start()
            msg += f"; autopilot log idle {int(age)} s: tick started"
    else:
        try:
            (coord / "lanes/handoff/LIMIT-OUTAGE.md").unlink()
        except OSError:
            pass
    sp.write_text(json.dumps(s))
    with open(coord / "autopilot/log.txt", "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S %Z', time.localtime(now))} LIMIT-GUARD: {msg}\n")
    return outage, msg


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--coord", default=str(Path.home() / "coord"))
    print(run(ap.parse_args().coord)[1])
