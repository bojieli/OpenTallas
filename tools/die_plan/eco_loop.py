#!/usr/bin/env python3
"""eco_loop.py -- late-stage ECO loop on a ROUTED core / type DB (KW-ECO-1, OWNER 2026-11-01 ~20:0x: "for cores and
types, enable iteration and fixing on late stages").

A routed kit whose sign-off fails only on TIMING / DRV / a small DRC count is repaired on its own routed DB instead of
being rebuilt from gen.  Every step is an existing, proven shared tool; this file only sequences them and decides when
to stop.  Sign-off and LEC are unchanged (no gate, corner, derate or margin is touched), so a PASS here is an ordinary
sign-off of a new routed DB.

OWNER 11-07 05:3x: "real near misses should still use late stage fixes, but do not use multiple iterations of late stage
fixes and do not use it to fix large misses".  So MAX_ITER = 1, --max-iter above 1 is refused, and a base record beyond
the near-miss numbers (near_miss()) stops before any P&R as verdict NOT_NEAR_MISS unless --owner-override.  A form that
does not sign off after its one iteration goes to GEOMETRY + REDESIGN, pin cycles first.

The iteration, from the kit's routed DB:
  1. prd_mk.sh SRC D <m|b|t><hold margin> SO   (tools/die_plan/post_route_drv; two-mode kit: m<N>; single-mode kit:
     t<N> (TT setup + DRV, no hold) when TT fails, then b<N> (FF hold + DRV) from it when FF fails; OT_PRD_FROM=route when the DB has no DRC,
     else grt = one full detailed route from the pre-DRT GRT DB, the FLOW-SHARED-10 form that clears small DRC counts;
     final = route from the kit's signed 6_final.odb, retried once when the routed seed does not match the SPEF)
  2. prd_run.sh D CPUS MEM 1 with OT_PRD_POST=0: the ECO hook prd_hook.tcl on the routed RCX SPEF (= measured arrivals)
       repair_design (slew/cap) -> repair_timing -setup (two-mode kits) -> repair_timing -hold, hold margin 5 ps (repair target only)
       (OWNER 11-02; was 12.19 measured arrivals + 10 ps) -> detailed_placement (legalises only what moved) ->
       global_route -start_incremental/-end_incremental -> detailed_route (route-keep: only the dirty nets are ripped)
     -> clk_freeze_check.sh (clock wires frozen) -> RCX + slew/cap count -> do-finish
  3. the kit's own sign-off on D with the kit's ORIGINAL config.mk restored (the ECO overrides only steer the route):
     the kit runner's GOAL=post when it has one (KV / HBM), else do-generate_abstract + signoff.py run exactly as
     run_kit.sh calls it (--run-dir D/run --kit D --corners tt,ff --image IMAGE).
Stop rules: sign-off SIGNED (or LOCAL_PASS_NEEDS_PARENT with local SIGNED) -> PASS; no improvement vs the previous
result (negative-WNS sum gain < 1 ps and neither the DRV nor the DRC count falling) -> EXHAUSTED; an iteration that
cannot route / finish / sign off -> stop with the best result so far; MAX_ITER (1) reached -> EXHAUSTED.

The post-route LEC is the caller's (signoff_chain.py runs its usual routed LEC on the PASS netlist; the CLI runs the
kit's lec.py with --lec).  Result: ROOT/eco_loop.json {schema opentallas.eco_loop.v1, kind eco, verdict, base routed
DB, iterations [commands, metrics, wall], best, flow sha}.

    eco_loop.py run --kit K [--runner R] [--out ROOT] [--hold-margin 5] [--mem 48] [--cpus 8] [--lec] [--owner-override]
    eco_loop.py check SIGNOFF.json        eligibility + near-miss decision of a sign-off record
Heavy: run through ot-run (--mem = honest peak, the ECO session + DRT + sign-off STA), never on localhost.
    The ECO docker cap is max(--mem, ceil(1.5 x the kit's measured OpenROAD peak)) (ECO-OOM-1); a step killed for memory
    (OOM / kill text in its log) ends the loop as verdict ECO_OOM ("late-ECO OOM ... at <cap> GB"), re-run at a larger --mem.
    A step stopped from outside (rc 137/143/130/129 or -9/-15/-2/-1 with no OOM line: docker stop, lane kill) ends it as
    verdict ABORTED: not a design result, retry as is (KW-FIX-24).
"""
import argparse
import hashlib
import math
import re
import tempfile
import json
import os
import shlex
import shutil
import subprocess
import sys
import threading
from contextvars import ContextVar
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRD = HERE / "post_route_drv"
SCHEMA = "opentallas.eco_loop.v1"
MAX_ITER = 1                  # OWNER 11-07 05:3x: one late-stage iteration per routed form; was 3
HOLD_MARGIN_PS = 5            # COORD 11-09 04:4x (KW-FIX-42): hold REPAIR TARGET 5 ps for every wave ECO (ECOs aimed at 0 ps landed at -0.0x..-1.4 ps under sign-off uncertainty + calibrated RC); the GATE is unchanged: FF hold slack >= 0 (OWNER 11-02 FLOW-22, 25 ps FF hold uncertainty stays); was 0 (11-02), 10 (12.19)
MIN_WNS_GAIN_PS = 1.0         # stop rule: < 1 ps gain and DRV/DRC not falling = no improvement
DRC_SMALL = 50                # = autopilot NEAR_DRC_MAX: above it the route is a ROUTING problem, not an ECO
ECO_FAILS = {"setup_tt", "hold_ff", "drv", "drc", "fanout"}
# COORD 11-07 05:37 working numbers for a near miss; beyond them = large miss, NOT_NEAR_MISS (--owner-override only)
NEAR_WNS_PS = 30.0            # setup / hold no worse than this
NEAR_ENDPOINTS = 100          # on no more than this many endpoints
NEAR_SLEW_NETS = 20           # slew violations by NET (COORD 05:41); a record with pin counts only: advisory
NEAR_DRC = 50                 # DRC under this
IMAGE = os.environ.get("OT_ORFS_IMAGE", "openroad/orfs:asap7lock")
# ECO machinery staged from the current tools (prd_mk.sh copies these from SO/tools/die_plan)
ECO_TOOL_FILES = ("clk_freeze.tcl", "clk_dump_db.tcl", "clk_geom_diff.py", "clk_freeze_check.sh",
                  "kit_modes_eco.tcl", "pg_connect.tcl")
FLOW_FILES = ("post_route_drv/prd_mk.sh", "post_route_drv/prd_run.sh", "post_route_drv/prd_hook.tcl",
              "post_route_drv/prd_route_keep.tcl", "post_route_drv/eco_grt_pre.tcl", "post_route_drv/eco_drt_pre.tcl", "post_route_drv/prd_targeted.tcl", "post_route_drv/prd_autofo.tcl",
              "post_route_drv/prd_count.tcl", "post_route_drv/post_grt_chain.py", "post_route_drv/prd_seed.py",
              "post_route_drv/prd_spef_insts.py", "eco_loop.py") + ECO_TOOL_FILES
POST_RUNNERS = ("run_kit_hbm.sh", "run_kit_kv.sh", "run_kit.sh")
# ECO-OOM-1 (DIE-S81-48 11-02, VEs autopilot 246986099dc1): the late ECO inherited the kit runner's ot-run memory (24 GB)
# as its docker cap, but the ECO session holds the routed DB + the routed SPEF in TWO scenes + repair + DRT on top of what
# the kit's own DRT needed (22.3 GB peak) -> docker SIGKILL rc 137 inside the first read_spef, reported as the generic
# "route / clock-freeze check / finish failed".  Now: (1) the ECO docker cap is floored at ECO_MEM_FACTOR x the kit's
# measured OpenROAD peak, (2) rc 137 / -9 or kill evidence in the step log = status ECO_OOM naming the cap.
ECO_MEM_FACTOR = 1.5
# KW-FIX-24 11-06 (S81-ENGRR-B5): rc 137 alone is not OOM evidence -- docker stop / a lane's kill ends a step 137 or 143
# too.  Same convention as autopilot classify ("infra-stopped": exit 137/143 with no OOM line in the run logs): OOM only
# with a memory line in the step log; an external-stop rc without one is ABORTED (infra, retryable, never a design
# verdict).  SIGSEGV (139 / -11) and every other rc stay tool / design errors as before.
STOP_RCS = {129, 130, 137, 143, -1, -2, -9, -15}
OOM_TEXT = re.compile(r"\bKilled\b|out of memory|OOMKilled|Cannot allocate memory|std::bad_alloc|\bError 137\b", re.I)
PEAK_RES = (re.compile(r"peak = ([0-9.]+) \(MB\)"), 1.0 / 1024,
            re.compile(r"Peak memory: ([0-9.]+)KB"), 1.0 / (1024 * 1024),
            re.compile(r"MEM: ([0-9.]+) MB peak"), 1.0 / 1024)


def measured_peak_gb(kit):
    """max OpenROAD peak memory (GB) in the kit's own logs (run/logs/**/*.log + KIT/*.log); 0.0 when none"""
    kit = Path(kit)
    logs = list(kit.glob("*.log")) + list((kit / "run" / "logs").rglob("*.log"))
    pats = [(PEAK_RES[i], PEAK_RES[i + 1]) for i in range(0, len(PEAK_RES), 2)]
    peak = 0.0
    for p in logs:
        try:
            t = p.read_text(errors="replace")
        except OSError:
            continue
        for rx, scale in pats:
            for m in rx.finditer(t):
                try:
                    peak = max(peak, float(m.group(1)) * scale)
                except ValueError:
                    pass
    return round(peak, 2)


