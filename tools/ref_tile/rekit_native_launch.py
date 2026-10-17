#!/usr/bin/env python3
"""Re-kit a CLOSED view that fails the native launch budget with the recipe-2 output stage (one command per view).

Why (el1014-root-macro-edge, 2026-10-14): the native pin audit (results/arch/native_pin_audit_1014, TT launch O - R <=
220 ps at phi - R) fails many CLOSED views because their kits predate the recipe-2 output stage of main 36de4b87f:
recipe-1 kits have no pin flop / pin pad stage at all, and early recipe-2 kits put BUF + HB4 + BUF (~120 ps TT) on every
output and let synthesis merge equal pin registers into one flop driving several pins.  The fix is the same block re-kitted:
the SAME RTL (blobs at the closed job's commit), the SAME outline and pin faces (the closed kit's floorplan), only the
generator's recipe-2 pin defaults applied (io_flop_at_pins + inhold/outhold through the kit-local pre_gpl.tcl,
pin_reg_split = one dedicated launch flop per output pin, hold_pad HB2xp67, keep_pin_regs).  The job carries
"reroute_reason": {"kind": "native_launch", ...}, which the closure loop's CLOSED_STANDS gate verifies (same RTL, same
FW/FH/PINS, recipe-2 output stage present in the new kit and absent from the closed one).

    rekit_native_launch.py list [--design qwen|s81|hbm|other] [--cell-only] [--post]
        every die-used CLOSED view of the audit that fails launch, with its closed job, kit recipe, whether a re-kit fixes
        it (or why not: RTL changed since the closed commit, the spec owns the PRE_GLOBAL_PLACE hooks, no spec.json, a
        live job of the block) and the one command.  --post writes one line per view into the owning stream log and a
        per-design summary into the die lead's log.
    rekit_native_launch.py rekit TARGET [TARGET ...] [--gate none|local|remote] [--submit]
        TARGET = view path, cell, kit dir or closed job name.  Writes the kit physical/ref_tile/<kit>/ in this checkout
        (same kit dir: the new view replaces the old one in place once CLOSED), runs the pre-route gate (default local;
        remote = synthesis smoke on the fleet, writes gate_result.json).  --submit (implies --gate remote): commit the kit
        by path, push to origin main, write job.json at that commit, commit + push it, drop it into the loop intake.

Nothing is routed by this tool; the loop routes the submitted job.  A view whose RTL changed since its closed commit is
NOT re-kitted (that is an rtl_change re-route the owner decides).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "hier_contract"))
import ref_tile as RT  # noqa: E402

AUDIT = "results/arch/native_pin_audit_1014"
DESIGNS = ("qwen", "s81", "hbm", "other")
LAUNCH_MAX_PS = 220.0
JOBS = Path(os.environ.get("CL_STATE", str(Path.home() / ".local/state/closure_loop"))) / "jobs"
INTAKE = Path(os.environ.get("CL_INTAKE", "/tmp/claude-review-20261003/closure_jobs"))
TAKE = Path(os.environ.get("CL_TAKEOVER", "/home/ubuntu/claude-takeover-20261007"))
DIE_LOG = {"qwen": "el1011-qwen-tp8.log", "s81": "el1011-s81die.log", "hbm": "el1011-hbmdie.log"}
KIT_RE = re.compile(r"ref_route\.sh\s+(\S+)/kit\.env")
TERMINAL = re.compile(r"^(CLOSED|CANCELLED|NEEDS_RTL|NEEDS_HUMAN|EARLY_FAIL_\w+|FLOORPLAN_MARGIN|PREROUTE_MARGIN|REFUSED|INVALID|SMOKE_OK|FAILED)$")
TAG = "nl"
FIX = ("kit re-generated at the closed RTL / outline / pin faces with the recipe-2 output stage (main 36de4b87f): one "
       "dedicated launch flop per output pin FIRM at its pin (pin_reg_split + io_flop_at_pins), HB2xp67 pin pad instead "
       "of BUF+HB4+BUF, top-level pin registers kept through synthesis")


def git(*a, check=True) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True, check=check).stdout


def show(commit: str, path: str) -> str | None:
    r = subprocess.run(["git", "-C", str(ROOT), "show", f"{commit}:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def blob(commit: str, path: str) -> str | None:
    r = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "-q", "--verify", f"{commit}:{path}"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def audit_rows(design: str, audit: str = AUDIT) -> list:
    p = ROOT / audit / f"{design}.json"
    text = p.read_text() if p.is_file() else show("origin/main", f"{audit}/{design}.json")
    return json.loads(text)["views"] if text else []


def failing(designs=DESIGNS, cell_only=False, audit=AUDIT) -> list:
    """die-used (contract "yes", and with --cell-only also "cell": the lib cell is used under another slot) CLOSED views
    over the launch budget, worst first per design"""
    want = ("yes", "cell") if cell_only else ("yes",)
    out = []
    for d in designs:
        rows = [dict(r, design=d) for r in audit_rows(d, audit)
                if r.get("used") in want and isinstance(r.get("launch_ps"), (int, float)) and r["launch_ps"] > LAUNCH_MAX_PS]
        out += sorted(rows, key=lambda r: -r["launch_ps"])
    return out


def job_state(name: str | None) -> dict | None:
    if not name:
        return None
    p = JOBS / f"{name}.json"
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def kit_of_job(j: dict | None) -> str | None:
    m = KIT_RE.search((((j or {}).get("spec") or {}).get("stages") or {}).get("route", {}).get("cmd") or "")
    return m.group(1) if m else None


def find_row(target: str, audit=AUDIT) -> dict | None:
    t = target.rstrip("/")
    for r in failing(DESIGNS, True, audit) + [dict(x, design=d) for d in DESIGNS for x in audit_rows(d, audit)]:
        if t in (r.get("view"), r.get("cell"), r.get("job"), r.get("view", "").split("/views/")[0]):
            return r
    return None


def live_jobs_of(block: str) -> list:
    """jobs of the block the loop is still working on, and intake specs it has not ingested yet (the intake directory
    keeps every spec it ever ingested: those are not pending)"""
    out = []
    for p in JOBS.glob("*.json"):
        try:
            j = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        if (j.get("spec") or {}).get("block") == block and not TERMINAL.match(str(j.get("status"))):
            out.append(p.stem)
    for p in INTAKE.glob("*.json"):
        try:
            j = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        if j.get("block") == block and not (JOBS / f"{j.get('name', p.stem)}.json").exists() \
                and not (JOBS / p.name).exists():
            out.append(f"{j.get('name', p.stem)} (intake)")
    return out


def assess(row: dict, check_live=True) -> dict:
    """everything needed to re-kit one audited view, without writing anything.  verdict: REKIT | SKIP (+ why)"""
    a = {"cell": row["cell"], "design": row["design"], "view": row["view"], "launch_ps": row["launch_ps"],
         "launch_over": row.get("launch_over"), "capture_ps": row.get("capture_ps"), "job": row.get("job"),
         "verdict": "SKIP"}
    kd = row["view"].split("/views/")[0]
    j = job_state(row.get("job"))
    a["kit"] = kit_of_job(j) or kd
    a["owner"] = ((j or {}).get("spec") or {}).get("owner")
    a["status"] = (j or {}).get("status")
    commit = (j or {}).get("commit_full") or (((j or {}).get("spec") or {}).get("source") or {}).get("commit")
    if not j:
        a["why"] = f"no closure-loop record of {row.get('job') or 'the view'} (closed outside the loop: re-kit by hand)"
        return a
    if j.get("status") != "CLOSED":
        a["why"] = f"closed job {row['job']} is {j.get('status')}"
        return a
    a["commit"] = commit
    raw = show(commit, f"{a['kit']}/spec.json")
    if raw is None:
        a["why"] = f"no {a['kit']}/spec.json at the closed commit {str(commit)[:9]} (not a ref_tile kit)"
        return a
    s = json.loads(raw)
    env = show(commit, f"{a['kit']}/kit.env") or ""
    m = re.search(r"^RECIPE=(\d+)", env, re.M)
    a["recipe"] = int(m.group(1)) if m else 1
    if "pin_reg_split.tcl" in (show(commit, f"{a['kit']}/pre_gpl.tcl") or ""):
        a["why"] = "the closed kit already has the recipe-2 output stage: the launch miss has another cause"
        return a
    own = [k for k in RT.RECIPE_OWN_HOOK_VARS if k in s.get("orfs_vars", {})]
    if own:
        a["why"] = (f"the spec owns {', '.join(own)} (its own boundary placement): recipe 2 adds no pin stage on top; "
                    f"the owner moves that hook into \"pin_hook_before_flops\" and drops the orfs_var")
        return a
    if s.get("io_flop_at_pins") is False or (s.get("inhold") is False and s.get("outhold") is False):
        a["why"] = "the spec switches the recipe-2 pin stage off explicitly (io_flop_at_pins / inhold / outhold false)"
        return a
    # the same RTL: every file the kit synthesises, and every macro / child view it instantiates
    paths = list(s["sources"]) + [s[k] for k in ("io_tcl", "post_synth_tcl") if s.get(k)]
    for it in s.get("macros", []) + s.get("children", []):
        v = it["view"]
        paths.append(f"{v}/{RT.view_name(v)}.lef")
    drift = [p for p in paths if blob(commit, p) != blob("HEAD", p)]
    if drift:
        a["why"] = (f"{len(drift)} of {len(paths)} RTL / view file(s) changed since the closed commit {commit[:9]} "
                    f"({', '.join(drift[:3])}): not a re-kit of the closed block (rtl_change is the owner's call)")
        a["drift"] = drift
        return a
    if check_live:
        live = live_jobs_of(j["spec"]["block"])
        if live:
            a["why"] = f"live / pending job(s) of {j['spec']['block']}: {', '.join(live[:3])}"
            return a
    a["spec"] = s
    a["verdict"] = "REKIT"
    return a


def new_spec(a: dict, audit=AUDIT) -> dict:
    """the closed kit's spec with the recipe-2 output stage, the closed outline pinned, the native_launch reason"""
    s = json.loads(json.dumps(a["spec"]))
    s["recipe"] = RT.RECIPE_LATEST
    if RT.RECIPE_LATEST >= 4 and s.get("kind") == "tile" and s.get("hold_budget", "die") == "die":
        # recipe 4 (FLOW-HOLD): flop-first pins, boundary hold is the die's -- the closed kit's explicit pin pads go
        for k in ("inhold", "outhold", "hold_pad", "inhold_drv"):
            s.pop(k, None)
    if a["recipe"] < 2:
        # a recipe-1 kit keeps its routed geometry and hold settings; only the output / input pin stage is new
        s["route"].setdefault("macro_halo_um", RT.HALO_UM)
        s["route"].setdefault("hold_margin_ns", 0.010)
    if not RT.contract_slot(s):
        fp = json.loads(show(a["commit"], f"{a['kit']}/floorplan.json") or "{}")
        die = fp.get("die")
        if die:
            s["outline"] = {"w": float(die[2]), "h": float(die[3]), "exact": True}
    j = s.setdefault("job", {})
    n = 1
    while list(JOBS.glob(f"{s['name']}-{TAG}{n}-*.json")) or list(INTAKE.glob(f"{s['name']}-{TAG}{n}-*.json")):
        n += 1
    j["tag"] = f"{TAG}{n}"
    j["branch"] = "main"
    j["purpose"] = (f"native launch re-kit of CLOSED {a['job']} ({a['cell']}: TT launch {a['launch_ps']} ps > "
                    f"{LAUNCH_MAX_PS:.0f} on {a.get('launch_over')} outputs at phi - R, {audit}/{a['design']}.json); same "
                    f"RTL, outline and pin faces; recipe-2 output stage")
    j.pop("reroute_reason", None)
    s.pop("reroute_reason", None)
    s["reroute_reason"] = {"kind": "native_launch", "source": f"{audit}/{a['design']}.json", "cell": a["cell"],
                           "launch_ps": a["launch_ps"], "capture_ps": a.get("capture_ps"),
                           "launch_over": a.get("launch_over"), "closed_job": a["job"], "fix": FIX}
    s["structural_change"] = ("recipe-2 output stage (one launch flop per output pin at the pin, HB2 pad, pin registers "
                              f"kept) on the closed RTL / outline of {a['job']}: TT launch {a['launch_ps']} ps > "
                              f"{LAUNCH_MAX_PS:.0f}")
    j.pop("structural_change", None)
    return s


