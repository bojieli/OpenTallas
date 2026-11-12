#!/usr/bin/env python3
"""path_respace as a composer stage (DIE-S81-87 contract):   path_respace_stage.py IN OUT REPORT [--sidecar-in SC --sidecar-out SC2]

IN  = die plan json (json or .gz), OUT = the plan with path_respace applied, REPORT = path_respace_report.json (+ the stage's
declared key list).  The stage edits ONLY these keys (it fails closed otherwise):
  partition_types.*.ft_slots[*].regs_um / stations / bit_sites_um
  partition_types.*.internal_stations[*].regs_um
  partition_types.*.clock.landing_contract.collector_tree.relays[*].xy
  latency.lanes.<lane>            (only lanes through a slot whose station count changed; +1-cycle lanes are listed with groups)
--sidecar-in/-out: the landed sidecar; collector.types[<type>].tree of every type whose plan collector_tree changed is
republished to the new plan tree (refused, listed, when the sidecar tree differed from the plan's old one).
Options: --no-collectors (leave relay sites alone), --no-add.
"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import path_respace as PR  # noqa: E402

DECLARED = [
    r"partition_types/[^/]+/ft_slots/\d+/(regs_um|stations|bit_sites_um)(/.*)?",
    r"partition_types/[^/]+/internal_stations/\d+/regs_um(/.*)?",
    r"partition_types/[^/]+/clock/landing_contract/collector_tree/relays/\d+/xy(/.*)?",
    r"latency/lanes/[^/]+(/.*)?",
]


def diff_paths(a, b, path=""):
    if type(a) != type(b):
        yield path
    elif isinstance(a, dict):
        for k in set(a) | set(b):
            if k not in a or k not in b:
                yield f"{path}/{k}"
            else:
                yield from diff_paths(a[k], b[k], f"{path}/{k}")
    elif isinstance(a, list):
        if len(a) != len(b):
            yield path
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                yield from diff_paths(x, y, f"{path}/{i}")
    elif a != b:
        yield path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("report")
    ap.add_argument("--sidecar-in")
    ap.add_argument("--sidecar-out")
    ap.add_argument("--no-collectors", action="store_true")
    ap.add_argument("--no-add", action="store_true")
    ap.add_argument("--limit", type=float, default=405.0)
    a = ap.parse_args(argv)
    raw = PR._load(a.inp)
    raw2, ops, rep = PR.run(copy.deepcopy(raw), a.limit, not a.no_add, collectors=not a.no_collectors)
    bad = sorted({p for p in diff_paths(raw, raw2) if not any(re.fullmatch(d, p.lstrip("/")) for d in DECLARED)})
    if bad:
        print("stage touched undeclared keys:", bad[:10], file=sys.stderr)
        return 2
    side_rep = None
    if a.sidecar_in:
        side = json.loads(Path(a.sidecar_in).read_text())
        types = (side.get("collector") or {}).get("types") or {}
        done, refused = [], []
        for c in rep["collector_chains"]:
            tn = c["type"]
            old = raw["partition_types"][tn]["clock"]["landing_contract"]["collector_tree"]
            st = types.get(tn)
            if st is None:
                refused.append(dict(type=tn, why="no sidecar collector entry"))
                continue
            if json.loads(json.dumps(st.get("tree"), sort_keys=True)) != json.loads(json.dumps(old, sort_keys=True)):
                refused.append(dict(type=tn, why="sidecar collector tree differs from the plan's old collector_tree"))
                continue
            st["tree"] = copy.deepcopy(raw2["partition_types"][tn]["clock"]["landing_contract"]["collector_tree"])
            done.append(tn)
        side_rep = dict(republished=done, refused=refused)
        if done:
            Path(a.sidecar_out).write_text(json.dumps(side) + "\n")
        else:                                  # nothing republished: the sidecar is passed through byte for byte
            Path(a.sidecar_out).write_bytes(Path(a.sidecar_in).read_bytes())
    rep["declared_keys"] = DECLARED
    rep["sidecar"] = side_rep
    Path(a.out).write_text(json.dumps(raw2) + "\n")
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(dict(rep["summary"], sidecar=side_rep)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
