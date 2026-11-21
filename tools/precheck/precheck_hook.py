#!/usr/bin/env python3
"""precheck_hook.py -- PRECHECK-1119 (c): run precheck after a plan apply, in the background, and post the family
summary to the die owner.  Started by tools/autopilot/publish_apply.py apply (systemd-run on the die's first gen
host); it never blocks, holds or gates anything (owner r703/r704).

  precheck_hook.py --die DIE --plan PLAN --tools TREE/tools/die_plan --event EV --owner LANE [--out-root DIR]
                   [--post-host intel2] [--no-post] [--prev-plan P0 --prev-tools T0 --prev-event E0 --prev-kits K]
                   [--tools-sha SHA] [--no-adopt-diff] [--no-census] [--no-census-hold]

ADOPT-CENSUS-1800: after precheck the same unit runs (each posts one line; none blocks the apply)
  ABS-CENSUS   plan_geom_census.py on the new plan: hops / reset legs / core wires over 300 um, unregistered memory reads
  ADOPT-DIFF   tools/autopilot/event_adopt_diff.py on the tree: LAG / BOTH files against main, proven-fix ledger
  EVENT-CENSUS event_census.py against the previous event (--prev-plan); regressed types are not launched (kit_wave
               hold_items "EVENT-CENSUS ..." written on the hub through event_census.py hold) unless --no-census-hold
"""
import argparse
import collections
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import precheck as PC  # noqa: E402

OUT_ROOT = "/srv/opentallas-scratch2/claude/precheck-runs"


def summary_text(die, event, owner, out, findings_tsv):
    """one post: per check the families flagged, worst value and an example type"""
    rows = []
    for ln in Path(findings_tsv).read_text().splitlines()[1:]:
        f = ln.split("\t")
        if len(f) >= 6:
            rows.append(dict(type=f[0], check=f[1], value=f[2], family=f[4], detail=f[5]))
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        by[r["check"]][r["family"]].append(r)
    parts = []
    for check in [c for c in PC.CHECKS if c in by] + [c for c in by if c not in PC.CHECKS]:
        fams = sorted(by[check].items(), key=lambda kv: -len(kv[1]))
        s = "; ".join(f"{fam} {len({r['type'] for r in rs})} ({rs[0]['type']}: {rs[0]['detail'][:90]})" for fam, rs in fams[:3])
        more = f"; +{len(fams) - 3} families" if len(fams) > 3 else ""
        parts.append(f"{check}: {s}{more}")
    head = (f"PRECHECK [PRECHECK-1119 -> {owner}; cc COORD] {die} event {event}: {len(rows)} findings "
            f"({', '.join(f'{c} {sum(len(v) for v in by[c].values())}' for c in by)}). Estimator only, not a gate. "
            f"Full: {out}/family_summary.md, rows {out}/suggested_rows.json.")
    return head + ("\n" + "\n".join(parts) if parts else " No findings.")