def eco_mem(kit, mem):
    """-> (docker cap GB for every ECO step, measured kit peak GB): max(mem, ceil(ECO_MEM_FACTOR x measured peak))"""
    peak = measured_peak_gb(kit)
    return max(int(mem), int(math.ceil(ECO_MEM_FACTOR * peak))), peak


def oom_evidence(rc, *logs):
    """True when a step was killed for memory: kill / OOM text in its log tail.  rc 137 / -9 alone is not evidence
    (docker stop ends a step the same way, KW-FIX-24)"""
    for p in logs:
        try:
            t = Path(p).read_text(errors="replace")[-20000:]
        except OSError:
            continue
        if OOM_TEXT.search(t):
            return True
    return False


def load(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError, TypeError):
        return {}


# ------------------------------------------------------------------------------------------------ record reading
def measured_vclk(ref):
    """sign-off IO frame: 'applied mode pin_flop_mean clock vclk latency_ps 332.27 ...' -> 332.27, else None"""
    m = re.match(r"applied mode pin_flop_mean .*\blatency_ps ([0-9.]+)", ref or "")
    return float(m.group(1)) if m else None


def eco_vclk_frame(pass_dir, variant, prev):
    """Single-mode pass: repair against the IO frame sign-off measured, not the plan bound.  The session bound
    OT_VCLK_FF (hd_ctl_e FF 342) while sign-off rebinds pin_flop_mean (332.27), so repair_timing saw no hold violation
    at FF -4.17.  Steers this pass only (kit_modes_eco.tcl); eco_loop restores the kit config.mk after the pass.
    OT_ECO_MEASURED_VCLK=0 = old frame.  -> ps written, or None."""
    if os.environ.get("OT_ECO_MEASURED_VCLK", "1") == "0" or variant[0] not in "tb":
        return None
    ps = (prev or {}).get("vclk_tt" if variant[0] == "t" else "vclk_ff")
    cfg = Path(pass_dir) / "config.mk"
    if ps is None or not cfg.is_file():
        return None
    with open(cfg, "a") as f:
        f.write(f"\nexport OT_ECO_VCLK_PS = {ps:.6f}\n")
    return ps


_LATE_HOLD_SCOPE = ContextVar("late_eco_hold_scope", default=None)


def hold_scope():
    """Explicit environment override, else this late-ECO call's scoped default."""
    if "OT_HOLD_REPAIR_SCOPE" in os.environ:
        return (os.environ.get("OT_HOLD_REPAIR_SCOPE") or "").strip().lower()
    return _LATE_HOLD_SCOPE.get() or ""


def late_hold_scope(kit):
    """Late ECO defaults to core-owned paths: exclude input starts AND output ends.

    Existing reg2reg implements that exact endpoint ownership, including internal
    macro paths. Explicit env/config scopes (even blank/all) retain their meaning.
    This default never changes pre-GRT repair or the declared ROUTE-HOLD form.
    """
    if "OT_HOLD_REPAIR_SCOPE" in os.environ:
        return hold_scope()
    scope = None
    try:
        for line in Path(kit, "config.mk").read_text(errors="replace").splitlines():
            m = _HOLD_SCOPE_MK_RX.match(line)
            if m:
                scope = m.group(1).strip().lower()
    except OSError:
        pass
    return "reg2reg" if scope is None else scope


def nonport_score(signoff_path):
    """KW-FIX-32 11-07 (COORD 21:4x (3), DIE-KV-91 M5 e1): (wns_ps, endpoints) the loop scores hold on when the repair
    scope is nonport: the FF census non-port split.  A clean census with no non-port violator scores (0.0, 0) (signoff
    prints STD_MIN_NONPORT only when there is one).  None when the split cannot be read: the whole number is scored."""
    try:
        s = json.loads((Path(signoff_path).parent / "ff" / "corner.json").read_text()).get("std_min_start")
    except (OSError, ValueError, AttributeError, TypeError):
        return None
    if not isinstance(s, dict) or s.get("err") != 0 or s.get("trunc") != 0:
        return None
    if s.get("nonport_n") is None:
        return (0.0, 0) if s.get("other") == 0 and s.get("reg") == 0 else None
    n = int(s["nonport_n"])
    if n == 0:
        return 0.0, 0
    return (None, n) if s.get("nonport_wns") is None else (float(s["nonport_wns"]), n)


def metrics(rec, signoff_path=None):
    """sign-off record -> {verdict, signed, tt, ff, drv, drc, fails}; with OT_HOLD_REPAIR_SCOPE=nonport and a readable
    FF census next to signoff_path also ff_np / ff_np_n (the non-port hold the ECO repairs), which the stop rule and the
    best pick score instead of ff. The late-ECO reg2reg scope scores the same fields on core_hold and also records
    ff_core / ff_core_n; standalone metrics without a scoped run retain the whole-number behavior."""
    c = rec.get("checks") or {}
    by = {}
    for k, v in ((c.get("drv") or {}).get("by_corner") or {}).items():
        if isinstance(v, dict):
            by[str(k).lower()] = sum(float(x or 0) for x in v.values())
    drv = sum(by.values())
    fails = sorted(k for k, v in c.items() if isinstance(v, dict) and v.get("verdict") == "FAIL")
    verdict = rec.get("verdict")
    signed = verdict == "SIGNED" or (verdict == "LOCAL_PASS_NEEDS_PARENT" and rec.get("local_verdict") == "SIGNED")
    out = dict(verdict=verdict, signed=bool(signed), tt=(c.get("setup_tt") or {}).get("wns_ps"),
                ff=(c.get("hold_ff") or {}).get("wns_ps"), drv=int(drv), drc=int((c.get("drc") or {}).get("count") or 0),
                drv_tt=int(by.get("tt", 0)), drv_ff=int(by.get("ff", 0)), fails=fails,
                vclk_tt=measured_vclk((c.get("setup_tt") or {}).get("vclk_reference")),
                vclk_ff=measured_vclk((c.get("hold_ff") or {}).get("ff_vclk_reference")))
    if signoff_path and hold_scope() in ("reg2reg", "nonport"):
        scope = hold_scope()
        split = core_hold(signoff_path) if scope == "reg2reg" else nonport_score(signoff_path)
        if split and split[0] is not None:
            out["ff_np"], out["ff_np_n"] = split[:2]   # scoring compatibility with explicit nonport callers
            out["hold_score_scope"] = "core" if scope == "reg2reg" else "non-port"
            if scope == "reg2reg":
                out["hold_score_exact"] = bool(split[2])
                if split[2]:
                    out["ff_core"], out["ff_core_n"] = split[:2]
                else:
                    out["hold_score_scope"] = "core-bound"
                    out["ff_core_bound"], out["ff_core_n_bound"] = split[:2]
    return out


def passes(kit, prev, hm):
    """ECO passes of one iteration.  Two-mode kit (OT_HOLD_MM=1): one m<N> pass (TT setup + BC hold in one session).
    Single-mode kit: the session holds one corner (kit_modes_eco.tcl), so TT setup / TT DRV is a t<N> pass and FF hold /
    FF DRV a b<N> pass started from it; each runs only when its corner fails (neither: b<N>, the DRC / fanout form)."""
    if hold_mm(kit):
        return ["m" + str(hm)]
    tt, ff = prev.get("tt"), prev.get("ff")
    need_t = (tt is not None and tt < 0) or prev.get("drv_tt", 0) > 0
    need_b = (ff is not None and ff < 0) or prev.get("drv_ff", 0) > 0 or prev.get("drc", 0) > 0
    out = (["t" + str(hm)] if need_t else []) + (["b" + str(hm)] if need_b or not need_t else [])
    return out


def eligible(rec, signoff_path=None):
    """(ok, reason): a NOT SIGNED routed sign-off whose only FAILs are TIMING / DRV / small DRC"""
    if not rec:
        return False, "no sign-off record"
    m = metrics(rec)
    if m["signed"]:
        return False, "already signed"
    if not m["fails"]:
        return False, "no FAIL gate (NOT RUN / parent-only reasons are not an ECO case)"
    other = sorted(set(m["fails"]) - ECO_FAILS)
    if other:
        return False, "structural gate FAIL " + ",".join(other) + " (not an ECO class)"
    if m["drc"] > DRC_SMALL:
        return False, f"DRC {m['drc']} > {DRC_SMALL} (ROUTING class)"
    if signoff_path and m["fails"] == ["hold_ff"]:
        split = core_hold(signoff_path)
        if port_only_hold(signoff_path) or (split is not None and split[1] == 0):
            return False, "hold is parent-port only (input starts/output ends): no core-owned ECO work"
    return True, "ECO class: " + ",".join(m["fails"])


