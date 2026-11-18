#!/usr/bin/env python3
"""publish_apply.py -- LATENCY-R 11-18 (COORD ruling 11-18, OWNER "remove plan validations, build all types directly from the latest plan").

Measured 11-17 (lanes/LATENCY-1117.md): a plan event spent 1.5-3 h between "bind done" and "first kit": serial PRE/G0/R8/cohort/CB16 checks, a 13-92 min
publish gate (static then dry gen), a separate apply step that waited on a person, gate-label misses, then a tick.  This tool is the one step a lane runs
the moment its tree is PUBLISHED:

  apply     optimistic atomic apply (apply_reviewed_tree_marker optimistic=True: publish gate, source guard and smoke are ADVISORY, no pilot hold, the
            event joins gate_events_extra in the same write), commit through coord-commit.sh, then the publish gate is started in the background as a
            REPORT (its record lists advisory findings; it never blocks), and one post names the warnings.  The next wave pass launches every type.
  bind-fail strict bind / LATCHECK (still running in parallel, the only blocking plan checks) failed: hold ONLY the types it names (explicit --types,
            or the plan item names found in --log), released by result:<owner>:<id>.  Running rows of held types are cancelled by the wave (kit_wave
            hold_records with cancel_running, WAVE-FLOW-R2).

    publish_apply.py apply --candidate JSON --expect-source OLD_TREE --expect-event OLD_EVENT --lane LANE [--coord ~/coord] [--no-gate]
    publish_apply.py bind-fail --die DIE --lane LANE --id ID (--types t1,t2 | --log FILE) [--reason TEXT] [--coord ~/coord] [--dry]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import apply_reviewed_tree_marker as A  # noqa: E402
import hold_records as HR  # noqa: E402


def post(C, lane, text, run=subprocess.run):
    return run(["bash", str(Path(C) / "bin/post.sh"), lane, text], capture_output=True, text=True, timeout=600)


def gate_argv(C, cand_path, tree, event):
    """the advisory publish gate after the apply: the projection re-applies the SAME tree onto the live config, so it expects the new source/event"""
    return [sys.executable, "-I", str(HERE / "publish_gate.py"), "run", "--candidate", str(cand_path), "--expect-source", tree,
            "--expect-event", str(event), "--coord", str(C), "--commit"]


def cmd_apply(a, run=subprocess.run, apply_fn=None, commit_fn=None):
    C = Path(a.coord)
    obj = json.loads(Path(a.candidate).read_text())
    obj["optimistic"] = True
    obj["_path"] = a.candidate
    t0 = time.time()
    res = (apply_fn or A.apply_marker)(C, obj, a.expect_source, a.expect_event, pilot_item=a.pilot_item, optimistic=True)
    res["commit"] = (commit_fn or A.commit_apply)(C, res)
    res["apply_s"] = round(time.time() - t0, 1)
    gate = "off"
    if not a.no_gate:
        # the gate's projection must see the candidate as optimistic too (guard/smoke advisory); written next to the receipt
        gc = Path(res["receipt"]).with_suffix(".gate_candidate.json")
        gc.write_text(json.dumps(dict({k: v for k, v in obj.items() if k != "_path"}, optimistic=True), indent=1))
        unit = "pubgate-%s-%d" % (res["applied"], int(time.time()))
        r = run(["systemd-run", "--user", "--unit", unit, "--collect", "--quiet", "--nice=10", *gate_argv(C, gc, (obj.get("marker") or obj)["tree"], res.get("event"))],
                capture_output=True, text=True, timeout=120)
        gate = unit if r.returncode == 0 else "not started (rc %d: %s)" % (r.returncode, (r.stderr or r.stdout)[-160:])
    res["advisory_gate"] = gate
    w = res.get("warnings") or []
    post(C, a.lane, f"APPLIED-OPTIMISTIC [{a.lane} -> COORD; cc WAVE-FLOW-R2] {res['applied']} event {res.get('event')} tree {res.get('source')}: every type launches on the "
                    f"next wave pass (no pilot); apply {res['apply_s']} s; advisory gate {gate}; gen_hosts {','.join(res.get('gen_hosts') or [])}; "
                    f"{len(w)} advisory warning(s){': ' + ' | '.join(w)[:900] if w else ''}. Strict bind + LATCHECK stay blocking: on a failure run "
                    f"publish_apply.py bind-fail (holds only the named types).", run=run)
    print(json.dumps(res))
    return 0


def item_names(d):
    """every item name the die's current plan lists (hold_event_items of its plan sha, else the union of all lists)"""
    hei = d.get("hold_event_items") or {}
    items = hei.get(d.get("plan_sha256")) or [i for v in hei.values() for i in v]
    return sorted(set(items))