def gather_kit_sinks(hosts, out):
    """run kit_sinks.py on each gen host (read-only grep of its kit run logs); returns the JSON files written"""
    files = []
    for h in hosts:
        f = out / f"kit_sinks_{h}.json"
        cmd = ["timeout", "300", "ssh", "-n", "-o", "ControlPath=none", h, f"cd / && python3 -I {HERE / 'kit_sinks.py'}"]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=330)
        except subprocess.TimeoutExpired:
            continue
        if r.returncode == 0 and r.stdout.strip().startswith("{"):
            f.write_text(r.stdout)
            files.append(str(f))
    return files


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--die", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--tools", required=True)
    ap.add_argument("--event", default="?")
    ap.add_argument("--owner", default="COORD")
    ap.add_argument("--out-root", default=OUT_ROOT)
    ap.add_argument("--post-host", default="intel2")
    ap.add_argument("--no-post", action="store_true")
    ap.add_argument("--kit-hosts", default="", help="gen hosts whose kit runs feed STALE-BINS (kit_sinks.py over ssh)")
    ap.add_argument("--prev-plan", default="", help="plan of the previous event (EVENT-CENSUS)")
    ap.add_argument("--prev-tools", default="")
    ap.add_argument("--prev-event", default="")
    ap.add_argument("--prev-kits", nargs="*", default=[], help="kit-wave items root(s) of the previous event on this host")
    ap.add_argument("--tools-sha", default="", help="the die's tools pin (ADOPT-DIFF ledger ancestor check)")
    ap.add_argument("--hub-rt", default=RT_HUB, help="runtime tree on the post host (event_census.py hold)")
    ap.add_argument("--no-adopt-diff", action="store_true")
    ap.add_argument("--no-census", action="store_true")
    ap.add_argument("--no-census-hold", action="store_true")
    a = ap.parse_args(argv)
    out = Path(a.out_root) / f"{a.die}_{a.event}_{time.strftime('%m%d%H%M')}"
    out.mkdir(parents=True, exist_ok=True)
    ks = gather_kit_sinks([h for h in a.kit_hosts.split(",") if h], out)
    rc = PC.main(["--die", a.die, "--plan", a.plan, "--tools", a.tools, "--out", str(out)] + (["--kit-sinks", ",".join(ks)] if ks else []))
    text = summary_text(a.die, a.event, a.owner, out, out / "findings.tsv")
    print(text)
    if not a.no_post:
        cmd = ["timeout", "600", "ssh", "-n", "-o", "ControlPath=none", a.post_host,
               "bash ~/coord/bin/post.sh PRECHECK-1119 " + _sq(text)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        print("POST", r.returncode, (r.stdout or r.stderr)[-200:])
    for name, fn in (("ABS-CENSUS", abs_census), ("ADOPT-DIFF", adopt_diff), ("EVENT-CENSUS", event_census)):
        try:
            line = fn(a, out)
        except Exception as e:  # noqa: BLE001 -- an estimator never fails the hook
            line = f"{name} {a.die} event {a.event}: not run ({type(e).__name__}: {str(e)[:200]})"
        if line:
            print(line)
            if not a.no_post:
                post_line(a, f"{line.split(' ', 1)[0]} [PRECHECK-1119 -> {a.owner}; cc COORD, ADOPT-CENSUS-1800] " + line.split(" ", 1)[1])
    return rc


RT_HUB = "/srv/opentallas-scratch2/claude/rt/current"


def post_line(a, text):
    cmd = ["timeout", "600", "ssh", "-n", "-o", "ControlPath=none", a.post_host, "bash ~/coord/bin/post.sh PRECHECK-1119 " + _sq(text[:3000])]
    return subprocess.run(cmd, capture_output=True, text=True)


def tree_of(tools):
    return Path(tools).resolve().parents[1]


def abs_census(a, out):
    import plan_geom_census as PG
    rows, info = PG.census(a.die, a.plan, a.tools, a.prev_kits)
    rec = PG.write(out / "abs_census", a.die, a.plan, rows, info, time.time())
    return rec["summary"].replace("ABS-CENSUS " + a.die, f"ABS-CENSUS {a.die} event {a.event}", 1)


def adopt_diff(a, out):
    if a.no_adopt_diff:
        return ""
    sys.path.insert(0, str(HERE.parent / "autopilot"))
    try:
        import event_adopt_diff as AD
    finally:
        sys.path.pop(0)
    o = out / "adopt_diff"
    argv = ["diff", "--tree", str(tree_of(a.tools)), "--die", a.die, "--plan", a.plan, "--plan-tools", a.tools, "--out", str(o), "--fetch"]
    if a.tools_sha:
        argv += ["--tools-sha", a.tools_sha]
    if AD.main(argv) != 0:
        return f"ADOPT-DIFF {a.die} event {a.event}: not run (see {o})"
    rep = json.loads((o / "adopt_diff.json").read_text())
    return rep["summary"].replace("ADOPT-DIFF ", f"ADOPT-DIFF event {a.event} ", 1) + f" Rows {o}/adopt_diff.tsv, ledger {o}/ledger.tsv"


def event_census(a, out):
    if a.no_census or not a.prev_plan or a.prev_plan == a.plan:
        return ""
    import event_census as EC
    o = out / "event_census"
    argv = ["run", "--die", a.die, "--prev-plan", a.prev_plan, "--new-plan", a.plan, "--new-tools", a.tools, "--event", a.event, "--out", str(o)]
    if a.prev_tools:
        argv += ["--prev-tools", a.prev_tools]
    if a.prev_kits:
        argv += ["--prev-kits", *a.prev_kits]
    EC.main(argv)
    rec = json.loads((o / "census.json").read_text())
    line = EC.summary(rec, o) + f" (previous event {a.prev_event or '?'})"
    if rec.get("held") and not a.no_census_hold:
        cmd = ["timeout", "900", "ssh", "-o", "ControlPath=none", a.post_host,
               f"cd / && python3 -I {a.hub_rt}/tools/precheck/event_census.py hold --die {a.die} --census - --event {_sq(a.event)} --lane PRECHECK-1119"]
        r = subprocess.run(cmd, input=json.dumps(rec), capture_output=True, text=True)
        line += f"; not launched: {len(rec['held'])} type(s) held (rc {r.returncode}); the event applies"
    elif rec.get("held"):
        line += "; --no-census-hold: reported only"
    return line


def _sq(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"


if __name__ == "__main__":
    sys.exit(main())