def output_stage_ok(s: dict) -> str | None:
    """None when the regenerated spec carries the full output stage, else what is missing.  Recipe 4 (FLOW-HOLD
    hold_budget die): flop-first pins -- io_flop_at_pins + kept pin registers, no pin pads.  Otherwise recipe 2."""
    if s.get("hold_budget") == "die":
        miss = [k for k, ok in (("io_flop_at_pins", s.get("io_flop_at_pins")), ("keep_pin_regs", s.get("keep_pin_regs")),
                                ("no pin pads", not (s.get("inhold") or s.get("outhold")))) if not ok]
        return ", ".join(miss) or None
    miss = [k for k, ok in (("recipe 2 pin hook (io_flop_at_pins + inhold/outhold)", RT.pin_hook_wrapper(s)),
                            ("pin_reg_split", s.get("pin_reg_split")), ("keep_pin_regs", s.get("keep_pin_regs")),
                            ("hold_pad HB2", (s.get("hold_pad") or {}).get("cell", RT.RECIPE_HOLD_PAD) == RT.RECIPE_HOLD_PAD
                             or not (s.get("inhold") or s.get("outhold"))))
            if not ok]
    return ", ".join(miss) or None


LEGACY_FILE = HERE / "legacy_layer_kits.json"


def keep_closed_layers(s: dict) -> str | None:
    """a closed kit generated before the 2026-10-12 M5 cut with pg_layer M6/M7 but not frozen in legacy_layer_kits.json
    cannot be regenerated at all (layer contract: NEW tiles cap at M5).  A native-launch re-kit is the SAME tile: it keeps
    the closed layer contract, so the kit is frozen as legacy (written to the json, read by every later regeneration --
    the loop's submit gate re-generates the kit at its commit)."""
    pg = s.get("pg_layer")
    if s["kind"] != "tile" or pg in (None, "M5") or s.get("layer_cap") or s["name"] in RT.LEGACY_KITS:
        return None
    d = json.loads(LEGACY_FILE.read_text())
    d["kits"][s["name"]] = pg
    d["kits"] = dict(sorted(d["kits"].items()))
    LEGACY_FILE.write_text(json.dumps(d, indent=1) + "\n")
    RT.LEGACY_KITS[s["name"]] = pg
    return f"kit frozen at its closed layer contract (PG {pg}) in {LEGACY_FILE.relative_to(ROOT)}"