def types_from_log(text, items):
    """plan item names that appear as whole words in a bind/LATCHECK failure log, longest first (a__b before a)"""
    found = []
    for it in sorted(items, key=len, reverse=True):
        if re.search(r"(?<![A-Za-z0-9_])" + re.escape(it) + r"(?![A-Za-z0-9_])", text):
            if not any(it in f for f in found):
                found.append(it)
    return sorted(found)


def bind_fail_record(d, types, lane, ident, reason):
    return {"id": f"bindfail-{ident}", "plan_sha": d.get("plan_sha256"), "items": list(types), "owner": lane, "carry": True, "cancel_running": True,
            "reason": f"LATENCY-R optimistic launch: strict bind/LATCHECK failed on these types only ({reason})"[:900],
            "release": [f"result:{lane}:{ident}"]}


def cmd_bind_fail(a, run=subprocess.run):
    C = Path(a.coord)
    cfg = json.loads((C / "autopilot/kit_wave.json").read_text())
    d = cfg["dies"][a.die]
    items = item_names(d)
    types = [t for t in (a.types or "").split(",") if t] or types_from_log(Path(a.log).read_text(errors="replace") if a.log else "", items)
    if not types:
        print("BIND-FAIL: no plan type named in the failure; nothing held (hold the die by hand if the failure is die-wide)")
        return 2
    rec = bind_fail_record(d, types, a.lane, a.id, a.reason or (a.log or "explicit types"))
    probe = json.loads(json.dumps(cfg))
    HR.add_record(probe, a.die, dict(rec))          # validation only: unknown item / lane / term -> ValueError, nothing written
    patch = [{"op": "add", "path": f"/dies/{a.die}/hold_records/-" if d.get("hold_records") else f"/dies/{a.die}/hold_records",
              "value": rec if d.get("hold_records") else [rec]}]
    if a.dry:
        print(json.dumps(patch, indent=1))
        return 0
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(patch, f)
    r = run([sys.executable, "-I", str(HERE / "kit_wave_edit.py"), "--message", f"{a.lane}: bind-fail hold {rec['id']} ({len(types)} types)", "--patch-file", f.name],
            capture_output=True, text=True, timeout=600)
    os.unlink(f.name)
    if r.returncode:
        print((r.stdout + r.stderr)[-600:])
        return 1
    post(C, a.lane, f"BIND-FAIL-HOLD [{a.lane} -> COORD; cc WAVE-FLOW-R2] {a.die}: held {len(types)} type(s) named by the strict bind/LATCHECK failure, every other "
                    f"type keeps building: {', '.join(types)[:900]}; release result:{a.lane}:{a.id}", run=run)
    print(json.dumps(rec))
    return 0


def main(argv=None):
    P = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = P.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("apply")
    p.add_argument("--candidate", required=True)
    p.add_argument("--expect-source", required=True)
    p.add_argument("--expect-event", required=True)
    p.add_argument("--lane", required=True)
    p.add_argument("--pilot-item")
    p.add_argument("--coord", default=os.path.expanduser("~/coord"))
    p.add_argument("--no-gate", action="store_true", help="do not start the advisory publish gate")
    b = sp.add_parser("bind-fail")
    b.add_argument("--die", required=True)
    b.add_argument("--lane", required=True)
    b.add_argument("--id", required=True)
    b.add_argument("--types", default="")
    b.add_argument("--log")
    b.add_argument("--reason", default="")
    b.add_argument("--coord", default=os.path.expanduser("~/coord"))
    b.add_argument("--dry", action="store_true")
    a = P.parse_args(argv)
    return cmd_apply(a) if a.cmd == "apply" else cmd_bind_fail(a)


if __name__ == "__main__":
    sys.exit(main())