def port_only_hold(signoff_path):
    """signoff.port_only_hold on the record's FF corner: every hold violator starts at an input port (parent's)"""
    import importlib.util
    try:
        corner = json.loads((Path(signoff_path).parent / "ff" / "corner.json").read_text())
        spec = importlib.util.spec_from_file_location("ot_signoff_for_eco", HERE / "signoff.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return bool(mod.port_only_hold(corner))
    except (OSError, ValueError, ImportError, AttributeError):
        return False


def nonport_hold(signoff_path):
    """DIE-KV-88 11-07 (COORD ruling): (wns_ps, endpoints) of the hold violators not started at an input port, from the
    FF corner's std_min_start, the source signoff.port_only_hold reads.  None when the split cannot be read: no census,
    a census with an error or truncated, or an older record without the non-port fields."""
    try:
        s = json.loads((Path(signoff_path).parent / "ff" / "corner.json").read_text()).get("std_min_start") or {}
    except (OSError, ValueError, AttributeError):
        return None
    w, n = s.get("nonport_wns"), s.get("nonport_n")
    if w is None or n is None or s.get("err") != 0 or s.get("trunc") != 0:
        return None
    return w, n


def core_hold(signoff_path):
    """KW-FIX-36 11-08 (COORD R4): (wns_ps, endpoints, exact) of the FF hold violators neither started at an input port
    nor ending at an output port, the two sets sign-off assigns to the parent (signoff.port_only_hold, census oport).
    None when the split cannot be read, as nonport_hold.  A record older than core_n has one bound only: endpoints =
    min(nonport_n, other + reg); wns stays the unsplit non-port wns (it may be set by an output endpoint), so the
    alignment gives an older record no easier number than the census it holds; re-sign for the exact split."""
    try:
        s = json.loads((Path(signoff_path).parent / "ff" / "corner.json").read_text()).get("std_min_start") or {}
    except (OSError, ValueError, AttributeError):
        return None
    if s.get("err") != 0 or s.get("trunc") != 0:
        return None
    if s.get("core_n") is not None and s.get("core_wns") is not None:
        return float(s["core_wns"]), int(s["core_n"]), True
    split = nonport_hold(signoff_path)
    if split is None:
        return None
    w, n = split
    if not (s.get("oport") or 0):
        return w, int(n), True                  # no output-port endpoints: the non-port census is already exact
    return w, int(min(n, (s.get("other") or 0) + (s.get("reg") or 0))), False


def near_miss(rec, signoff_path=None):
    """-> (near, [what is beyond the numbers], [advisories]).  Only FAIL gates count: port-only hold is PASS in a current
    record, and an older record's FF census gives the same answer; it goes to the parent, not to an ECO.  A mixed record
    scores hold on the endpoints sign-off leaves to the core (KW-FIX-36 R4: without input-port starts and output-port
    endpoints, core_hold); with no readable split it scores the whole number.  Same numbers as ever: one iteration,
    NEAR_WNS_PS, NEAR_ENDPOINTS of the remaining endpoints."""
    c = rec.get("checks") or {}
    far, warn = [], []
    for key, name in (("setup_tt", "setup"), ("hold_ff", "hold")):
        g = c.get(key) or {}
        if g.get("verdict") != "FAIL":
            continue
        if key == "hold_ff" and signoff_path and port_only_hold(signoff_path):
            warn.append("hold is port-only: the parent's, no ECO for it")
            continue
        w, n = g.get("wns_ps"), g.get("violators") or 0
        split = core_hold(signoff_path) if key == "hold_ff" and signoff_path else None
        if split:
            w, n, exact = split
            warn.append(f"hold scored on core-owned only: {int(n)} endpoint(s) at {w} ps; the rest start at input ports or end "
                        f"at output ports, the parent's" + ("" if exact else " (older census: count bounded, wns unsplit; re-sign for the exact split)"))
        if w is not None and w < -NEAR_WNS_PS:
            far.append(f"{name} WNS {w} ps worse than -{NEAR_WNS_PS:g}")
        if n > NEAR_ENDPOINTS:
            far.append(f"{name} {int(n)} endpoints > {NEAR_ENDPOINTS}")
    by = (c.get("drv") or {}).get("by_corner") or {}
    corners = [v for v in by.values() if isinstance(v, dict)]
    nets = [v["slew_nets"] for v in corners if v.get("slew_nets") is not None]
    pins = max([float(v.get("slew") or 0) for v in corners] or [0])
    if nets:
        if max(nets) > NEAR_SLEW_NETS:
            far.append(f"{int(max(nets))} slew nets > {NEAR_SLEW_NETS}")
    elif pins > NEAR_SLEW_NETS:
        warn.append(f"{int(pins)} slew pins, nets not in the record: count the nets (near miss = at most {NEAR_SLEW_NETS}, one family, local cause)")
    drc = int((c.get("drc") or {}).get("count") or 0)
    if drc >= NEAR_DRC:
        far.append(f"DRC {drc} not under {NEAR_DRC}")
    return not far, far, warn


def neg_sum(m, nonport=False):
    ff = m.get("ff_np") if nonport else m.get("ff")
    return sum(min(float(w), 0.0) for w in (m.get("tt"), ff) if w is not None)


def _np(a, b):
    """both sides carry the non-port hold score (nonport scope, readable census on both): compare on it"""
    return "ff_np" in a and "ff_np" in b


def improved(prev, cur):
    """stop rule: True when cur is better than prev by >= 1 ps negative-WNS sum, or fewer DRV, or fewer DRC; nonport
    scope (both scored): hold is the non-port WNS, and fewer non-port hold endpoints also count"""
    np_ = _np(prev, cur)
    gain = neg_sum(cur, np_) - neg_sum(prev, np_)
    fewer = np_ and cur["ff_np_n"] < prev["ff_np_n"]
    return gain >= MIN_WNS_GAIN_PS or fewer or cur["drv"] < prev["drv"] or cur["drc"] < prev["drc"]


def better(a, b):
    """is metrics a strictly better than b (signed first, then neg-WNS sum, DRV, DRC)"""
    np_ = _np(a, b)
    ka = (a["signed"], neg_sum(a, np_), -a["drv"], -a["drc"])
    kb = (b["signed"], neg_sum(b, np_), -b["drv"], -b["drc"])
    return ka > kb


def newest_signoff(d, since=0.0):
    recs = [p for p in Path(d).glob("signoff*/signoff.json") if p.stat().st_mtime >= since]
    return max(recs, key=lambda p: p.stat().st_mtime) if recs else None


def flow_sha(tools=HERE):
    h = hashlib.sha256()
    for rel in FLOW_FILES:
        p = Path(tools) / rel
        h.update(rel.encode() + b"\0")
        h.update(p.read_bytes() if p.is_file() else b"MISSING")
    out = dict(tools_sha256=h.hexdigest())
    try:
        r = subprocess.run(["git", "-C", str(tools), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            out["git"] = r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    b = load(Path(tools).parent / "BUNDLE.json")
    if b.get("sha256"):
        out["admission_bundle"] = b["sha256"]
    return out


# ------------------------------------------------------------------------------------------------ staging
def hold_mm(kit):
    mm = "0"
    try:
        for line in Path(kit, "config.mk").read_text().splitlines():
            for pre in ("override export OT_HOLD_MM = ", "export OT_HOLD_MM = "):
                if line.startswith(pre):
                    mm = line[len(pre):].strip()
    except OSError:
        pass
    return mm == "1"


# KW-FIX-24 11-06 (COORD 11:14 class tool gap, S81-IDX-B4 eco_vbc): signoff.py / prd_mk.sh / tap_balance.tcl resolve
# shared Tcl from physical/common_flow BESIDE tools/die_plan (clock_family.tcl; macro_cts_cluster.tcl for two-mode
# kits' orfs_hold_mm.tcl).  The staged SO tree had only tools/die_plan, so its own signoff.py bundle (prd_mk.sh, every
# pass) found nothing there and stopped with 'incomplete tool bundle'.  stage_so now stages physical/common_flow next to
# so/tools/die_plan: the whole directory when the tool source has it, else the bundle's common_flow members (admission
# bundle copy beside signoff.py, or git HEAD of a sparse checkout).
COMMON_FLOW_BUNDLE = ("clock_family.tcl", "macro_cts_cluster.tcl")
COMMON_FLOW_REQUIRED = ("clock_family.tcl",)


def _copy_w(src, dst):
    """copy2 into a staged tree that stays writable (DIE-KV-93 11-08 FLOW class): a read-only tag tools tree (0444)
    used to stage 0444 copies, so a later kit file of the same name (kit .tcl override) or a re-copy hit EACCES.
    The destination is replaced, never written through, and the staged copy gets u+w; the source is untouched."""
    dst = Path(dst)
    if dst.is_symlink() or dst.is_file():
        dst.unlink()
    shutil.copy2(src, dst)
    os.chmod(dst, os.stat(dst).st_mode | 0o200)
    return dst


def stage_common_flow(so, tools=HERE):
    """so/physical/common_flow from the checkout of `tools`; returns the staged dir.  Raises ValueError when a required
    member (clock_family.tcl) has no source, naming the fix (stage physical/common_flow next to tools/die_plan)."""
    tools = Path(tools)
    out = Path(so) / "physical" / "common_flow"
    out.mkdir(parents=True, exist_ok=True)
    src_dir = tools.parents[1] / "physical" / "common_flow"
    if src_dir.is_dir():
        shutil.copytree(src_dir, out, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"), copy_function=_copy_w)
    for name in COMMON_FLOW_BUNDLE:
        if (out / name).is_file():
            continue
        src = tools / name                      # admission bundle: copy beside signoff.py
        if not src.is_file():
            try:                                # sparse checkout: the bytes from git HEAD (common_flow_src.py)
                sys.path.insert(0, str(tools))
                from common_flow_src import common_flow_file
                src = common_flow_file(name, tools.parents[1])
            except (ImportError, ValueError):
                pass
            finally:
                if sys.path and sys.path[0] == str(tools):
                    sys.path.pop(0)
        if Path(src).is_file():
            _copy_w(src, out / name)
    missing = [n for n in COMMON_FLOW_REQUIRED if not (out / n).is_file()]
    if missing:
        raise ValueError(f"eco_loop: incomplete tool bundle: physical/common_flow/{', '.join(missing)} not found for "
                         f"tools {tools} (stage physical/common_flow next to tools/die_plan)")
    return out


def stage_so(kit, root, tools=HERE):
    """Stage one selected tool cohort, retaining kit-local hooks and inputs.

    Shared Python tools must come from `tools`: old kits can contain a partially
    refreshed signoff.py whose sdc_lint.py no longer implements its API.  Preserve
    unique kit scripts and geometry/runner overrides, then bundle the selected
    sign-off family together (including its Tcl helpers), with physical/common_flow staged beside tools/die_plan
    (stage_common_flow, KW-FIX-24).
    """
    so = Path(root) / "so"
    dp = so / "tools" / "die_plan"
    dp.mkdir(parents=True, exist_ok=True)
    for p in Path(tools).iterdir():
        if p.is_file():
            _copy_w(p, dp / p.name)
    for p in Path(kit).iterdir():
        if p.is_file() and p.suffix in (".py", ".tcl", ".sh") and p.stat().st_size < (8 << 20):
            if p.suffix == ".py" and (Path(tools) / p.name).is_file():
                continue
            _copy_w(p, dp / p.name)
    stage_common_flow(so, tools)
    subprocess.run([sys.executable, "-I", str(Path(tools) / "signoff.py"), "bundle", str(dp)],
                   check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    for n in ECO_TOOL_FILES:
        _copy_w(Path(tools) / n, dp / n)
    scope = hold_mm_scope_needed(kit)
    srcs = (Path(kit), Path(tools).parent)
    if scope and not hold_mm_supports(Path(kit) / "orfs_hold_mm.tcl", scope):
        srcs = (Path(tools).parent,)       # KW-FIX-44: a kit copy older than the scope never reaches the ECO
    for n in HOLD_MM_FILES:
        for src in (s / n for s in srcs):
            if src.is_file():
                _copy_w(src, so / "tools" / n)
                break
    if scope and not hold_mm_supports(so / "tools" / "orfs_hold_mm.tcl", scope):
        raise ValueError(f"eco_loop: OT_HOLD_REPAIR_SCOPE={scope} on a two-mode kit needs an orfs_hold_mm.tcl that "
                         f"supports it; neither the kit {kit} nor the tools {Path(tools).parent} has one "
                         f"(stage tools/orfs_hold_mm.{{py,tcl}} from main)")
    return so


# KW-FIX-44 11-09 (HBM-COLLECT-1/N4-C 10:54, both n4_local_vA ECOs; DIE-HEAD-91 04:10 tx_eco1/1b): a two-mode kit whose
# orfs_hold_mm.tcl predates the hold-repair scope it now asks for (kit config.mk or env OT_HOLD_REPAIR_SCOPE=nonport) made
# prd_hook.tcl refuse ("OT_HOLD_SCOPE nonport requires matching orfs_hold_mm.tcl") after the full ECO route, so no repair
# ran and the one ECO iteration was spent.  prd_mk.sh keeps the pass dir's (= the kit's) copy, and stage_so preferred it
# too; FLOW_FILES refreshed post_route_drv/* only.  Now the pair is staged from the current tools whenever the kit copy
# lacks the scope, in the SO tree (stage_so) and in every pass dir after prd_mk.sh (refresh_hold_mm), and the loop stops
# with ERROR before any prd_run when no copy supports it.  A kit without a scope, or whose copy supports it: unchanged.
HOLD_MM_FILES = ("orfs_hold_mm.py", "orfs_hold_mm.tcl")
HOLD_SCOPES = ("reg2reg", "nonport")
_HOLD_MODES_RX = re.compile(r"^\s*set\s+::ot_hold_scope_supported_modes\s+\{([^}]*)\}", re.M)
_HOLD_SCOPE_MK_RX = re.compile(r"^\s*(?:override\s+)?export\s+OT_HOLD_REPAIR_SCOPE\s*[:?]?=\s*(\S*)\s*$")


def kit_hold_scope(kit):
    """the ECO's OT_HOLD_REPAIR_SCOPE: the environment (hold_scope()) else the last export in the kit config.mk"""
    s = hold_scope()
    if s:
        return s
    try:
        for line in Path(kit, "config.mk").read_text(errors="replace").splitlines():
            m = _HOLD_SCOPE_MK_RX.match(line)
            if m:
                s = m.group(1).strip().lower()
    except OSError:
        pass
    return s


def hold_mm_scope_needed(kit):
    """the scope the kit's orfs_hold_mm.tcl must support in this ECO: '' unless two-mode with a reg2reg / nonport scope"""
    s = kit_hold_scope(kit)
    return s if hold_mm(kit) and s in HOLD_SCOPES else ""


def hold_mm_supports(tcl, scope):
    """does orfs_hold_mm.tcl implement `scope`?  nonport: listed in ::ot_hold_scope_supported_modes (what prd_hook.tcl and
    grt_nonport_hold.tcl check); reg2reg: the list, or (older copies) the ot_hold_repair_scope proc itself"""
    try:
        t = Path(tcl).read_text(errors="replace")
    except OSError:
        return False
    m = _HOLD_MODES_RX.search(t)
    if m:
        return scope in m.group(1).split()
    return False  # a named legacy proc alone cannot prove the scoped MM dispatch contract


def pin_late_hold_scope(pd):
    """Pin the selected late scope in Make and assert it at actual OpenROAD entry."""
    scope = hold_scope()
    if scope not in HOLD_SCOPES:
        return None
    pd = Path(pd)
    hook = pd / "prd_hook.tcl"
    if not hook.is_file():
        raise ValueError("scoped late ECO has no staged prd_hook.tcl; refused before physical repair")
    hook_text = hook.read_text()
    if "proc ot_prd_hold_scope_assert {}" not in hook_text or "ot_prd_expected_hold_scope" not in hook_text:
        raise ValueError("staged late-ECO hook lacks the runtime scope postcondition; refused before physical repair")
    def replace(path, text):
        # A resumed kit may be hard-linked to its donor. Replace only our path.
        with tempfile.NamedTemporaryFile("w", dir=pd, prefix=path.name + ".scope.", delete=False) as f:
            f.write(text)
            tmp = Path(f.name)
        tmp.chmod(path.stat().st_mode & 0o777)
        os.replace(tmp, path)
    config = pd / "config.mk"
    replace(config, config.read_text() + f"\noverride export OT_HOLD_REPAIR_SCOPE = {scope}\n")
    replace(hook, f"set ::ot_prd_expected_hold_scope {scope}\n" + hook_text)
    return scope


def refresh_hold_mm(pd, so, kit):
    """after prd_mk.sh: a pass dir whose orfs_hold_mm.tcl is missing or lacks the needed scope gets the SO pair (staged
    from the current tools by stage_so).  -> list of refreshed names; raises ValueError when the SO copy lacks it too"""
    scope = hold_mm_scope_needed(kit)
    if not scope or hold_mm_supports(Path(pd) / "orfs_hold_mm.tcl", scope):
        return []
    src = Path(so) / "tools"
    if not hold_mm_supports(src / "orfs_hold_mm.tcl", scope):
        raise ValueError(f"eco_loop: OT_HOLD_REPAIR_SCOPE={scope}: no orfs_hold_mm.tcl supporting it for pass dir {pd}")
    done = []
    for n in HOLD_MM_FILES:
        if (src / n).is_file():
            _copy_w(src / n, Path(pd) / n)
            done.append(n)
    return done


def post_runner(d, runner):
    """the kit runner copied into the pass dir when it has a sign-off-only GOAL=post (KV / HBM), else None"""
    names = [Path(runner).name] if runner else []
    for n in names + list(POST_RUNNERS):
        p = Path(d) / n
        if p.is_file():
            t = p.read_text(errors="replace")
            if "GOAL=post" in t or "GOAL != post" in t or "GOAL!=post" in t or '"$GOAL" = post' in t:
                return p
    return None


def set_aside_stage_resume(d):
    """KW-FIX-37 11-08 (COORD, HBM-HARD-7 EP host): prd_mk.sh copies a stage-resumed kit's resume.json into the pass dir, and
    the kit runner refuses GOAL=post while it is there (FAIL_PREFLOOR 'goal post unsupported', exit 10), so the ECO ended
    'sign-off wrote no record' on a finished route.  resume.json only steers the runner's make chain, which GOAL=post never
    enters.  Renamed in this pass dir only (never the kit); the file stays beside it for the audit.  -> new path or None"""
    p = Path(d) / "resume.json"
    if not (p.is_file() or p.is_symlink()):
        return None
    q = p.with_name("resume.json.was_stage_resume")
    os.replace(p, q)
    return str(q)


def docker():
    return "docker" if subprocess.call(["docker", "ps"], stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL) == 0 else "sudo docker"


ABSTRACT_SH = r'''set -uo pipefail
D=$1; CPUS=$2; MEM=$3; IMAGE=$4; DK=$5; MM=$6
PATCH=true; [ "$MM" = 1 ] && PATCH="python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1 || exit 9"
[ -f "$D/kwrs_busfit.py" ] && PATCH="python3 -I /work/kwrs_busfit.py patch /OpenROAD-flow-scripts/flow/scripts/util.tcl; $PATCH"
$DK run --rm --name eco-abs-$$ --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$D":/work -w /OpenROAD-flow-scripts/flow \
  "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; $PATCH; \
  make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS do-generate_abstract" > "$D/run_eco_abstract.log" 2>&1
rc=$?
$DK run --rm -v "$D":/work "$IMAGE" chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
exit $rc
'''


# KW-FIX-24 11-06 (COORD 15:5x, S81-ENGRR-B6 15:23/15:56): the route-keep incremental GRT (OT_PRD_ROUTE_KEEP ripped ...
# -> global_route -end_incremental -> ... restore) hung 3x on S81 eng_rr_e (B3, B4 eco1, B6 eco1r, epyc2): openroad at
# 100% of one core, run_prd.log flat for 90+ min.  Class fix: while a pass runs, a watchdog reads run_prd.log; when the
# last route-keep line is the rip (no restore after it) and the log has not grown for GRT_FLAT_S, it stops that pass's
# ECO container (docker stop of the prd-* container whose /work mount is this pass dir, nothing else) and the iteration
# ends grt_hang; run_loop reruns it ONCE as a full ECO route (OT_PRD_FROM=grt on every pass: incremental GRT from the
# ECO's GRT seed + a full detailed route, no route-keep) in i<n>g.  No check, margin or corner changes.
GRT_FLAT_S = int(os.environ.get("OT_ECO_GRT_FLAT_S", "2700"))   # 45 min
WATCH_POLL_S = 60
KEEP_RIP = re.compile(r"OT_PRD_ROUTE_KEEP ripped (\d+) nets")
KEEP_RESTORE = "OT_PRD_ROUTE_KEEP restore"


def grt_hang(log, flat_s=None, now=None):
    """-> rip count (int) when run_prd.log sits in the route-keep incremental GRT (rip line, no restore after it) and
    has not grown for flat_s seconds; else None"""
    flat_s = GRT_FLAT_S if flat_s is None else flat_s
    try:
        st = os.stat(log)
        t = Path(log).read_text(errors="replace")
    except OSError:
        return None
    m = None
    for m in KEEP_RIP.finditer(t):
        pass
    if m is None or KEEP_RESTORE in t[m.end():]:
        return None
    if (now or time.time()) - st.st_mtime < flat_s:
        return None
    return int(m.group(1))


def stop_eco_container(pd):
    """docker stop the prd-* ECO container(s) of pass dir pd (matched by the /work bind mount source) -> names stopped"""
    dk = docker().split()
    pd = str(Path(pd).resolve())
    try:
        ids = subprocess.run(dk + ["ps", "-q", "--filter", "name=prd-"], capture_output=True, text=True,
                             timeout=60).stdout.split()
    except (OSError, subprocess.SubprocessError):
        return []
    hit = []
    for cid in ids:
        try:
            r = subprocess.run(dk + ["inspect", "-f", "{{.Name}}\t{{range .Mounts}}{{.Source}}|{{.Destination}} {{end}}",
                                     cid], capture_output=True, text=True, timeout=60).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            continue
        name, _, mounts = r.partition("\t")
        srcs = [m.rpartition("|")[0] for m in mounts.split() if m.endswith("|/work")]
        if any(os.path.realpath(x) == pd for x in srcs):   # docker -v keeps the logical path; compare resolved
            subprocess.run(dk + ["stop", "-t", "30", cid], capture_output=True, timeout=180)
            hit.append(name.lstrip("/"))
    return hit


class GrtWatch:
    """background watchdog over one ECO pass (see GRT_FLAT_S); .hung = None or dict(rip=, flat_s=, stopped=)"""

    def __init__(self, pd, stop=None, flat_s=None, poll_s=None):
        self.log = Path(pd) / "run_prd.log"
        self.pd, self.stop_fn = pd, stop or stop_eco_container
        self.flat_s = GRT_FLAT_S if flat_s is None else flat_s
        self.poll_s = WATCH_POLL_S if poll_s is None else poll_s
        self.hung, self._done = None, threading.Event()
        self._t = threading.Thread(target=self._loop, daemon=True)

    def _loop(self):
        while not self._done.wait(self.poll_s):
            rip = grt_hang(self.log, self.flat_s)
            if rip is not None:
                self.hung = dict(rip=rip, flat_s=self.flat_s, at=time.time())
                self.hung["stopped"] = self.stop_fn(self.pd)
                return

    def __enter__(self):
        self._t.start()
        return self

    def __exit__(self, *a):
        self._done.set()
        self._t.join(timeout=5)
        return False


# ------------------------------------------------------------------------------------------------ one iteration
def flexpa_sig11(pd):
    """the ECO session died with SIGSEGV inside DRT pin access (FlexPA) -- the incremental-GRT dirty-route class"""
    try:
        t = (Path(pd) / "run_prd.log").read_text(errors="replace")
    except OSError:
        return False
    return "Signal 11 received" in t and "drt::FlexPA" in t


def stage_mismatch(pd):
    """the ECO hook found SPEF instances missing from the seed DB (prd_hook.tcl OT_PRD STAGE_MISMATCH): the kit's
    6_final is a post-route ECO of its 5_2_route.odb (DIE-S81-50 11-03, S81 l4) -> seed with OT_PRD_FROM=final"""
    try:
        t = (Path(pd) / "run_prd.log").read_text(errors="replace")
    except OSError:
        return False
    return "OT_PRD STAGE_MISMATCH" in t


def iterate(n, src, root, kit, runner, so, mode, hm, mem, cpus, run, image=IMAGE, prev=None, tag="", repair_rc="",
            trim=True, keep_route=True, watch_stop=None):
    """one ECO iteration from routed dir src into root/i<n><tag> (a single-mode kit's t<N> pass first into
    root/i<n><tag>t); repair_rc 'placement' = OT_PRD_REPAIR_RC (FlexPA SIG11 class); -> iteration record (metrics None
    when no sign-off)"""
    d = Path(root) / f"i{n}{tag}"
    t0 = time.time()
    vs = passes(kit, prev or {}, hm)
    it = dict(n=n, dir=str(d), source=str(src), mode=mode, variant="+".join(vs), started=t0, commands=[], rc={},
              pass_dirs=[], repair_rc=repair_rc or "auto")

    def step(name, cmd, **kw):
        it["commands"].append(" ".join(shlex.quote(str(c)) for c in cmd))
        rc = run([str(c) for c in cmd], **kw)
        it["rc"][name] = rc
        return rc

    def end(status, reason=""):
        it.update(status=status, reason=reason, finished=time.time(), wall_s=round(time.time() - t0, 1))
        return it

    def oom(rc, what, *logs):
        if rc and oom_evidence(rc, *logs):
            return end("ECO_OOM", f"{what} OOM-killed at {mem} GB docker cap (rc {rc})")
        if rc in STOP_RCS:
            return end("ABORTED", f"{what} stopped from outside (rc {rc}, no OOM line in its log): not a design result")
        return None

    s = src
    for i, v in enumerate(vs):
        pd = d if i == len(vs) - 1 else Path(root) / f"i{n}{tag}{v[0]}"
        it["pass_dirs"].append(str(pd))
        # the first pass of the iteration keeps / re-routes per the DRC count; a later one starts from a fresh ECO route
        # keep_route=False (GRT-hang class retry): every pass is a full ECO route (OT_PRD_FROM=grt), never route-keep
        env = dict(os.environ, OT_PRD_FROM=mode if i == 0 else ("route" if keep_route else "grt"), OT_PRD_POST="0",
                   OT_PRD_FINISH="1")
        if "OT_HOLD_REPAIR_SCOPE" not in env and hold_scope():
            env["OT_HOLD_REPAIR_SCOPE"] = hold_scope()
        if (Path(kit) / "kwrs_busfit.py").is_file():  # KW-FIX-5: the kit's LEF-only pins (prd_run.sh busfit_prep)
            env["OT_BUSFIT_PY"] = str(Path(kit) / "kwrs_busfit.py")
        if repair_rc:
            env["OT_PRD_REPAIR_RC"] = repair_rc
        stag = "" if len(vs) == 1 else "_" + v[0]
        if step("prd_mk" + stag, ["bash", PRD / "prd_mk.sh", s, pd, v, so], env=env):
            return end("ERROR", f"prd_mk.sh {v} failed (pass dir not staged)")
        try:
            fresh = refresh_hold_mm(pd, so, kit)
            pinned_scope = pin_late_hold_scope(pd)
            if pinned_scope:
                it["hold_repair_scope"] = pinned_scope
        except ValueError as e:
            return end("ERROR", str(e))
        if fresh:
            it.setdefault("hold_mm_refreshed", {})[v] = fresh
        if trim:
            gone = trim_superseded(root, pd)
            if gone:
                it.setdefault("trimmed", []).extend(gone)
        it.setdefault("eco_vclk_ps", {})[v] = eco_vclk_frame(pd, v, prev)
        with GrtWatch(pd, stop=watch_stop) as w:
            rc = step("prd_run" + stag, ["bash", PRD / "prd_run.sh", pd, cpus, mem, 1], env=env)
        if not rc and pinned_scope and v[0] in "mb":
            try:
                trace = (pd / "run_prd.log").read_text(errors="replace")
            except OSError:
                trace = ""
            if f"OT_PRD_HOLD_SCOPE_VERIFIED scope={pinned_scope} " not in trace:
                return end("ERROR", "late ECO scoped repair has no runtime completion receipt; no result accepted")
        if w.hung:
            it["grt_hang"] = w.hung
            return end("ERROR", f"ECO {v} route-keep incremental GRT hung (run_prd.log flat {w.hung['flat_s']} s after "
                                f"ripping {w.hung['rip']} nets; stopped {','.join(w.hung['stopped']) or 'no container'})")
        if rc:
            hit = oom(rc, f"ECO {v} session", pd / "run_prd.log", pd / "run_prd_finish.log")
            if hit:
                return hit
            if stage_mismatch(pd):
                it["stage_mismatch"] = True
                return end("ERROR", f"ECO {v} seed DB does not match the SPEF (OT_PRD STAGE_MISMATCH, run_prd.log)")
            if flexpa_sig11(pd):
                it["flexpa_sig11"] = True
                return end("ERROR", f"ECO {v} session SIGSEGV in DRT pin access (FlexPA SIG11 class, run_prd.log)")
            return end("ERROR", f"ECO {v} route / clock-freeze check / finish failed (prd_result.json)")
        # the ECO overrides steer only the ECO route: the next pass and the sign-off start from the kit's own config
        if (pd / "config.mk").is_file():
            shutil.copy2(pd / "config.mk", pd / "config_eco.mk")
        shutil.copy2(Path(kit) / "config.mk", pd / "config.mk")
        s = pd
    if trim and len(it["pass_dirs"]) > 1 and os.environ.get("OT_ECO_KEEP_ROUTED") != "1":
        # KW-FIX-32 11-07 (COORD 21:0x: 13 S81 slice_station loops held 165 GB on epyc6 root, ~8 GB per t<N> copy):
        # the final pass is routed from its own full copy, so the intermediate pass's ORFS run data goes now
        gone = prune_dirs(it["pass_dirs"][:-1])
        if gone:
            it["intermediate_pruned"] = gone
    ts = time.time()
    pr = post_runner(d, runner)
    if pr:
        aside = set_aside_stage_resume(d)
        if aside:
            it["stage_resume_set_aside"] = aside
        # RESYNTH-GUARD is skipped while resume.json exists; keep that for this post, which runs no make chain
        step("signoff", ["bash", pr, d, "post", mem, cpus], **({"env": dict(os.environ, OT_ALLOW_RESYNTH="1")} if aside else {}))
    else:
        rc = step("abstract", ["bash", "-c", ABSTRACT_SH, "eco_abstract", d, cpus, mem, image, docker(),
                               "1" if hold_mm(kit) else "0"])
        if rc:
            hit = oom(rc, "ECO abstract", d / "run_eco_abstract.log")
            if hit:
                return hit
            return end("ERROR", "do-generate_abstract failed (run_eco_abstract.log)")
        step("signoff", [sys.executable, "-I", d / "signoff.py", "run", "--run-dir", d / "run", "--kit", d,
                         "--out", d / "signoff", "--image", image, "--corners", "tt,ff"],
             env=dict(os.environ, SIGNOFF_DOCKER=os.environ.get("SIGNOFF_DOCKER", "docker")))
    so_rec = newest_signoff(d, ts - 1)
    if not so_rec:
        hit = oom(it["rc"].get("signoff"), "ECO sign-off")
        if hit:
            return hit
        return end("ERROR", "sign-off wrote no record")
    it["signoff"] = str(so_rec)
    rec = load(so_rec)
    it["base"] = (rec.get("inputs") or {}).get("base")
    it["metrics"] = metrics(rec, so_rec)
    return end("SIGNED" if it["metrics"]["signed"] else "NOT_SIGNED")


TRIM_ODBS = ("5_route.odb", "5_3_fillcell.odb", "6_1_fill.odb")


def trim_superseded(root, current):
    """KW-FIX-16 11-05 (COORD URGENT: intel2 scratch2 fell ~1 GB/min, ECO loops wrote ~8 GB of odbs per iteration):
    once pass dir `current` is staged (prd_mk.sh has copied its seed: 5_1_grt / 5_2_route / 6_final, never the three
    below), every earlier finished pass dir under root drops 5_route / 5_3_fillcell / 6_1_fill odbs.  Kept: 6_final.odb
    (the sign-off routed DB; a base without it is not touched), 5_2_route / 5_1_grt (seeds), logs, reports, sign-off,
    and any pass whose sign-off is SIGNED.  OT_ECO_KEEP_ROUTED=1 (or run_loop keep) turns it off.  -> [removed paths]"""
    if os.environ.get("OT_ECO_KEEP_ROUTED") == "1":
        return []
    root, cur = Path(root), Path(current).resolve()
    gone = []
    for d in sorted(root.glob("i*")):
        if not d.is_dir() or not re.fullmatch(r"i\d+[a-z]*", d.name) or d.resolve() == cur:
            continue
        so_rec = load(d / "signoff" / "signoff.json") if (d / "signoff" / "signoff.json").is_file() else {}
        if so_rec and metrics(so_rec)["signed"]:
            continue
        for base in d.glob("run/results/asap7/*/base"):
            if not (base / "6_final.odb").is_file():
                continue
            for name in TRIM_ODBS:
                f = base / name
                if f.is_file() and not f.is_symlink():
                    f.unlink()
                    gone.append(str(f))
    return gone


def trim_best(it):
    """KW-FIX-24 11-06 (COORD 16:3x URGENT: epyc6 scratch2 10 GB; S81 slice_station__t7 a15 eco_*/i2 = 11 GB, copied home
    by the ot-run spill copy-back): the loop's final dir keeps 5_route / 5_3_fillcell / 6_1_fill odbs (3 x 2 GB) that
    only lead to its 6_final.odb.  Once 6_final.odb exists and is the dir's sign-off routed DB (signoff.py ROUTED_DBS
    order: 6_final first), they go.  Kept: 6_final.*, 5_2_route / 5_1_grt seeds, logs, reports, sign-off.
    OT_ECO_KEEP_ROUTED=1 (or run_loop keep) turns it off.  -> [removed paths]"""
    if os.environ.get("OT_ECO_KEEP_ROUTED") == "1" or not it or not it.get("dir"):
        return []
    gone = []
    for base in Path(it["dir"]).glob("run/results/asap7/*/base"):
        fin = base / "6_final.odb"
        if not fin.is_file() or fin.stat().st_size == 0:
            continue
        for name in TRIM_ODBS:
            f = base / name
            if f.is_file() and not f.is_symlink():
                f.unlink()
                gone.append(str(f))
    return gone


def prune_dirs(dirs):
    """remove run/results + run/objects (the full ORFS copy) under each pass dir; config, logs, reports, PRD.json,
    prd_result.json and signoff/ stay as evidence.  -> [removed paths]"""
    gone = []
    for d in map(Path, dirs):
        for sub in ("run/results", "run/objects"):
            p = d / sub
            if p.is_dir() and not p.is_symlink() and str(p.resolve()).startswith(str(d.resolve()) + os.sep):
                shutil.rmtree(p, ignore_errors=True)
                gone.append(str(p))
    return gone


def prune(it, intermediate_only=False):
    """drop the heavy ORFS run data of a superseded iteration (json / logs / sign-off stay as evidence); the best
    iteration keeps its final dir and drops only its intermediate t<N> pass"""
    dirs = [Path(p) for p in it.get("pass_dirs") or [] if p != it["dir"]]
    if not intermediate_only:
        dirs.append(Path(it["dir"]))
    prune_dirs(dirs)
    if not intermediate_only:
        it["pruned"] = True


# ------------------------------------------------------------------------------------------------ the loop
def route_hold_declared(kit):
    """ROUTE-HOLD-PASS declared by the kit spec: freeze.json flow_defaults.route_hold_pass.on and config.mk
    OT_ROUTE_HOLD_PASS = 1 (last assignment wins), both written by gen_core_kit_hbm --route-hold-pass on"""
    kit = Path(kit)
    try:
        fz = json.loads((kit / "freeze.json").read_text())
    except (OSError, ValueError):
        return False
    if not (((fz.get("flow_defaults") or {}).get("route_hold_pass") or {}).get("on") is True):
        return False
    v = None
    try:
        for line in (kit / "config.mk").read_text().splitlines():
            m = re.match(r"^\s*(?:override\s+)?(?:export\s+)?OT_ROUTE_HOLD_PASS\s*[:?]?=\s*(.*?)\s*$", line)
            if m:
                v = m[1]
    except OSError:
        return False
    return v == "1"


def route_hold_ran(kit):
    """the declared pass has run on this kit (KIT/route_hold_pass.json run true)"""
    try:
        return bool(json.loads((Path(kit) / "route_hold_pass.json").read_text()).get("run"))
    except (OSError, ValueError, AttributeError):
        return False


def run_loop(kit, base_signoff, root=None, runner=None, max_iter=MAX_ITER, hold_margin=HOLD_MARGIN_PS, mem=48,
             cpus=8, run=subprocess.call, tools=HERE, image=IMAGE, keep=False, repair_rc="", from_mode="",
             owner_override=False, strict_one_pass=False, route_hold_form=False):
    """Apply the core-owned repair/scoring default only for this late-ECO call."""
    options = dict(locals())
    if route_hold_form:
        return _run_loop(**options)
    token = _LATE_HOLD_SCOPE.set(late_hold_scope(kit))
    try:
        return _run_loop(**options)
    finally:
        _LATE_HOLD_SCOPE.reset(token)


def _run_loop(kit, base_signoff, root=None, runner=None, max_iter=MAX_ITER, hold_margin=HOLD_MARGIN_PS, mem=48,
             cpus=8, run=subprocess.call, tools=HERE, image=IMAGE, keep=False, repair_rc="", from_mode="",
             owner_override=False, strict_one_pass=False, route_hold_form=False):
    """-> result dict (also written to ROOT/eco_loop.json).  verdict PASS | EXHAUSTED | ERROR | NOT_ELIGIBLE | NOT_NEAR_MISS

    route_hold_form (ROUTE-HOLD-PASS, DIE-HBM-97 11-10, COORD vecd-clkroot-r2 ruling (a)): run the kit's DECLARED in-flow
    routed-RCX hold pass (tools/die_plan/route_hold_pass.py).  Honoured only when the kit's own spec declares it
    (route_hold_declared: freeze.json flow_defaults.route_hold_pass.on AND config.mk OT_ROUTE_HOLD_PASS = 1, both written by
    the generator before the build); then ONE hold repair on the routed RCX parasitics, one physical dispatch, no recovery
    retry, and the near-miss numbers are recorded (res near_miss) without stopping it.  A caller flag on a kit that does
    not declare the form is an ERROR.  Gates are unchanged.  A kit whose declared pass has run takes no ECO on top
    (NOT_ELIGIBLE)."""
    if route_hold_form and (max_iter != 1 or not strict_one_pass):
        raise ValueError("route_hold_form requires max_iter=1 and strict_one_pass")
    if max_iter > MAX_ITER:
        raise ValueError(max_iter_refusal(max_iter))
    if strict_one_pass and max_iter != 1:
        raise ValueError("strict-one-pass requires max_iter=1")
    kit = Path(kit).resolve()
    t0 = time.time()
    base_signoff = Path(base_signoff).resolve()
    base_rec = load(base_signoff)
    root = Path(root or kit / ("eco_" + time.strftime("%Y%m%d_%H%M%S") + "_" + str(os.getpid()))).resolve()
    mem_in = mem
    mem, peak = eco_mem(kit, mem)
    res = dict(schema=SCHEMA, kind="eco", tool="tools/die_plan/eco_loop.py", kit=str(kit), root=str(root),
               mem_requested_gb=mem_in, mem_gb=mem, kit_peak_gb=peak, mem_factor=ECO_MEM_FACTOR,
               base_signoff=str(base_signoff), base_routed_db=(base_rec.get("inputs") or {}).get("odb"),
               base_metrics=metrics(base_rec, base_signoff) if base_rec else None,
               hold_repair_scope=kit_hold_scope(kit), max_iter=max_iter, hold_margin_ps=hold_margin,
               started=t0, iterations=[], flow=flow_sha(tools), host=os.uname().nodename)
    if strict_one_pass:
        budget = dict(limit=1, dispatched=0, blocked=[])
        res["strict_one_pass"] = True
        res["physical_dispatch_budget"] = budget
        original_run = run

        def run(cmd, **kwargs):
            # The common physical entry point also covers split t<N>/b<N>
            # passes and any future recovery path, not just today's retries.
            if len(cmd) > 1 and cmd[0] == "bash" and Path(cmd[1]).name == "prd_run.sh":
                if budget["dispatched"] >= budget["limit"]:
                    budget["blocked"].append(list(map(str, cmd)))
                    print("ECO_STRICT_ONE_PASS: refused additional physical dispatch", flush=True)
                    return 73
                budget["dispatched"] += 1
            return original_run(cmd, **kwargs)
    ok, why = eligible(base_rec, None if route_hold_form else base_signoff)
    res["eligibility"] = why
    declared = route_hold_declared(kit)
    res["route_hold_form"] = dict(requested=bool(route_hold_form), declared=declared)

    def done(verdict, reason):
        res.update(verdict=verdict, reason=reason, finished=time.time(), wall_s=round(time.time() - t0, 1))
        if root.is_dir():
            (root / "eco_loop.json").write_text(json.dumps(res, indent=1) + "\n")
        return res

    if route_hold_form and not declared:
        return done("ERROR", "route_hold_form requested but the kit spec does not declare ROUTE-HOLD-PASS "
                    "(freeze.json flow_defaults.route_hold_pass.on + config.mk OT_ROUTE_HOLD_PASS = 1)")
    if not route_hold_form and declared and route_hold_ran(kit):
        return done("NOT_ELIGIBLE", "ROUTE-HOLD-PASS form: the declared in-flow hold pass has run; no further ECO on top "
                    "(COORD vecd-clkroot-r2 (4))")
    if not ok:
        return done("NOT_ELIGIBLE", why)
    near, far, warn = near_miss(base_rec, base_signoff)
    res["near_miss"] = dict(near=near, beyond=far, advisory=warn, owner_override=bool(owner_override),
                            route_hold_form=bool(route_hold_form))
    for w in warn:
        print("ECO_LOOP advisory: " + w, flush=True)
    if not near and route_hold_form:
        print("ECO_LOOP declared ROUTE-HOLD-PASS form: beyond the late-ECO near-miss numbers (" + "; ".join(far) +
              "), recorded; the kit's declared one-pass stage runs", flush=True)
    if not near and not owner_override and not route_hold_form:
        return done("NOT_NEAR_MISS", "; ".join(far) + f" (near miss: setup/hold no worse than {NEAR_WNS_PS:g} ps on at most "
                    f"{NEAR_ENDPOINTS} endpoints, at most {NEAR_SLEW_NETS} slew nets, DRC under {NEAR_DRC}): GEOMETRY + REDESIGN, no ECO")
    root.mkdir(parents=True, exist_ok=False)
    try:
        so = stage_so(kit, root, tools)
    except ValueError as e:
        if "OT_HOLD_REPAIR_SCOPE" not in str(e):
            raise
        return done("ERROR", str(e) + " -- refused before any ECO route; no iteration used")
    src, prev = kit, res["base_metrics"]
    best = None
    verdict, stop = "EXHAUSTED", f"{max_iter} iteration(s), still not signed: GEOMETRY + REDESIGN, no second ECO"
    for n in range(1, max_iter + 1):
        # --from wins over OT_ECO_FROM=route|grt: owner-chosen seed (DIE-HEAD-59: a DRC tied to one pin + a GRT-session RSZ-0074, route-keep)
        mode = from_mode or os.environ.get("OT_ECO_FROM") or ("route" if prev["drc"] == 0 else "grt")
        it = iterate(n, src, root, kit, runner, so, mode, hold_margin, mem, cpus, run, image, prev=prev,
                     repair_rc=repair_rc, trim=not keep)
        res["iterations"].append(it)
        if it.get("flexpa_sig11") and not repair_rc and not strict_one_pass:
            # class retry (once per loop): the same iteration with placement-estimated ECO nets in a new dir
            repair_rc = "placement"
            res["repair_rc_retry"] = f"iteration {n}: FlexPA SIG11 -> OT_PRD_REPAIR_RC=placement"
            it = iterate(n, src, root, kit, runner, so, mode, hold_margin, mem, cpus, run, image, prev=prev,
                         tag="r", repair_rc=repair_rc, trim=not keep)
            res["iterations"].append(it)
        if it.get("grt_hang") and "grt_hang_retry" not in res and not strict_one_pass:
            # KW-FIX-24 class retry (once per loop): the same iteration as a full ECO route, no route-keep
            res["grt_hang_retry"] = f"iteration {n}: route-keep incremental GRT hang -> OT_PRD_FROM=grt, full detailed route"
            it = iterate(n, src, root, kit, runner, so, "grt", hold_margin, mem, cpus, run, image, prev=prev,
                         tag="g", repair_rc=repair_rc, trim=not keep, keep_route=False)
            res["iterations"].append(it)
        if it.get("stage_mismatch") and n == 1 and mode == "route" and not strict_one_pass:
            # class retry: the kit's routed seed predates its signed 6_final (post-route ECO kit) -> seed with 6_final
            res["stage_retry"] = "iteration 1: OT_PRD STAGE_MISMATCH -> OT_PRD_FROM=final"
            it = iterate(n, src, root, kit, runner, so, "final", hold_margin, mem, cpus, run, image, prev=prev,
                         tag="f", repair_rc=repair_rc, trim=not keep)
            res["iterations"].append(it)
        m = it.get("metrics")
        if not m:
            stop = f"iteration {n}: {it.get('reason')}"
            if it.get("status") in ("ECO_OOM", "ABORTED"):
                verdict = it["status"]
            break
        if best is None or better(m, best["metrics"]):
            old, best = best, it
            if old is not None and not keep and os.environ.get("OT_ECO_KEEP_ROUTED") != "1":
                # KW-FIX-32 11-07 (COORD 21:0x): iteration n is adopted over the previous best, whose full ORFS copy
                # (already staged into iteration n by prd_mk) goes now instead of at loop end; its sign-off stays
                prune(old)
        if m["signed"]:
            best, verdict, stop = it, "PASS", f"signed off after {n} ECO iteration(s)"
            break
        if not improved(prev, m):
            stop = f"no improvement at iteration {n} (WNS gain < {MIN_WNS_GAIN_PS} ps, DRV/DRC not falling)"
            break
        src, prev = Path(it["dir"]), m
    if best is None:
        if verdict not in ("ECO_OOM", "ABORTED"):
            verdict = "ERROR"
    else:
        res["best"] = dict(n=best["n"], dir=best["dir"], signoff=best["signoff"], base=best["base"],
                           metrics=best["metrics"])
    # A completed route can lack metrics because abstract/signoff infrastructure
    # failed. Keep its entire terminal iteration available for post-only recovery.
    recovery = res["iterations"][-1] if res["iterations"] and not res["iterations"][-1].get("metrics") else None
    if recovery is not None:
        recovery["retained_for_recovery"] = True
        res["recovery"] = dict(dir=recovery["dir"], pass_dirs=list(recovery["pass_dirs"]),
                               reason=recovery.get("reason"), status=recovery.get("status"))
    if not keep:
        for it in res["iterations"]:
            if it is not recovery:
                prune(it, intermediate_only=it is best)
        if best is not None:
            gone = trim_best(best)
            if gone:
                best.setdefault("trimmed", []).extend(gone)
                res["best_trimmed"] = len(gone)
    return done(verdict, stop)


def max_iter_refusal(n):
    return (f"eco_loop: --max-iter {n} refused: one late-stage iteration per routed form, at most {MAX_ITER} (OWNER 11-07 05:3x). "
            "If it does not sign off: GEOMETRY + REDESIGN, pin cycles first.")


def summary(res):
    """one-line evidence for FAIL reasons / class tables"""
    if not res:
        return ""
    b = (res.get("best") or {}).get("metrics") or {}
    m0 = res.get("base_metrics") or {}
    its = len(res.get("iterations") or [])
    if res.get("verdict") == "NOT_ELIGIBLE":
        return f"late-ECO not eligible: {res.get('reason')}"
    if res.get("verdict") == "NOT_NEAR_MISS":
        return f"late-ECO not a near miss: {res.get('reason')}"
    tag = {"PASS": "late-ECO PASS", "ECO_OOM": "late-ECO OOM", "ABORTED": "late-ECO ABORTED"}.get(res.get("verdict"), "late-ECO exhausted")
    return (f"{tag} ({its} it, {res.get('wall_s')} s): TT {m0.get('tt')}->{b.get('tt')} FF {m0.get('ff')}->{b.get('ff')} "
            + (f"({b.get('hold_score_scope', 'non-port')} {m0.get('ff_np')}/{m0.get('ff_np_n')}->{b.get('ff_np')}/{b.get('ff_np_n')}) " if "ff_np" in b else "")
            + f"drv {m0.get('drv')}->{b.get('drv')} drc {m0.get('drc')}->{b.get('drc')}; {res.get('reason')}")


def lec_tool_of(kit, lec_tool=None, tools=HERE):
    """KW-FIX-44 11-09 (COORD; HBM-CORES-B own_RF4T eco1b met every sign-off number and ended LEC_FAIL only because the
    kit had no lec.py): --lec-tool, else the kit's own lec.py, else the current tools' lec.py.  -> Path or None"""
    for p in ([Path(lec_tool)] if lec_tool else []) + [Path(kit) / "lec.py", Path(tools) / "lec.py"]:
        if p.is_file():
            return p
    return None


def run_lec(kit, res, mem, cpus, lec_tool=None, run=subprocess.call, tools=HERE):
    """Prove the actual ECO capsule; expose the fresh receipt for resign.py --lec."""
    best = res.get("best") or {}
    netlist = Path(best.get("base") or "") / "6_final.v"
    tool = lec_tool_of(kit, lec_tool, tools)
    if tool is None:
        res["lec"] = dict(tool=None, netlist=str(netlist), exit=None, verdict="NO_LEC_TOOL",
                          reason=f"no lec.py: --lec-tool {lec_tool or '-'}, kit {kit}, tools {tools} (a tool gap, not a design verdict)")
        Path(res["root"], "eco_loop.json").write_text(json.dumps(res, indent=1) + "\n")
        print("ECO_LOOP LEC_TOOL_MISSING: " + res["lec"]["reason"], file=sys.stderr, flush=True)
        return False
    candidate = Path(best["dir"]).resolve()
    out = Path(tempfile.mkdtemp(prefix="lec_postroute_", dir=candidate))
    rc = run([sys.executable, str(tool), str(candidate), "--netlist", str(netlist), "--out", str(out), "--mem", str(mem),
              "--jobs", str(cpus)], env=dict(os.environ, OT_LEC_SUPERSET_VEC="1"))
    lec = load(out / "lec.json") if rc == 0 else {}
    res["lec"] = dict(tool=str(tool), netlist=str(netlist), record=str(out / "lec.json"), exit=rc,
                      verdict=lec.get("verdict"), all_shown=(lec.get("superset_vec") or {}).get("all_shown"))
    Path(res["root"], "eco_loop.json").write_text(json.dumps(res, indent=1) + "\n")
    return rc == 0 and lec.get("verdict") == "EQUIVALENT"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--kit", required=True)
    r.add_argument("--signoff", help="base sign-off record (default: newest KIT/signoff*/signoff.json)")
    r.add_argument("--runner", help="the kit runner (its GOAL=post signs off a pass dir when supported)")
    r.add_argument("--out", help="loop root (new dir; default KIT/eco_<ts>)")
    r.add_argument("--max-iter", type=int, default=MAX_ITER)
    r.add_argument("--hold-margin", type=int, default=HOLD_MARGIN_PS)
    r.add_argument("--mem", type=int, default=48)
    r.add_argument("--cpus", type=int, default=8)
    r.add_argument("--keep", action="store_true", help="keep the run data of superseded iterations")
    r.add_argument("--strict-one-pass", action="store_true",
                   help="one physical prd_run dispatch total; disable recovery retries (default unchanged)")
    r.add_argument("--lec", action="store_true", help="run the kit's post-route LEC on a PASS (into BEST/lec)")
    r.add_argument("--lec-tool")
    r.add_argument("--owner-override", action="store_true", help="run although the base record is beyond the near-miss numbers")
    # DIE-KV-67/CL 11-04: a small-DRC kit whose full DRT took many hours (ZH rfB: 13.7 h) can keep its wires instead
    r.add_argument("--from", dest="from_mode", choices=["route", "grt"], default="",
                   help="seed of every iteration (default: route when the DB has no DRC, else grt)")
    r.add_argument("--repair-rc", choices=["placement", "grt"], default="",
                   help="OT_PRD_REPAIR_RC from iteration 1 (default: the hook decides, a wired seed repairs on placement; a fresh one after a FlexPA SIG11)")
    c = sub.add_parser("check")
    c.add_argument("record")
    a = ap.parse_args()
    if a.cmd == "check":
        rec = load(a.record)
        ok, why = eligible(rec, a.record)
        print(("ECO_ELIGIBLE " if ok else "ECO_NOT_ELIGIBLE ") + why)
        if not ok:
            return 1
        near, far, warn = near_miss(rec, a.record)
        print(("ECO_NEAR_MISS" if near else "ECO_NOT_NEAR_MISS " + "; ".join(far)) + ("" if not warn else " | advisory: " + "; ".join(warn)))
        return 0 if near else 1
    if a.max_iter > MAX_ITER:
        print(max_iter_refusal(a.max_iter), file=sys.stderr)
        return 2
    base = Path(a.signoff) if a.signoff else newest_signoff(a.kit)
    if not base:
        print("ECO_LOOP FAIL: no sign-off record in the kit")
        return 3
    res = run_loop(a.kit, base, a.out, a.runner, a.max_iter, a.hold_margin, a.mem, a.cpus, keep=a.keep,
                   repair_rc=a.repair_rc, from_mode=a.from_mode, owner_override=a.owner_override,
                   strict_one_pass=a.strict_one_pass)
    if res["verdict"] == "PASS" and a.lec and not run_lec(a.kit, res, a.mem, a.cpus, a.lec_tool):
        # NO_LEC_TOOL: the routed DB is untouched and signed; only the proof is missing -> re-sign uncharged with a tool
        res["verdict"] = "LEC_TOOL_MISSING" if (res.get("lec") or {}).get("verdict") == "NO_LEC_TOOL" else "LEC_FAIL"
        Path(res["root"], "eco_loop.json").write_text(json.dumps(res, indent=1) + "\n")
    print("ECO_LOOP " + res["verdict"] + ": " + summary(res))
    print("ECO_LOOP record " + str(Path(res["root"]) / "eco_loop.json"))
    return 0 if res["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
