#!/usr/bin/env python3
"""Hourly failure scan (owner 2026-10-08). Lists failed jobs (NEEDS_RTL / NEEDS_HUMAN / INVALID / NEEDS_BUDGET) that were
not handled in an earlier run. FLOORPLAN_MARGIN is actionable floorplan work. A job is DISCARDED (marked processed, not worked) when its block already has a CLOSED job
(superseded). It is SKIPPED this run when its block has a live successor (QUEUED/SYNC/READY/RUNNING/ECO), and comes back
if that successor fails. Everything else is NEW work, written to new_<ts>.json grouped by kind (timing|flow) and target
(qwen|s81|hbm|other). `--commit FILE` marks the jobs in FILE as processed after the agents have been launched."""
import json, glob, pathlib, sys, time, re, os
D = pathlib.Path(os.environ.get("CL_TAKEOVER", "/home/ubuntu/claude-takeover-20261007")) / "failtrig"
D.mkdir(parents=True, exist_ok=True)
J = pathlib.Path(os.environ.get("CL_STATE", str(pathlib.Path.home()/".local/state/closure_loop"))) / "jobs"
P = D/"processed.json"; done = set(json.loads(P.read_text())) if P.exists() else set()
if len(sys.argv) > 2 and sys.argv[1] == "--commit":
    done |= set(json.load(open(sys.argv[2])).get("keys") or json.load(open(sys.argv[2]))["names"]); P.write_text(json.dumps(sorted(done))); print("committed", len(done)); sys.exit()
# stuckscan 2026-10-08: EARLY_FAIL_* = a route stopped by the loop's early-fail gates (hopeless setup/hold/congestion/DRC):
# redesign work, reported even with a live sibling; diagnosis + worst-path classes in failtrig/stuck/<job>.json
EARLY = {"EARLY_FAIL_SETUP", "EARLY_FAIL_HOLD", "EARLY_FAIL_CONGESTION", "EARLY_FAIL_DRC"}
FAIL = {"NEEDS_RTL", "NEEDS_HUMAN", "INVALID", "NEEDS_BUDGET", "FLOORPLAN_MARGIN"} | EARLY; LIVE = {"QUEUED", "SYNC", "READY", "RUNNING", "ECO", "MIGRATING"}
jobs = []
for f in J.glob("*.json"):
    try: jobs.append(json.loads(f.read_text()))
    except Exception: pass
blk = lambda j: (j.get("spec") or {}).get("block") or re.sub(r"[-_][0-9a-f]{9}.*$", "", j["name"])
# 2026-10-08: a CLOSED job that was later revoked (revoked_closures.json, or the option-B link-budget revocation) does
# not supersede failures -- dsfd_svcio_q's orph2 re-routes were silently discarded against its revoked closure
_rv = set()
try: _rv |= set(json.load(open(D.parent/"revoked_closures.json")))
except Exception: pass
_rvb = set()
for _p in sorted(glob.glob(str(pathlib.Path.home()/"OpenTallas/results/closure_loop/option_b_status_*/status.json")))[-1:]:
    try: _rvb = {b["block"] for b in (json.load(open(_p)).get("revoked_previously_closed") or {}).get("blocks", [])}
    except Exception: pass
closed = {blk(j) for j in jobs if j.get("status") == "CLOSED" and j["name"] not in _rv
          and not (blk(j) in _rvb and (j.get("events") or [""])[-1][:16] < "2026-10-07T20:45")}
live = {blk(j) for j in jobs if j.get("status") in LIVE}
# drive-1143: CRITICAL-path blocks / fallbacks are always reported, even with a live sibling (bfh_halfphl ODB-0372 was
# hidden 10:27 behind the live full-rate bfh_* routes on the same block).
CRIT_BLOCKS = {"ot_s81_bf_native"}; CRIT_NAME = re.compile(r"^(bfh?_halfphl|hbm_attn_tile)")
crit = lambda j: blk(j) in CRIT_BLOCKS or bool(CRIT_NAME.match(j["name"])) or j.get("status") in EARLY
def target(n):
    n = n.lower()
    if n.startswith(("qfd", "qwen", "core_", "cdc_", "slab", "code_pair", "stream4", "embed")): return "qwen"
    if n.startswith(("hbm", "hfd", "ha2", "w2-", "smh")): return "hbm"
    if n.startswith(("s81", "dsfd", "dshead", "dsrom", "bf_", "window", "wcol", "wsrc", "pq", "qelem", "dsfh")): return "s81"
    return "other"
new = {}; discard = []
# 2026-10-08: a job is processed per FAILURE (name@time of its failing event), not per name -- a job retried after
# triage that failed again (attn tile r23h/r23hq 07:50/08:27) was hidden for 2 h.  Legacy name-only entries still
# count unless the job was retried after them (a retry event precedes the current failure).
def key(j): return j["name"] + "@" + (j.get("events") or [""])[-1][:19]
def handled(j):
    if key(j) in done: return True
    if j["name"] not in done: return False
    return not any(("human retry" in e or "ioref" in e or "re-queued" in e) for e in (j.get("events") or [])[:-1])
for j in jobs:
    n = j["name"]
    if j.get("status") not in FAIL or handled(j): continue
    ev = (j.get("events") or [""])[-1]
    if "released" in ev and "superseded" in ev: discard.append(key(j)); continue
    b = blk(j)
    if b in closed: discard.append(key(j)); continue
    if b in live and not crit(j): continue
    kind = "timing" if j.get("status") in ({"NEEDS_RTL", "NEEDS_BUDGET"} | EARLY) else "flow"
    if j.get("status") == "FLOORPLAN_MARGIN": kind = "floorplan"
    if j.get("status") == "EARLY_FAIL_HOLD" and "old flow" in (j.get("reason") or ""): kind = "flow"  # re-route under the HM/stall guard
    new.setdefault(f"{kind}:{target(n)}", []).append({"job": n, "key": key(j), "block": b, "host": j.get("host"), "why": ev[26:220]})
if discard: done |= set(discard); P.write_text(json.dumps(sorted(done)))
ts = time.strftime("%Y%m%d-%H%M"); out = D/f"new_{ts}.json"
names = [x["job"] for v in new.values() for x in v]
out.write_text(json.dumps({"groups": new, "names": names, "keys": [x["key"] for v in new.values() for x in v]}, indent=1))
print(f"discarded(superseded)={len(discard)} new={len(names)} file={out}")
for k, v in sorted(new.items()): print(f"  {k}: {len(v)}")