DAEMON = Path(os.environ.get("CL_DAEMON_TREE", "/home/ubuntu/wt-claude-closure-daemon-1010"))


def sync_daemon_legacy():
    """the loop's submit gate regenerates the kit with the daemon tree's ref_tile.py, which reads ITS
    legacy_layer_kits.json: copy ours there when it only adds entries (a daemon-only edit is never overwritten)"""
    dst = DAEMON / "tools/ref_tile/legacy_layer_kits.json"
    try:
        mine, theirs = json.loads(LEGACY_FILE.read_text()), json.loads(dst.read_text())
    except (OSError, ValueError):
        return
    if theirs["kits"] != mine["kits"] and all(mine["kits"].get(k) == v for k, v in theirs["kits"].items()):
        dst.write_text(LEGACY_FILE.read_text())
        print(f"REKIT: synced {LEGACY_FILE.name} to the closure daemon tree")


def write_kit(a: dict, audit=AUDIT) -> dict:
    s = new_spec(a, audit)
    note = keep_closed_layers(s)
    with tempfile.TemporaryDirectory() as td:
        sp = Path(td) / f"{s['name']}.json"
        sp.write_text(json.dumps(s, indent=1) + "\n")
        dry = RT.gen(str(sp), write=False)
        chk = RT.load_spec(str(sp))
        RT.apply_recipe(chk, RT.kit_recipe(chk, None, str(sp)))
        miss = output_stage_ok(chk)
        if miss:
            return {"ok": False, "why": f"regenerated spec lacks {miss}"}
        fails = [f for f in dry["findings"] if f[0] == "FAIL"]
        if fails:
            return {"ok": False, "why": "floorplan at the closed outline: " + "; ".join(str(f[2]) for f in fails)[:400]}
        old = dry["outline"]
        r = RT.gen(str(sp))
    return {"ok": True, "kit": r["kit"], "outline": old, "job": r["job"], "note": note}


