#!/usr/bin/env python3
"""launch_gates.py -- FP-CONVERGE-S81 (FABLE-RC-S81): LAUNCH-SCOPE and FT-SITE-LEGAL lines for kit_preflight (report-only).

  lines(kit, plan=None, environ=None) -> [str]   WARN lines; plan = die plan json (default $OT_LAUNCH_PLAN)
  blocking(environ)                              True only with OT_LAUNCH_GATES_BLOCK=1 (kit_preflight then fails on any WARN line)

The kit facts come from the environment the wave sets: OT_KIT_TYPE (default: kit dir name), OT_KIT_GOAL, OT_WAVE_PLAN_SHA,
OT_EVENT_TYPES (comma list, event touched set), OT_KIT_SIGNED / OT_KIT_OPEN_FUNCTIONAL / OT_KIT_FP_CLEAN (1/0).  A missing fact
is skipped, so the gate never invents a violation.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def blocking(environ=None):
    return (os.environ if environ is None else environ).get("OT_LAUNCH_GATES_BLOCK") == "1"


def kit_facts(kit, plan_sha=None, environ=None):
    env = os.environ if environ is None else environ
    tt = env.get("OT_EVENT_TYPES")
    d = dict(type=env.get("OT_KIT_TYPE") or Path(kit).name, goal=env.get("OT_KIT_GOAL") or None,
             bound_plan_sha=plan_sha, wave_plan_sha=env.get("OT_WAVE_PLAN_SHA") or None,
             touched_types=[x for x in tt.split(",") if x] if tt else None)
    for k, e in (("signed", "OT_KIT_SIGNED"), ("open_functional_row", "OT_KIT_OPEN_FUNCTIONAL")):
        if env.get(e) in ("0", "1"):
            d[k] = env[e] == "1"
    if env.get("OT_KIT_FP_CLEAN") in ("0", "1"):
        d["fp_clean"] = env["OT_KIT_FP_CLEAN"] == "1"
    return d


def bits_blocking(environ=None):
    """True only with OT_BITS_OVER_CYCLE_BLOCK=1: a BITS-OVER-CYCLE line then fails the kit (FP-CONVERGE-S81, FABLE-RC-S81 19:19)"""
    return (os.environ if environ is None else environ).get("OT_BITS_OVER_CYCLE_BLOCK") == "1"


def lines(kit, plan=None, environ=None):
    env = os.environ if environ is None else environ
    sys.path.insert(0, str(HERE))
    try:
        import adv_fpconv2 as F2
    except ImportError:
        return ["SKIP LAUNCH-GATES no adv_fpconv2 beside launch_gates"]
    finally:
        try:
            sys.path.remove(str(HERE))
        except ValueError:
            pass
    plan = plan or env.get("OT_LAUNCH_PLAN")
    sha = hashlib.sha256(Path(plan).read_bytes()).hexdigest() if plan and Path(plan).is_file() else None
    facts = kit_facts(kit, sha, env)
    out = list(F2.launch_scope(facts))
    raw = json.loads(Path(plan).read_text()) if sha else None
    if raw:
        out += F2.legal_gate(raw, {facts["type"]})
    # dsdv_slice route goals stay behind bits_over_cycle = 0 (placed scan of the kit / $OT_PLACED_SCAN_DIRS, else the plan); guarded import
    sys.path.insert(0, str(HERE))
    try:
        import adv_bitscycle as BC
        out += BC.gate_lines(facts["type"], facts.get("goal"), raw, kit=kit, environ=env)
    except ImportError:
        pass
    finally:
        try:
            sys.path.remove(str(HERE))
        except ValueError:
            pass
    return out
