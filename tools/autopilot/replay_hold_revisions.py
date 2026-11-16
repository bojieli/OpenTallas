#!/usr/bin/env python3
"""replay_hold_revisions.py: HOLDGEN-1115 migration proof.  For every committed revision of autopilot/kit_wave.json (git repo = the coord
hub) since --since, load it the legacy way and after migrate_cfg(), and compare each die's effective hold_items (keys, order, reasons)
and the auto-released set.  Exit 1 on any difference.   usage: replay_hold_revisions.py --repo ~/coord --since 2026-11-15"""
import argparse, json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hold_records as HR  # noqa: E402
import kit_wave as KW  # noqa: E402


def effective(text, migrate, merged=lambda r: False):
    KW._git_is_merged = merged
    cfg = json.loads(text)
    cfg.setdefault("dies", {})
    if migrate:
        HR.migrate_cfg(cfg)
        text = json.dumps(cfg)
    c = KW.load_config(text)
    held = {die: list((d.get("hold_items") or {}).items()) for die, d in c["dies"].items()}
    return {k: v for k, v in held.items() if v}, sorted((a, b) for a, b, _ in c.get("_hold_auto_released") or [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--path", default="autopilot/kit_wave.json")
    ap.add_argument("--since", default="2026-11-15")
    ap.add_argument("--ref", default="HEAD")
    a = ap.parse_args()
    out = subprocess.run(["git", "-C", a.repo, "log", "--since", a.since, "--format=%H", a.ref, "--", a.path],
                         capture_output=True, text=True, check=True).stdout.split()
    bad = n = keys = 0
    for sha in reversed(out):
        r = subprocess.run(["git", "-C", a.repo, "show", f"{sha}:{a.path}"], capture_output=True, text=True)
        if r.returncode:
            continue
        try:
            json.loads(r.stdout)
        except ValueError:
            continue
        n += 1
        for merged in (lambda ref: False, lambda ref: True):          # nothing merged / everything merged: both release paths
            old, new = effective(r.stdout, False, merged), effective(r.stdout, True, merged)
            keys = max(keys, sum(len(v) for v in old[0].values()))
            if old != new:
                bad += 1
                od, nd = old[0], new[0]
                print(f"DIFF {sha[:10]}: dies old {sorted(od)} new {sorted(nd)}; "
                      + "; ".join(f"{d}: {len(od.get(d, []))} vs {len(nd.get(d, []))}" for d in sorted(set(od) | set(nd)) if od.get(d) != nd.get(d)))
    print(f"replayed {n} revisions x2 merge modes, max held keys {keys}, differences {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