def gate(kd: str, mode: str, mem: int = 24) -> tuple[str, str]:
    if mode == "none":
        return "SKIPPED", ""
    cmd = [sys.executable, str(HERE / "pre_route_gate.py"), kd] + (["--remote", "auto", "--mem", str(mem)]
                                                                   if mode == "remote" else [])
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=4 * 3600)
    m = re.search(r"PRE_ROUTE_GATE:\s*(\w+)", r.stdout)
    fails = [ln for ln in r.stdout.splitlines() if ln.startswith("GATE FAIL")]
    return (m.group(1) if m else "ERROR"), ("; ".join(fails)[:600] or r.stdout[-300:])


def push_main():
    for _ in range(3):
        git("fetch", "-q", "origin", "main")
        if subprocess.run(["git", "-C", str(ROOT), "rebase", "-q", "origin/main"], capture_output=True).returncode:
            subprocess.run(["git", "-C", str(ROOT), "rebase", "--abort"], capture_output=True)
            raise SystemExit("rekit: rebase onto origin/main failed; resolve by hand")
        if subprocess.run(["git", "-C", str(ROOT), "push", "-q", "origin", "HEAD:main"], capture_output=True).returncode == 0:
            return git("rev-parse", "HEAD").strip()
    raise SystemExit("rekit: push to origin main failed three times")


