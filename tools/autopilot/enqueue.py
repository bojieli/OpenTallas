#!/usr/bin/env python3
"""enqueue.py -- append one validated kit row to the AUTOPILOT queue (coord/state autopilot/queue.tsv) and commit it.

    python3 enqueue.py --die s81 --type slice_station__t5 --kit epyc2:/srv/opentallas-scratch2/claude/<lane>/.../<kit> \
        --src claude/<branch>@<sha> --geom PASS --geom-ref "GEOM-REVIEW 2026-10-25 03:33 <record>" \
        --mem 24 --cells 120000 --lane S81 [--goal route|finish] [--runner /abs/run_kit.sh] [--threads 8]
        [--mode submit|adopt] [--no-commit]

mode submit (default): the autopilot launches the kit through ot-run once it carries a GEOM PASS.  The kit is fresh or
  placed (the GEOM review is done on 3_place): run_kit.sh continues in its run dir.  A kit that already routed, signed
  off or carries FAIL_PREFLOOR/FAIL_POSTCTS is refused (enqueue a fresh kit).
  --geom PASS|PASS-COND --geom-ref "<record>"  : submitted on the next tick.
  --geom REQ --geom-ref "<GEOM REQ tag>"       : waits; the tick reads lanes/GEOM-REVIEW.md and submits within one tick
                                                 of a REPLY/VERDICT [<tag>] that names the kit (type, __suffix or sha)
                                                 with PASS/PASS-COND (mixed/unclear verdicts never submit).
mode adopt: the lane already launched the run by hand; the autopilot only watches it (hub ot-run client + containers +
  logs), then classifies, archives SIGNED / renders + records failures, and deletes failed data.
--mem is the honest ot-run admission (peak of a comparable run + margin); --cells the expected std cells (<= 400000).
Commit = ~/coord/bin/coord-commit.sh (serialised push).
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import autopilot as AP  # noqa: E402

COORD = Path(os.environ.get("AP_COORD", str(Path.home() / "coord")))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("die", "type", "kit", "src", "geom", "geom-ref", "mem", "cells", "lane"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--goal", default="")
    ap.add_argument("--runner", default="")
    ap.add_argument("--threads", default="")
    ap.add_argument("--mode", default="", choices=["", "submit", "adopt"])
    ap.add_argument("--no-commit", action="store_true")
    a = ap.parse_args(argv)
    row = [a.die, a.type, a.kit, a.src, a.geom, a.geom_ref, a.mem, a.cells, a.lane, a.goal, a.runner, a.threads, a.mode]
    if any("\t" in x or "\n" in x for x in row):
        sys.exit("enqueue: no tabs/newlines in fields")
    line = "\t".join(row).rstrip("\t")
    (r,) = AP.parse_queue(line).values()
    if r["error"]:
        sys.exit(f"enqueue: REFUSED: {r['error']}")
    if r["geom"].upper() not in AP.GEOM_OK and r["mode"] != "adopt":
        print(f"enqueue: NOTE geom '{r['geom']}' is not PASS: the row waits for a GEOM-REVIEW verdict of tag "
              f"'{AP.geom_tag(r['geom_ref'])}' naming {r['type']} (or a PASS row appended later)")
    q = COORD / "autopilot" / "queue.tsv"
    q.parent.mkdir(parents=True, exist_ok=True)
    new = not q.exists()
    with open(q, "a") as f:
        if new:
            f.write("# AUTOPILOT queue (tools/autopilot/autopilot.py): " + "\t".join(AP.QCOLS) + "\n")
        f.write(line + "\n")
    print(f"enqueue: id {r['id']} -> {q}")
    if not a.no_commit:
        subprocess.run([str(COORD / "bin" / "coord-commit.sh"), f"AUTOPILOT enqueue {a.die}/{a.type} {r['id']}",
                        "autopilot/queue.tsv"], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
