#!/usr/bin/env python3
"""row_ledger_check.py -- FP-CONVERGE-S81 ROW-LEDGER (FABLE-RC-S81, report-only).

  row_ledger_check.py --plan PLAN.json --ledger lanes/ROW-LEDGER-S81.tsv [--ops FILE ...] [--strict]

Ledger tsv (lanes/ROW-LEDGER-S81.tsv), header: row_file  sha256  owner  types  pre_verdict  applied_in_plan_sha
A plan does not record which rows were applied, so applied is judged BY OP CONTENT (adv_row_applied.applied: every op's value is
at its path in the plan).  A ledger row whose ops file is FULL in the plan must carry a matching sha256, owner, types and
pre_verdict; an --ops file applied in the plan but absent from the ledger is a finding.  Exit 0 unless --strict and a finding.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adv_fpconv2 as F2  # noqa: E402
import adv_row_applied as RA  # noqa: E402


def applied_files(plan, files):
    """-> {file: sha256} of ops files fully applied in the plan (by content)"""
    out = {}
    for f in files:
        try:
            ops = RA.ops_of(json.loads(Path(f).read_text()))
        except (OSError, ValueError):
            continue
        if not ops:
            continue
        n, a, _old, _miss = RA.applied(ops, plan)
        if n and a == n:
            out[str(f)] = F2.sha256_file(f)
    return out


def check(plan, ledger_path, ops_files=()):
    ledger = F2.read_ledger(ledger_path)
    files = list(ledger) + [f for f in ops_files if f not in ledger]
    app = applied_files(plan, files)
    return F2.row_ledger(app, ledger)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--plan", required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--ops", nargs="*", default=[])
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args(argv)
    out = check(json.loads(Path(a.plan).read_text()), a.ledger, a.ops)
    for x in out:
        print(x)
    print(f"ROW-LEDGER {len(out)} finding(s)")
    return 1 if (a.strict and out) else 0


if __name__ == "__main__":
    sys.exit(main())
