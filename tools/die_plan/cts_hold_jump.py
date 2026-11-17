#!/usr/bin/env python3
"""cts_hold_jump.py -- report the CTS hold-buffer count against the kit's previous form before detail route
(CLOSURE-STRATEGY-2100 lever 4, HOLD-FLOW-R 11-16).

QC headseg44 put 16,494 hold BUFx2 at CTS and nobody saw it until detail route sat at 900-1,200 violations for hours.  The
count is in the CTS log ("[INFO RSZ-0032] Inserted N hold buffers."); this report sums it for the current and the previous form
and flags a jump of FACTOR (default 2) or more.  Advisory: it never fails a build unless --strict.

    cts_hold_jump.py CUR_4_1_cts.log PREV_4_1_cts.log [--factor 2] [--min 200] [--out report.json] [--strict]

PREV may also be a JSON file written by this tool (its "current" count is then the previous count).  A previous count of 0
or an unreadable previous form is reported as NO_BASELINE (no flag).  --min keeps a 3 -> 9 jump on a tiny kit quiet.
Exit: 0 (report), 3 with --strict and a flag.
"""
import argparse
import json
import re
import sys
from pathlib import Path

INSERTED = re.compile(r"Inserted\s+([0-9][0-9,]*)\s+hold\s+buffers?", re.I)


def count_hold_buffers(text):
    return sum(int(m.group(1).replace(",", "")) for m in INSERTED.finditer(text))


def previous_count(path):
    p = Path(path)
    if not p.is_file():
        return None
    txt = p.read_text(errors="replace")
    if p.suffix == ".json":
        try:
            d = json.loads(txt)
            return int(d["current"])
        except (ValueError, KeyError, TypeError):
            return None
    return count_hold_buffers(txt)


def compare(cur, prev, factor=2.0, floor=200):
    if prev is None or prev <= 0:
        return dict(current=cur, previous=prev, ratio=None, verdict="NO_BASELINE", flag=False)
    ratio = cur / prev
    flag = ratio >= factor and cur >= floor
    return dict(current=cur, previous=prev, ratio=round(ratio, 3), verdict="JUMP" if flag else "OK", flag=flag,
                factor=factor, floor=floor)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cur")
    ap.add_argument("prev")
    ap.add_argument("--factor", type=float, default=2.0)
    ap.add_argument("--min", type=int, default=200, dest="floor")
    ap.add_argument("--out")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args(argv)
    cur = count_hold_buffers(Path(a.cur).read_text(errors="replace"))
    rec = compare(cur, previous_count(a.prev), a.factor, a.floor)
    if a.out:
        Path(a.out).write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print("OT_CTS_HOLD_JUMP " + json.dumps(rec, sort_keys=True))
    if rec["flag"]:
        print(f"OT_CTS_HOLD_JUMP FLAG: {cur} CTS hold buffers vs {rec['previous']} in the previous form ({rec['ratio']}x >= {a.factor:g}x): "
              "read the CTS hold scope / margin before spending detail route")
    return 3 if (a.strict and rec["flag"]) else 0


if __name__ == "__main__":
    sys.exit(main())
