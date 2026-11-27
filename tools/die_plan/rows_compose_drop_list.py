#!/usr/bin/env python3
"""rows_compose_drop_list.py PLAN_IN PLAN_OUT REPORT.json --baseline BASE.json [--intend 'PATTERN # reason' ...]   (P-COMPOSE-DROP, QC-R3-TREERTL 11-27)

A row script: PLAN_OUT = PLAN_IN unchanged; names every path BASE carries and PLAN_IN lacks in compose_drop_list.txt beside PLAN_OUT
(the file compose_drop_guard.plan_drop_pats / the PRE COMPOSEDROP class reads).  Re-anchored relays (reset_tree_anchor inputs changed, relays
re-picked) are named with their evidence; every other drop must match an --intend pattern or the row exits 1 with the list (nothing written)."""
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compose_drop_guard as CDG  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_in")
    ap.add_argument("plan_out")
    ap.add_argument("report")
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--intend", action="append", default=[])
    ap.add_argument("--list-dir", help="tree-relative plan dir (resolved in the private fork) the list is written to; default: beside PLAN_OUT")
    a = ap.parse_args(argv)
    prev = json.loads(Path(a.baseline).read_text())
    new = json.loads(Path(a.plan_in).read_text())
    pats = CDG.load_drop_list_lines(a.intend)
    text, named, unnamed = CDG.emit_drop_list(prev, new, pats)
    rep = dict(named=len(named), unnamed=unnamed, reanchored=CDG.reanchored_types(prev, new))
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    if unnamed:
        print(f"rows_compose_drop_list: {len(unnamed)} drop(s) no pattern names: {unnamed[:6]}", file=sys.stderr)
        return 1
    # intended patterns that matched a drop are written as the explicit paths with the operator's reason
    reasons = {p: (l.split(" #", 1)[1].strip() if " #" in l else "") for l in a.intend for p in named if CDG.intended("DROP", p, CDG.load_drop_list_lines([l]))}
    lines = [ln if ln.startswith("#") else (ln if "# intended" not in ln or not reasons.get(ln.split()[1]) else f"{ln.split('  #')[0]}  # {reasons[ln.split()[1]]}")
             for ln in text.splitlines()]
    out = Path(a.plan_out)
    if Path(a.plan_in).resolve() != out.resolve():
        shutil.copyfile(a.plan_in, out)
    dest = (Path.cwd() / a.list_dir).resolve() if a.list_dir else out.parent
    (dest / "compose_drop_list.txt").write_text("\n".join(lines) + ("\n" if lines else ""))
    print(f"rows_compose_drop_list: {len(named)} drop(s) named in {dest / 'compose_drop_list.txt'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
