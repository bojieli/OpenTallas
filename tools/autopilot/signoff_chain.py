#!/usr/bin/env python3
"""Continue a reviewed kit through its existing runner, sign-off and routed LEC.

Runs inside the same ot-run allocation as the physical runner. Diagnostic CTS/GRT
goals remain diagnostics. Existing runner corner/hold policy takes precedence.
"""
import argparse
import json
import os
import subprocess
import tempfile
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


def _profile_module():
    """tools/die_plan/signoff_profile.py: in the admission bundle (die_plan/ beside this file) or a repo checkout"""
    here = Path(__file__).resolve().parent
    for d in (here / "die_plan", here.parent / "die_plan"):
        if (d / "signoff_profile.py").is_file():
            import importlib.util
            spec = importlib.util.spec_from_file_location("signoff_profile", d / "signoff_profile.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise RuntimeError("signoff_profile.py not staged with the chain (R-MINIMAL profile)")


def minimal():
    """OWNER 11-13 R-MINIMAL (default) vs OT_SIGNOFF_PROFILE=legacy"""
    return os.environ.get("OT_SIGNOFF_PROFILE", "minimal").strip().lower() != "legacy"


def signed(physical):
    """the record passes sign-off under the active profile.  minimal: re-judged here from the record's measured numbers
    (DRC 0, TT setup >= -42 ps, FF hold >= 0), so a record from an older kit-frozen signoff.py is judged by R-MINIMAL
    too; legacy: SIGNED or LOCAL_PASS_NEEDS_PARENT as before"""
    if minimal():
        return _profile_module().judge(physical)["verdict"] == "SIGNED"
    return physical.get("verdict") in ("SIGNED", "LOCAL_PASS_NEEDS_PARENT")


def signoff_gates(physical):
    if minimal():
        j = _profile_module().judge(physical)
        return dict(j["gates"])
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


LATE_ECO_KEYS = ("verdict", "reason", "eligibility", "root", "base_signoff", "base_routed_db", "base_metrics", "best",
                 "flow", "wall_s", "max_iter", "hold_margin_ps", "kind", "schema")


def eco_tool():
    """tools/die_plan/eco_loop.py: in the admission bundle (die_plan/ beside this file) or in a repo checkout"""
    here = Path(__file__).resolve().parent
    for p in (here / "die_plan" / "eco_loop.py", here.parent / "die_plan" / "eco_loop.py"):
        if p.is_file():
            return p
    return None


def late_eco_enabled(kit, flag=True):
    """default ON (OWNER 11-01 20:0x); opt-out: --no-late-eco, OT_LATE_ECO=0, or a KIT/late_eco.off marker"""
    return bool(flag) and os.environ.get("OT_LATE_ECO", "1") != "0" and not (Path(kit) / "late_eco.off").exists()


RT_ROOT = "/srv/opentallas-scratch2/claude/rt"


def current_eco_tool(dest=None, host=None, run=subprocess.run, local=True):
    """FABLE-FLOW-1555 (C): the late ECO reads eco_loop.py + post_route_drv (prd_mk.sh ...) from rt/current AT RUN TIME, not from the admission
    bundle frozen at submit (4 of 4 late ECOs of jobs submitted before 8f3d1679753 died on the old prd_mk).  rt/current is read directly when it is
    visible, else (sealed job: /srv is hidden) tools/die_plan + physical/common_flow of the hub's rt/current are fetched over ssh
    (as the admission bootstrap fetches its bundle) into a job-local repo-shaped tree.  -> (eco_loop.py path, rt sha) or (None, why)"""
    cur = Path(RT_ROOT) / "current"
    if local and (cur / "tools/die_plan/eco_loop.py").is_file():
        return (cur / "tools/die_plan/eco_loop.py").resolve(), os.path.basename(os.path.realpath(cur))
    host = host or os.environ.get("AP_ADMISSION_HUB", "hub")
    dest = Path(dest or tempfile.mkdtemp(prefix="eco-rt-", dir=os.environ.get("TMPDIR") or "/tmp"))
    rt = RT_ROOT
    cmd = (f"cd {rt} && s=$(readlink current) && cd current && echo RT_SHA=$s >&2 && "
           "tar -cf - --exclude=__pycache__ --exclude='test_*' tools/die_plan physical/common_flow")
    try:
        src = subprocess.Popen(["ssh", "-n", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=15", host, cmd],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ex = run(["tar", "-C", str(dest), "-xf", "-"], stdin=src.stdout)
        src.stdout.close()
        err = src.stderr.read().decode(errors="replace")
        rc = src.wait()
    except (OSError, subprocess.SubprocessError) as e:
        return None, f"fetch from {host} failed: {e}"
    sha = (err.split("RT_SHA=", 1)[1].split()[0] if "RT_SHA=" in err else "?")
    tool = dest / "tools/die_plan/eco_loop.py"
    if rc or getattr(ex, "returncode", 1) or not tool.is_file():
        return None, f"fetch from {host} rc {rc}: {err.strip()[-200:]}"
    return tool, sha


def late_eco(kit, record, runner, mem, threads, run=subprocess.call, current=current_eco_tool):
    """KW-ECO-1: the late-stage ECO loop on the kit's routed DB -> eco_loop result dict (None: tool missing)"""
    tool, why = current() if current else (None, "off")
    if tool:
        print(f"LATE_ECO_TOOLS rt {why}: eco_loop.py + post_route_drv from rt/current ({tool.parent}); ECO sign-off signoff.py {_sha(tool.parent / 'signoff.py')}", flush=True)
    else:
        tool = eco_tool()
        print(f"LATE_ECO_TOOLS SKIPPED rt/current ({why}); using the admission bundle copy {tool}", flush=True)
    if tool is None:
        return dict(verdict="ERROR", reason="eco_loop.py not staged with the chain")
    import importlib.util
    spec = importlib.util.spec_from_file_location("eco_loop", tool)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    res = mod.run_loop(kit, record, runner=runner, mem=mem, cpus=threads, run=run, tools=tool.parent)
    res["summary"] = mod.summary(res)
    return res


def eco_receipt(res):
    out = {k: res.get(k) for k in LATE_ECO_KEYS if k in res}
    out["summary"] = res.get("summary", "")
    out["record"] = str(Path(res["root"]) / "eco_loop.json") if res.get("root") and res.get("iterations") else None
    out["iterations"] = [{k: it.get(k) for k in ("n", "mode", "variant", "status", "reason", "metrics", "wall_s",
                                                 "commands", "signoff", "base")} for it in res.get("iterations") or []]
    return out


KFR = "/srv/opentallas-scratch2/claude/rt/current/tools/autopilot/kit_flow_refresh.py"


def flow_refresh(kit, goal, script=KFR, bundle=None):
    """TOOLS-DECOUPLE class fix (COORD 11-18): before the physical runner, the kit's verbatim copies of main flow scripts are replaced by
    the current versions (record KIT/flow_refresh.jsonl), so a fix on main reaches every stage this job has not run yet.
    FABLE-FLOW-1000 A: the job is sealed (bwrap: rt/current is not visible), so the refresher, the flow blob index and the current
    scripts come from the admission bundle this chain runs from (die_plan/__flow__); rt/current only when the bundle has none.
    A skip prints one KIT_FLOW_REFRESH SKIPPED line.  OT_FLOW_REFRESH=0 or KIT/.no_flow_refresh turns it off.  -> the refresher exit code:
    75 = FLOW-REFRESH-PARTIAL (all or nothing: nothing was changed, the caller defers the stage)."""
    b = Path(bundle) if bundle else Path(__file__).resolve().parent
    fl = b / "die_plan" / "__flow__"
    if os.environ.get("OT_FLOW_REFRESH", "1") == "0":
        print("KIT_FLOW_REFRESH SKIPPED: OT_FLOW_REFRESH=0", flush=True)
        return None
    if (fl / "kit_flow_refresh.py").is_file() and (fl / "flow_blobs.json").is_file():
        argv = [sys.executable, "-I", str(fl / "kit_flow_refresh.py"), "--kit", str(kit), "--stage", str(goal),
                "--index", str(fl / "flow_blobs.json"), "--src", f"tools/die_plan={b / 'die_plan'}",
                "--src", f"physical/common_flow={fl / 'common_flow'}", "--src", f"tools/autopilot={fl}", "--rt", str(b)]
    elif os.path.isfile(script):
        argv = [sys.executable, "-I", script, "--kit", str(kit), "--stage", str(goal)]
    else:
        print(f"KIT_FLOW_REFRESH SKIPPED: no refresher in the admission bundle {fl} and {script} is not visible in this job", flush=True)
        return None
    try:
        return subprocess.call(argv, timeout=600)
    except Exception as e:                                      # noqa: BLE001
        print(f"KIT_FLOW_REFRESH skipped: {type(e).__name__}: {e}", flush=True)
        return None


def runner_override(kit, since=0.0):
    """kit_flow_refresh.runner_override without importing it (the refresher may come from the bundle): the last flow_refresh.jsonl
    record's runner_override, when that file exists and was written by this refresh"""
    try:
        lines = (Path(kit) / "flow_refresh.jsonl").read_text().splitlines()
        alt = (json.loads(lines[-1]) if lines else {}).get("runner_override")
    except (OSError, ValueError):
        return None
    return alt if alt and os.path.isfile(alt) and os.path.getmtime(alt) >= since - 5 else None


def _sha(path):
    import hashlib
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]
    except OSError:
        return "-"


def signoff_tool_source(bundle=None):
    """-> (die_plan dir, label): rt/current when visible, else the admission bundle this chain runs from (die_plan/), else None"""
    cur = Path(RT_ROOT) / "current" / "tools" / "die_plan"
    if (cur / "signoff.py").is_file():
        return cur.resolve(), "rt " + os.path.basename(os.path.realpath(Path(RT_ROOT) / "current"))
    b = Path(bundle) if bundle else Path(__file__).resolve().parent
    if (b / "die_plan" / "signoff.py").is_file():
        return b / "die_plan", "admission bundle " + b.name[:20]
    return None, "no rt/current and no admission bundle die_plan"


def stage_signoff_tool(kit, bundle=None, source=None):
    """FABLE-CLOSURE 1935 lever 5 (COORD 11-18): the sign-off (the runner's signoff.py run, the chain's fallback run, and so every
    route / finish verdict) uses the CURRENT signoff.py family, not the kit's gen-time copy (hc0: kit copy vs rt differed by 11 ps TT,
    8.6 ps hold).  kit_flow_refresh replaces only verbatim main copies inside its blob window; this stages the whole SIGNOFF_BUNDLE
    (signoff.py bundle, so the family stays API-consistent) from rt/current or the admission bundle into a temp dir, then copy +
    rename into the kit.  One SIGNOFF_TOOL line + KIT/signoff_tool.jsonl name the sha used.  Opt-out: KIT/.keep_kit_signoff."""
    kit = Path(kit)
    if (kit / ".keep_kit_signoff").exists() or os.environ.get("OT_SIGNOFF_FROM_RT", "1") == "0":
        print(f"SIGNOFF_TOOL KIT copy kept (opt-out): signoff.py {_sha(kit / 'signoff.py')}", flush=True)
        return None
    src, label = (Path(source), "given") if source else signoff_tool_source(bundle)
    if src is None:
        print(f"SIGNOFF_TOOL SKIPPED ({label}): kit copy signoff.py {_sha(kit / 'signoff.py')}", flush=True)
        return None
    old = _sha(kit / "signoff.py")
    tmp = Path(tempfile.mkdtemp(prefix=".so_stage.", dir=str(kit)))
    try:
        r = subprocess.run([sys.executable, "-I", str(src / "signoff.py"), "bundle", str(tmp)],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300)
        if r.returncode:
            print(f"SIGNOFF_TOOL SKIPPED (bundle from {src} rc {r.returncode}: {r.stderr.strip()[-200:]}): kit copy signoff.py {old}", flush=True)
            return None
        names = []
        for f in sorted(tmp.iterdir()):
            if not f.is_file():
                continue
            t = kit / f.name
            if t.is_file() and t.read_bytes() == f.read_bytes():
                continue
            os.replace(f, t)
            names.append(f.name)
        # Legacy kits lack the generator's native nominal libraries. The
        # sign-off bundle carries their replacements in a subdirectory.
        nominal = tmp / "nomcap_libs"
        target = kit / "nomcap_libs"
        if (nominal / "MANIFEST.json").is_file() and not (kit / "nomcap" / "MANIFEST.json").is_file():
            if not target.exists() and not target.is_symlink():
                os.replace(nominal, target)
                names.append(nominal.name)
            elif target.is_dir() and not target.is_symlink():
                # Complete an interrupted copy with the manifest published last.
                for member in sorted(nominal.iterdir(), key=lambda p: (p.name == "MANIFEST.json", p.name)):
                    if not member.is_file():
                        continue
                    existing = target / member.name
                    if existing.is_file() and existing.read_bytes() == member.read_bytes():
                        continue
                    os.replace(member, existing)
                    names.append(str(existing.relative_to(kit)))
        rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S %Z"), "source": str(src), "label": label, "signoff_py": _sha(kit / "signoff.py"),
               "kit_copy_was": old, "replaced": names}
        with open(kit / "signoff_tool.jsonl", "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        print(f"SIGNOFF_TOOL {label}: signoff.py {rec['signoff_py']} (kit copy was {old}); replaced {len(names)}: {' '.join(names)}", flush=True)
        return rec
    except (OSError, subprocess.SubprocessError) as e:
        print(f"SIGNOFF_TOOL SKIPPED ({type(e).__name__}: {e}): kit copy signoff.py {old}", flush=True)
        return None
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def continue_kit(kit, runner, goal, mem, threads, run=subprocess.call, preflight=None, proof_only=False, lec=None,
                 late=True, eco_loop=late_eco, plan_dir=None, refresh=flow_refresh, so_tool=stage_signoff_tool):
    kit = Path(kit).resolve()
    started = time.time()
    prior = {str(p): (p.stat().st_mtime_ns, p.stat().st_size)
             for p in kit.glob("signoff*/signoff.json")}
    preflight = Path(preflight) if preflight else kit / "kit_preflight.py"
    if not preflight.is_file() and preflight != kit / "kit_preflight.py":
        print("KIT_PREFLIGHT FAIL: staged source tool missing", flush=True)
        return 3
    if preflight.is_file():
        # KW-FIX-44 11-10 (DIE-KV-97): this run has no plan dir, so the plan-reading contract checks (macro_pin_grid
        # ...) FAIL 'no plan contents (pass --plan-dir)'; it then overwrote KIT/preflight.json, the gen-time --plan-dir
        # verdict.  Its own receipt is kept; KIT/preflight.json stays the gen-time one.
        extra = ["--plan-dir", str(plan_dir)] if plan_dir else (
            ["--no-emit"] if (kit / "preflight.json").is_file() and "--no-emit" in preflight.read_text(errors="replace")
            else [])
        rc = run([sys.executable, str(preflight), str(kit), "--out",
                  str(kit / ("preflight_autopilot_" + str(time.time_ns()) + ".json"))] + extra)
        if rc and minimal():
            # R-MINIMAL: kit preflight (R-CAP / reach / core-tap / street) is ADVISORY -- reported, never blocks
            print(f"KIT_PREFLIGHT ADVISORY: preflight exit {rc} (R-MINIMAL: not blocking)", flush=True)
            rc = 0
        if rc:
            print("KIT_PREFLIGHT FAIL: autopilot stopped before physical runner", flush=True)
            return rc
    if not proof_only and refresh:
        t_ref = time.time()
        frc = refresh(kit, goal)
        if frc == 75:
            # FLOW-PROC-A (FABLE-FLOW-0800 e): the all-or-nothing flow refresh could not write every file (it printed the
            # KIT_FLOW_REFRESH FAIL FLOW-REFRESH-PARTIAL line, the kit is unchanged): defer the stage, never run it on mixed flow files
            print("FLOW-REFRESH-PARTIAL: stage deferred before the physical runner (autopilot class CRASH infra-flow-refresh)", flush=True)
            return 75
        alt = runner_override(kit, t_ref)
        if alt and alt != str(runner):
            print(f"KIT_FLOW_REFRESH runner override: {runner} is read-only in this job; running the refreshed copy {alt}", flush=True)
            runner = alt
    if not proof_only and so_tool and goal not in ("cts", "grt"):
        so_tool(kit)
    rc = 0 if proof_only else run(["bash", runner, str(kit), goal, str(mem), str(threads)])
    if goal in ("cts", "grt"):
        return rc
    receipt = {"started": started, "runner_exit": rc, "goal": goal,
               "verdict": "INCOMPLETE", "proof_only": proof_only, "mem_gb": mem}
    out = kit / ("autopilot_chain_" + str(time.time_ns()) + ".json")

    def done(code, verdict, reason):
        eco = receipt.get("eco") or {}
        if eco.get("summary") and verdict != "PASS":
            # the FAIL evidence names the late-ECO result (class table: "late-ECO exhausted")
            reason = f"{reason}; {eco['summary']}"
        receipt.update(verdict=verdict, reason=reason, finished=time.time())
        out.write_text(json.dumps(receipt, indent=1) + "\n")
        return code

    records = [p for p in kit.glob("signoff*/signoff.json")
               if proof_only or prior.get(str(p)) != (p.stat().st_mtime_ns, p.stat().st_size)]
    # KW-ECO-1 (OWNER 11-01 20:0x): a routed sign-off that fails only TIMING / DRV / small DRC is repaired on its own
    # routed DB (one ECO iteration on a real near miss, OWNER 11-07; eco_loop.py) BEFORE it is reported as a failure; sign-off + routed LEC unchanged.
    if records and not proof_only and rc in (0, 1) and late_eco_enabled(kit, late):
        latest = max(records, key=lambda p: p.stat().st_mtime)
        if not signed(load(latest)):
            res = eco_loop(kit, latest, runner, mem, threads, run=run) or {}
            receipt["eco"] = eco_receipt(res)
            best = res.get("best") or {}
            if res.get("verdict") == "PASS" and best.get("signoff"):
                link = kit / ("signoff_eco_" + str(time.time_ns()))
                os.symlink(Path(best["signoff"]).parent, link)
                records = [link / "signoff.json"]
                rc = 0 if signed(load(records[0])) else 1
                receipt["eco"]["signoff_link"] = str(link)
    # signoff.py returns 1 for local-PASS-needs-parent. It is a valid
    # provisional result, so prove the route while preserving WAIT-PARENT.
    pending_parent = (rc == 1 and records and
                      load(max(records, key=lambda p: p.stat().st_mtime)).get("verdict") == "LOCAL_PASS_NEEDS_PARENT")
    if rc == 1 and records and minimal() and signed(load(max(records, key=lambda p: p.stat().st_mtime))):
        # R-MINIMAL: the kit's own (frozen, legacy) signoff.py said NOT SIGNED / NEEDS_PARENT on an advisory gate
        rc, pending_parent = 0, False
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
    if not signed(physical):
        return done(1, "NOT_SIGNED", "physical signoff did not pass" + (
            " (R-MINIMAL: " + "; ".join(_profile_module().judge(physical)["reasons"]) + ")" if minimal() else ""))
    gates = signoff_gates(physical)
    receipt["gates"] = gates
    if minimal():
        j = _profile_module().judge(physical)
        receipt.update(profile="minimal", advisories=j["advisories"], achieved_period_ps=j["achieved_period_ps"],
                       legacy_verdict=physical.get("verdict"))
    bad = sorted(k for k, v in gates.items() if v != "PASS")
    if bad:
        # an older frozen kit signoff.py can say SIGNED without running a gate (AUTOPILOT-SIGNOFF-2)
        return done(1, "NOT_SIGNED", "signoff gates not PASS: " + ", ".join(f"{k}={gates[k]}" for k in bad))
    base = Path((physical.get("inputs") or {}).get("base", ""))
    netlist = base / "6_final.v"
    if minimal() and os.environ.get("OT_CHAIN_LEC", "async") != "sync":
        # R-MINIMAL: the post-route LEC is ADVISORY / async -- sign-off never waits for it.  The routed netlist is
        # recorded; the LEC report runs off the sign-off path (future_kit_lec scheduler / lec lane).
        # OT_CHAIN_LEC=sync runs it here as before but never fails the chain on it.
        receipt.update(netlist=str(netlist), routed_lec="ADVISORY_ASYNC")
        return done(0, "PASS", "physical signoff complete (R-MINIMAL: DRC 0, TT setup >= -42 ps, FF hold >= 0); "
                               "routed LEC advisory/async")
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
    if minimal():
        receipt["routed_lec"] = "ADVISORY " + str(result.get("verdict"))
        return done(0, "PASS", f"physical signoff complete; routed LEC advisory: {result.get('verdict')} exit {code}")
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
    ap.add_argument("--no-late-eco", action="store_true", help="KW-ECO-1 opt-out: no late-stage ECO loop on a NOT SIGNED route")
    ap.add_argument("--plan-dir", help="plan dir for the kit preflight's plan-reading contract checks (optional)")
    ap.add_argument("runner")
    ap.add_argument("kit")
    ap.add_argument("goal")
    ap.add_argument("mem", type=int)
    ap.add_argument("threads", type=int)
    a = ap.parse_args()
    return continue_kit(a.kit, a.runner, a.goal, a.mem, a.threads, preflight=a.preflight, proof_only=a.proof_only, lec=a.lec,
                        late=not a.no_late_eco, plan_dir=a.plan_dir)


if __name__ == "__main__":
    sys.exit(main())
