#!/usr/bin/env python3
"""ROUTE-HOLD-PASS (DIE-HBM-97 11-10, COORD vecd-clkroot-r2): in-flow FF hold repair on ROUTED parasitics, one pass.

Why: the GRT-stage hold repair runs on GRT RC (hold_guard_grt.tcl, margin 0) and lands at ~0 there, but the routed RCX
moves it: vecd4ae v32e0 GRT ws -71.19 -> +0.01 (3,790 HB4), sign-off FF hold core-owned -98.94 ps on 3,250 reg2reg
endpoints.  This stage repairs on the routed RCX SPEF instead, inside the kit flow.

Opt-in per kit, decided BEFORE the build: the generator flag --route-hold-pass on writes
    export OT_ROUTE_HOLD_PASS = 1
    export OT_ROUTE_HOLD_TOOLS = <repo>/tools/die_plan
into config.mk; run_kit_hbm.sh calls `route_hold_pass.py run KIT SIGNOFF` after the kit's own sign-off (GOAL finish /
route).  The stage runs when the record's hold_ff FAILs on core-owned endpoints (eco_loop.core_hold: neither input-port
start nor output-port end); port-only hold is the parent's (NEEDS_PARENT) and is left alone.  It is ONE iteration of the
shared post-route repair (eco_loop.run_loop -> prd_mk.sh / prd_run.sh / prd_hook.tcl: repair_design, repair_timing -hold
on the routed RCX SPEF, legalise, incremental GRT, one detailed route, RCX, the kit's GOAL=post sign-off), with
max_iter 1, strict_one_pass (one physical dispatch, no recovery retry) and route_hold_form, which eco_loop honours only when
the kit SPEC declares the pass (freeze.json flow_defaults.route_hold_pass.on + config.mk; on/off for the whole build).
The pass record (on/off, before/after FF hold, core endpoints repaired, verdict, LEC) is written into the sign-off
records (key route_hold_pass); routed LEC after the pass; no ECO on top (eco_loop NOT_ELIGIBLE once it ran).  Repair TARGET = eco_loop.HOLD_MARGIN_PS (5 ps, the flow's exposed
target, COORD 11-09 KW-FIX-42); every GATE stays FF hold slack >= 0.  Result: KIT/route_hold_pass.json.
    route_hold_pass.py run KIT SIGNOFF.json [--mem 48] [--cpus 16] [--lec]
    route_hold_pass.py decide KIT SIGNOFF.json         (no P&R: prints the decision)
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import eco_loop  # noqa: E402

KEY = "OT_ROUTE_HOLD_PASS"


def enabled(kit):
    """the kit SPEC declares the pass (eco_loop.route_hold_declared: freeze.json flow_defaults.route_hold_pass.on and
    config.mk OT_ROUTE_HOLD_PASS = 1)"""
    return eco_loop.route_hold_declared(kit)


def hold_numbers(signoff):
    """{wns_ps, violators, core_wns_ps, core_n} of a sign-off record's FF hold (core = eco_loop.core_hold split)"""
    try:
        h = (json.loads(Path(signoff).read_text()).get("checks") or {}).get("hold_ff") or {}
    except (OSError, ValueError):
        return None
    split = eco_loop.core_hold(signoff)
    return dict(verdict=h.get("verdict"), wns_ps=h.get("wns_ps"), violators=h.get("violators"),
                core_wns_ps=split[0] if split else None, core_n=split[1] if split else None)


def record(signoff, block):
    """the pass record goes INTO the sign-off record (key route_hold_pass); the rest of the record is untouched"""
    try:
        p = Path(signoff)
        d = json.loads(p.read_text())
        d["route_hold_pass"] = block
        p.write_text(json.dumps(d, indent=1, default=str) + "\n")
    except (OSError, ValueError):
        pass


