#!/usr/bin/env python3
"""Continue a reviewed kit through its existing runner, sign-off and routed LEC.

Runs inside the same ot-run allocation as the physical runner. Diagnostic CTS/GRT
goals remain diagnostics. Existing runner corner/hold policy takes precedence.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def load(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def continue_kit(kit, runner, goal, mem, threads, run=subprocess.call, preflight=None, proof_only=False):
    kit = Path(kit).resolve()
    started = time.time()
    prior = {str(p): (p.stat().st_mtime_ns, p.stat().st_size)
             for p in kit.glob("signoff*/signoff.json")}
    preflight = Path(preflight) if preflight else kit / "kit_preflight.py"
    if not preflight.is_file() and preflight != kit / "kit_preflight.py":
        print("KIT_PREFLIGHT FAIL: staged source tool missing", flush=True)
        return 3
    if preflight.is_file():
        rc = run([sys.executable, str(preflight), str(kit), "--out",
                  str(kit / ("preflight_autopilot_" + str(time.time_ns()) + ".json"))])
        if rc:
            print("KIT_PREFLIGHT FAIL: autopilot stopped before physical runner", flush=True)
            return rc
    rc = 0 if proof_only else run(["bash", runner, str(kit), goal, str(mem), str(threads)])
    if goal in ("cts", "grt"):
        return rc
    receipt = {"started": started, "runner_exit": rc, "goal": goal,
               "verdict": "INCOMPLETE", "proof_only": proof_only, "mem_gb": mem}
    out = kit / ("autopilot_chain_" + str(time.time_ns()) + ".json")

    def done(code, verdict, reason):
        receipt.update(verdict=verdict, reason=reason, finished=time.time())
        out.write_text(json.dumps(receipt, indent=1) + "\n")
        return code

    records = [p for p in kit.glob("signoff*/signoff.json")
               if proof_only or prior.get(str(p)) != (p.stat().st_mtime_ns, p.stat().st_size)]
    # signoff.py returns 1 for local-PASS-needs-parent. It is a valid
    # provisional result, so prove the route while preserving WAIT-PARENT.
    pending_parent = (rc == 1 and records and
                      load(max(records, key=lambda p: p.stat().st_mtime)).get("verdict") == "LOCAL_PASS_NEEDS_PARENT")
    if rc and not pending_parent:
        return done(rc, "RUNNER_FAIL", "physical runner did not complete")
    if proof_only and not records:
        return done(3, "SIGNOFF_MISSING", "proof-only requires an existing physical signoff record")
    if not records:
        # Recover the historical route-only runner gap without routing again.
        # Only an actual final ODB+SPEF is sufficient for per-corner sign-off.
        bases = [p.parent for p in kit.glob("run/results/asap7/*/base/6_final.odb")
                 if (p.parent / "6_final.spef").is_file()]
        if len(bases) != 1 or not (kit / "signoff.py").is_file():
            return done(3, "SIGNOFF_MISSING", "no unique final ODB/SPEF and staged signoff tool")
        so = kit / ("signoff_autopilot_" + str(time.time_ns()))
        code = run([sys.executable, str(kit / "signoff.py"), "run", "--base", str(bases[0]),
                    "--kit", str(kit), "--out", str(so)])
        records = [so / "signoff.json"]
        if code and not records[0].is_file():
            return done(code, "SIGNOFF_MISSING", "signoff tool failed without a record")
    so = max(records, key=lambda p: p.stat().st_mtime)
    physical = load(so)
    receipt["signoff"] = str(so)
    if physical.get("verdict") not in ("SIGNED", "LOCAL_PASS_NEEDS_PARENT"):
        return done(1, "NOT_SIGNED", "physical signoff did not pass")
    base = Path((physical.get("inputs") or {}).get("base", ""))
    netlist = base / "6_final.v"
    if not netlist.is_file() or not (kit / "lec.py").is_file():
        return done(3, "LEC_MISSING", "routed 6_final.v and staged lec.py required")
    proof = kit / ("lec_routed_autopilot_" + str(time.time_ns()))
    code = run([sys.executable, str(kit / "lec.py"), str(kit), "--netlist", str(netlist),
                "--out", str(proof), "--mem", str(mem), "--jobs", str(threads)])
    result = load(proof / "lec.json")
    receipt.update(netlist=str(netlist), lec=str(proof / "lec.json"),
                   lec_verdict=result.get("verdict"), lec_exit=code)
    if code in (137, -9) or "out of memory" in str(result.get("reason", "")).lower():
        return done(code or 137, "LEC_OOM", f"routed proof stopped in {mem} GB; route kept; re-admit --proof-only at measured memory")
    if code or result.get("verdict") != "EQUIVALENT":
        return done(code or 1, "LEC_FAIL", "routed LEC must be EQUIVALENT with exit 0")
    return done(0, "PASS", "physical signoff and routed LEC complete")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--proof-only", action="store_true", help="resume proof of an existing signed route, never reroute")
    ap.add_argument("--preflight", help="separately staged shared tool, including its source helpers")
    ap.add_argument("runner")
    ap.add_argument("kit")
    ap.add_argument("goal")
    ap.add_argument("mem", type=int)
    ap.add_argument("threads", type=int)
    a = ap.parse_args()
    return continue_kit(a.kit, a.runner, a.goal, a.mem, a.threads, preflight=a.preflight, proof_only=a.proof_only)


if __name__ == "__main__":
    sys.exit(main())
