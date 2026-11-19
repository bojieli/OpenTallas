#!/usr/bin/env python3
"""validate.py -- PRECHECK-1119 (b): recall on the known 11-18 positives and false-positive rate on signed (counted) types.

  validate.py --runs RUN_DIR[,RUN_DIR...] --counted counted.json [--known known.json] > validation.md

known.json: {"<run tag>": {"<CHECK>": ["<type or type-prefix>", ...]}}  (prefix match).  counted.json: ["die|type", ...]
(kit_wave_state counted_blocks keys).  A signed type that a check flags is a false positive of that check (it closed).
"""
import argparse
import collections
import json
from pathlib import Path

KNOWN = {
    "s81_d8e": {"MISAIM": ["col_h9_r1__", "col_h10_r1__", "col_h10_r2__", "col_h9_r2__"],
                "FACE-BANK": ["ot_s81sl_leaf__" + t for t in ("t14", "t23", "t28", "t3", "t33", "t40__cl86ea32b3", "t40__cl86ea32b3__sid5S",
                              "t41", "t47", "t52", "t53__clb66fa5cb", "t54__cl501e5681", "t61", "t62", "t66", "t67", "t72", "t75", "t8")],
                "TAP-EDGE": ["ot_s81sl_leaf__t25__cl431c660f"], "TAP-COVER": ["ot_s81sl_leaf__t25__cl431c660f"],
                "RESET-FANOUT": ["phy__t1"]},
    "kv_d23h2": {"TAP-CAP|TAP-COVER": ["kv3_pv", "kv3_pv_v8"]},
}


def load(run):
    rows = []
    p = Path(run) / "findings.tsv"
    for ln in p.read_text().splitlines()[1:]:
        f = ln.split("\t")
        rows.append(dict(type=f[0], check=f[1], value=f[2], family=f[4]))
    return rows


def match(t, pats):
    return any(t == p or (p.endswith("__") and t.startswith(p)) for p in pats)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--counted", required=True)
    a = ap.parse_args()
    counted = json.loads(Path(a.counted).read_text())
    L = ["# PRECHECK-1119 validation", ""]
    for run in a.runs.split(","):
        tag = Path(run).name
        rows = load(run)
        rec = json.loads((Path(run) / "precheck.json").read_text())
        die = rec["die"]
        raw = json.loads(Path(rec["plan"]).read_text())
        placed = {q.get("type") for q in raw.get("partitions") or []}
        signed = {k.split("|", 1)[1] for k in counted if k.split("|", 1)[0] == die}
        by = collections.defaultdict(set)
        for r in rows:
            by[r["check"]].add(r["type"])
        flagged_any = set().union(*by.values()) if by else set()
        L.append(f"## {tag} ({die}, {rec['types']} types, {rec['findings']} findings, {rec['seconds']} s)")
        L.append("| check | types flagged | signed flagged / signed in plan | known positives found |")
        L.append("|---|---|---|---|")
        sig_plan = signed & placed
        for check in sorted(by):
            kp = []
            for kc, pats in KNOWN.get(tag, {}).items():
                if check in kc.split("|"):
                    kp = pats
            found = sum(1 for p in kp if any(match(t, [p]) for t in by[check])) if kp else None
            fp = sorted(by[check] & sig_plan)
            L.append(f"| {check} | {len(by[check])} | {len(fp)} / {len(sig_plan)} {('(' + ', '.join(fp[:4]) + ')') if fp else ''} | "
                     f"{'' if found is None else f'{found} / {len(kp)}'} |")
        for kc, pats in KNOWN.get(tag, {}).items():
            if not any(c in by for c in kc.split("|")):
                L.append(f"| {kc} | 0 | | 0 / {len(pats)} |")
        L.append("")
    print("\n".join(L))


if __name__ == "__main__":
    main()
