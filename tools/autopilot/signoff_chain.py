#!/usr/bin/env python3
"""Continue a reviewed kit through its existing runner, sign-off and routed LEC.

Runs inside the same ot-run allocation as the physical runner. Diagnostic CTS/GRT
goals remain diagnostics. Existing runner corner/hold policy takes precedence.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def load(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


# gates a SIGNED record must carry PASS (TT setup / FF hold with one mode per corner, DRV slew/cap, clock insertion vs
# the bound band, DRC, antenna, PG census); a missing gate is NOT RUN, never PASS
REQUIRED_GATES = ("setup_tt", "hold_ff", "drv", "clock", "drc", "antenna", "pg")


def signoff_gates(physical):
    checks = physical.get("checks") or {}
    out = {}
    for k in REQUIRED_GATES:
        v = checks.get(k)
        out[k] = (v.get("verdict") or "NOT RUN") if isinstance(v, dict) else str(v) if v else "NOT RUN"
    corners = physical.get("corners") or {}
    for c in ("tt", "ff"):
        if corners and not (corners.get(c) or {}).get("done"):
            out["corner_" + c] = "NOT RUN"
    return out


def proof_stale(proof, base):
    """'' when lec.json and lec.log are both newer than 6_final.odb and 6_final.v, else the reason"""
    try:
        ref = max((base / n).stat().st_mtime for n in ("6_final.odb", "6_final.v") if (base / n).exists())
    except ValueError:
        return "routed 6_final.odb/.v missing for the proof mtime check"
    for n in ("lec.json", "lec.log"):
        p = proof / n
        if not p.is_file():
            return f"routed LEC {n} missing"
        if p.stat().st_mtime <= ref:
            return f"routed LEC {n} is not newer than 6_final (stale proof)"
    return ""


def continue_kit(kit, runner, goal, mem, threads, run=subprocess.call, preflight=None, proof_only=False, lec=None):
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
    gates = signoff_gates(physical)
    receipt["gates"] = gates
    bad = sorted(k for k, v in gates.items() if v != "PASS")
    if bad:
        # an older frozen kit signoff.py can say SIGNED without running a gate (AUTOPILOT-SIGNOFF-2)
        return done(1, "NOT_SIGNED", "signoff gates not PASS: " + ", ".join(f"{k}={gates[k]}" for k in bad))
    base = Path((physical.get("inputs") or {}).get("base", ""))
    netlist = base / "6_final.v"
    tool = Path(lec) if lec else kit / "lec.py"
    receipt["lec_tool"] = str(tool)
    if not netlist.is_file() or not tool.is_file():
        return done(3, "LEC_MISSING", "routed 6_final.v and the staged current lec.py required")
    proof = kit / ("lec_routed_autopilot_" + str(time.time_ns()))
    env = dict(os.environ, OT_LEC_SUPERSET_VEC="1")
    code = run([sys.executable, str(tool), str(kit), "--netlist", str(netlist),
                "--out", str(proof), "--mem", str(mem), "--jobs", str(threads)], env=env)
    result = load(proof / "lec.json")
    sv = result.get("superset_vec") or {}
    receipt.update(netlist=str(netlist), lec=str(proof / "lec.json"),
                   lec_verdict=result.get("verdict"), lec_exit=code, lec_all_shown=sv.get("all_shown"))
    if code in (137, -9) or "out of memory" in str(result.get("reason", "")).lower():
        return done(code or 137, "LEC_OOM", f"routed proof stopped in {mem} GB; route kept; re-admit --proof-only at measured memory")
    if code or result.get("verdict") != "EQUIVALENT":
        return done(code or 1, "LEC_FAIL", "routed LEC must be EQUIVALENT with exit 0")
    if sv.get("all_shown") is not True:
        return done(1, "LEC_FAIL", "routed LEC superset check: all_shown must be true (OT_LEC_SUPERSET_VEC=1)")
    stale = proof_stale(proof, base)
    if stale:
        # stale-log lesson 10-27: a proof older than the routed netlist it names is not a proof of this route
        return done(1, "LEC_FAIL", stale)
    receipt["gates"]["routed_lec"] = "PASS"
    return done(0, "PASS", "physical signoff and routed LEC complete")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--proof-only", action="store_true", help="resume proof of an existing signed route, never reroute")
    ap.add_argument("--preflight", help="separately staged shared tool, including its source helpers")
    ap.add_argument("--lec", help="separately staged current main lec.py (routed proof); default KIT/lec.py")
    ap.add_argument("runner")
    ap.add_argument("kit")
    ap.add_argument("goal")
    ap.add_argument("mem", type=int)
    ap.add_argument("threads", type=int)
    a = ap.parse_args()
    return continue_kit(a.kit, a.runner, a.goal, a.mem, a.threads, preflight=a.preflight, proof_only=a.proof_only, lec=a.lec)


if __name__ == "__main__":
    sys.exit(main())