def owner_log(owner: str | None, design: str) -> Path:
    m = re.search(r"(el10\d\d-[A-Za-z0-9_.-]+)", owner or "")
    if m and (TAKE / f"{m.group(1)}.log").exists():
        return TAKE / f"{m.group(1)}.log"
    return TAKE / DIE_LOG.get(design, "el1014-root-macro-edge.log")


def post(path: Path, line: str):
    stamp = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    with open(path, "a") as f:
        f.write(f"{stamp} [native-launch re-kit] {line}\n")


def command(a: dict) -> str:
    return f"python3 tools/ref_tile/rekit_native_launch.py rekit {a['view']} --submit"


def cmd_list(args) -> int:
    rows = failing(args.design or DESIGNS, args.cell_only, args.audit)
    res = [assess(r) for r in rows]
    by = {}
    for a in res:
        by.setdefault(a["design"], []).append(a)
        line = (f"{a['design']:5} {a['verdict']:5} {a['cell']:34} launch {a['launch_ps']:6.1f} ps ({a.get('launch_over')} "
                f"out) recipe {a.get('recipe', '-')} job {a['job']}" + (f"  -> {command(a)}" if a["verdict"] == "REKIT"
                                                                       else f"  ({a.get('why')})"))
        print(line)
    if args.json:
        Path(args.json).write_text(json.dumps([{k: v for k, v in a.items() if k != "spec"} for a in res], indent=1) + "\n")
    if args.post:
        for a in res:
            msg = (f"{a['cell']} ({a['view']}) CLOSED {a['job']} fails the native launch budget: TT launch "
                   f"{a['launch_ps']} ps > 220 on {a.get('launch_over')} outputs ({args.audit}/{a['design']}.json). ")
            msg += (f"Re-kit with the recipe-2 output stage (same RTL / outline / pins, reroute_reason native_launch): "
                    f"`{command(a)}`" if a["verdict"] == "REKIT" else f"NOT re-kittable as is: {a.get('why')}")
            post(owner_log(a.get("owner"), a["design"]), msg)
        for d, xs in by.items():
            if d in DIE_LOG:
                k = [x["cell"] for x in xs if x["verdict"] == "REKIT"]
                post(TAKE / DIE_LOG[d], f"{d}: {len(xs)} die-used CLOSED views fail TT launch > 220 ps; {len(k)} re-kittable "
                                        f"by one command (tools/ref_tile/rekit_native_launch.py list --design {d}): "
                                        f"{', '.join(k) or '-'}; the rest need the owner (RTL drift / own hooks).")
    return 0