def decide(kit, signoff):
    """-> (run: bool, reason)"""
    if not enabled(kit):
        return False, "ROUTE-HOLD-PASS not declared in the kit spec (off for this build)"
    try:
        rec = json.loads(Path(signoff).read_text())
    except (OSError, ValueError) as e:
        return False, f"no readable sign-off record ({e})"
    hold = (rec.get("checks") or {}).get("hold_ff") or {}
    if hold.get("verdict") != "FAIL":
        return False, f"hold_ff {hold.get('verdict')}: nothing to repair"
    if eco_loop.port_only_hold(signoff):
        return False, "hold is port-only: the parent's (NEEDS_PARENT), no core repair"
    split = eco_loop.core_hold(signoff)
    if split is not None and split[1] == 0:
        return False, "no core-owned hold endpoints: the parent's (NEEDS_PARENT)"
    what = f"core-owned {split[1]} endpoint(s) at {split[0]} ps" if split else f"{hold.get('violators')} endpoint(s) (no split)"
    return True, "hold_ff FAIL, " + what


def run(kit, signoff, mem=48, cpus=16, lec=False, run_loop=eco_loop.run_loop, run_lec=None):
    kit = Path(kit).resolve()
    go, why = decide(kit, signoff)
    before = hold_numbers(signoff)
    out = dict(schema="opentallas.route_hold_pass.v1", kit=str(kit), signoff=str(signoff), on=enabled(kit), run=go,
               reason=why, passes=1 if go else 0, hold_margin_ps=eco_loop.HOLD_MARGIN_PS, before=before)
    print(("ROUTE_HOLD_PASS run: " if go else "ROUTE_HOLD_PASS skip: ") + why, flush=True)
    if go:
        runner = kit / "run_kit_hbm.sh"
        res = run_loop(kit, signoff, root=kit / "route_hold_pass", runner=str(runner) if runner.is_file() else None,
                       max_iter=1, hold_margin=eco_loop.HOLD_MARGIN_PS, mem=mem, cpus=cpus,
                       strict_one_pass=True, route_hold_form=True)
        its = res.get("iterations") or []
        after_so = (its[0].get("signoff") if its else None) or (res.get("best") or {}).get("signoff")
        after = hold_numbers(after_so) if after_so else None
        rep = None
        if before and after and before.get("core_n") is not None and after.get("core_n") is not None:
            rep = int(before["core_n"]) - int(after["core_n"])
        out.update(verdict=res.get("verdict"), reason_loop=res.get("reason"), root=res.get("root"),
                   after_signoff=after_so, after=after, core_endpoints_repaired=rep)
        if res.get("verdict") == "PASS" and lec:
            ok = (run_lec or eco_loop.run_lec)(str(kit), res, mem, cpus, None)
            out["lec"] = (res.get("lec") or {}).get("verdict") if ok else "LEC_FAIL"
            if not ok:
                out["verdict"] = "LEC_FAIL"
        if after_so:
            record(after_so, {k: out.get(k) for k in ("on", "run", "passes", "hold_margin_ps", "before", "after",
                                                      "core_endpoints_repaired", "verdict", "lec", "signoff")})
    record(signoff, {k: out.get(k) for k in ("on", "run", "reason", "passes", "hold_margin_ps", "before")} |
           {"after_signoff": out.get("after_signoff"), "verdict": out.get("verdict", "SKIP")})
    (kit / "route_hold_pass.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    print("ROUTE_HOLD_PASS " + str(out.get("verdict", "SKIP")), flush=True)
    return 0 if (not go or out.get("verdict") == "PASS") else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("run", "decide"):
        p = sub.add_parser(n)
        p.add_argument("kit")
        p.add_argument("signoff")
        if n == "run":
            p.add_argument("--mem", type=int, default=48)
            p.add_argument("--cpus", type=int, default=16)
            p.add_argument("--lec", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "decide":
        go, why = decide(a.kit, a.signoff)
        print(("RUN " if go else "SKIP ") + why)
        return 0
    return run(a.kit, a.signoff, a.mem, a.cpus, a.lec)


if __name__ == "__main__":
    sys.exit(main())
