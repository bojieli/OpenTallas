#!/usr/bin/env python3
"""precheck_hook.py -- PRECHECK-1119 (c): run precheck after a plan apply, in the background, and post the family
summary to the die owner.  Started by tools/autopilot/publish_apply.py apply (systemd-run on the die's first gen
host); it never blocks, holds or gates anything (owner r703/r704).

  precheck_hook.py --die DIE --plan PLAN --tools TREE/tools/die_plan --event EV --owner LANE [--out-root DIR]
                   [--post-host intel2] [--no-post]
"""
import argparse
import collections
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
    return rc


def _sq(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"


if __name__ == "__main__":
    sys.exit(main())