def cmd_rekit(args) -> int:
    rc = 0
    gate_mode = "remote" if args.submit else args.gate
    done = []
    for t in args.targets:
        row = find_row(t, args.audit)
        if not row:
            print(f"REKIT {t}: not in the native pin audit {args.audit}")
            rc = 1
            continue
        a = assess(row)
        if a["verdict"] != "REKIT":
            print(f"REKIT {a['cell']}: SKIP ({a.get('why')})")
            rc = 1
            continue
        w = write_kit(a, args.audit)
        if not w["ok"]:
            print(f"REKIT {a['cell']}: kit NOT written: {w['why']}")
            rc = 1
            continue
        v, why = gate(w["kit"], gate_mode, args.mem)
        print(f"REKIT {a['cell']}: kit {w['kit']} (closed {a['job']}, outline {w['outline'][0]} x {w['outline'][1]}"
              + (f"; {w['note']}" if w.get("note") else "") + f") pre-route gate {v}" + (f": {why}" if v not in ("PASS", "WARN", "SKIPPED") else ""))
        if v in ("PASS", "WARN"):
            done.append((a, w))
        elif v != "SKIPPED":
            rc = 1
    if not args.submit or not done:
        return rc
    kits = [w["kit"] for _, w in done]
    git("add", "--", *kits, str(LEGACY_FILE.relative_to(ROOT)))
    git("commit", "-q", "-m", f"native launch re-kit: {len(done)} CLOSED view(s) with the recipe-2 output stage "
        f"({', '.join(a['cell'] for a, _ in done[:10])}); same RTL / outline / pins, reroute_reason native_launch\n\n"
        f"Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    c1 = push_main()[:9]
    for a, w in done:
        sp = ROOT / w["kit"] / "spec.json"
        subprocess.run([sys.executable, str(HERE / "ref_tile.py"), "job", str(sp), "--commit", c1], cwd=ROOT, check=True,
                       capture_output=True)
    git("add", "--", *[f"{k}/job.json" for k in kits])
    git("commit", "-q", "-m", f"native launch re-kit: job specs at {c1}\n\nCo-Authored-By: Claude Opus 5.5 "
        f"<noreply@anthropic.com>")
    push_main()
    sync_daemon_legacy()
    INTAKE.mkdir(parents=True, exist_ok=True)
    for a, w in done:
        job = json.loads((ROOT / w["kit"] / "job.json").read_text())
        (INTAKE / f"{job['name']}.json").write_text(json.dumps(job, indent=1) + "\n")
        print(f"REKIT {a['cell']}: SUBMITTED {job['name']}")
        post(owner_log(a.get("owner"), a["design"]), f"{a['cell']}: native launch re-kit SUBMITTED {job['name']} "
                                                     f"(kit {w['kit']} @ {c1}, closed {a['job']} stands until it closes)")
    return rc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--audit", default=AUDIT)
    sub = ap.add_subparsers(dest="cmd", required=True)
    li = sub.add_parser("list")
    li.add_argument("--design", action="append", choices=DESIGNS)
    li.add_argument("--cell-only", action="store_true", help="also views whose lib cell is used under another slot")
    li.add_argument("--post", action="store_true")
    li.add_argument("--json")
    rk = sub.add_parser("rekit")
    rk.add_argument("targets", nargs="+")
    rk.add_argument("--gate", choices=("none", "local", "remote"), default="local")
    rk.add_argument("--mem", type=int, default=24)
    rk.add_argument("--submit", action="store_true")
    a = ap.parse_args(argv)
    return cmd_list(a) if a.cmd == "list" else cmd_rekit(a)


if __name__ == "__main__":
    sys.exit(main())
