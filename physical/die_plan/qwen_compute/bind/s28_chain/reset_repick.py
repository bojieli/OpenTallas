#!/usr/bin/env python3
"""QC-S28-BIND (c)/(d): reset reference re-pick + local-copy depth law on the FINAL composed plan, re-using the reviewed
QC-S28-TAPS rule (taps/compose_taps.py stage_r, street_rule.reset_resel rule) unchanged, with one difference: the
TAPS one-off MEASURED_SHIFT (cbn_q00__cl622f65d2 +1) is already inside the recorded anchors, so it is not applied again.

  BASE = the plan on which the clock.reset_tree_anchor records were made (QC-S28-TAPS out, zz_c1_taps 67b0bf06d8dc)
  For every type with an anchor:   d0 = tree depth on BASE, d1 = tree depth now (d1 < d0 refused: pad first)
    START stage raw_reset          same anchored depth, nearest non-ported relay to the STAGE xy (kept if unchanged)
    landing_local_resets raw       anchored depth + (d1 - d0)  (copy depth + 1 = consumer reset depth)
    anchors re-recorded            (a later bind is a no-op re-pick)
  reset_repick.py BASE PLAN_IN PLAN_OUT REPORT.json EQ.tsv     (run from the event tree root, plans in the plan folder)
"""
import importlib.util
import json
import shutil
import sys
from pathlib import Path

TAPS = Path("/srv/opentallas-scratch2/claude/qc-s28-hf1c/taps/compose_taps.py")


def main(base, pin, pout, rep, eqf):
    spec = importlib.util.spec_from_file_location("compose_taps", str(TAPS))
    CT = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(CT)
    CT.MEASURED_SHIFT = {}
    shutil.copyfile(pin, pout)
    raw = json.loads(Path(pout).read_text())
    names = sorted(tn for tn, t in raw["partition_types"].items() if (t.get("clock") or {}).get("reset_tree_anchor"))
    B = json.loads(Path(base).read_text())
    names = [n for n in names if n in B["partition_types"]]
    rows = CT.stage_r(base, B, pout, names)
    eq = []
    for tn, r in sorted(rows.items()):
        d0, d1 = r["depth"]
        if d1 != d0:
            eq.append([tn, "reset tree depth (wavefront release) vs anchor base", str(d0), str(d1), str(d1 - d0),
                       "pad-only (reset_pad.py) / base re-solve"])
        for x in r["local_resets"]:
            if x["depth_before"] != x["depth_after"]:
                eq.append([tn, "landing_local_resets.%s raw" % x["name"], "%s@%d" % (x["raw_before"], x["depth_before"]),
                           "%s@%d" % (x["raw_after"], x["depth_after"]), str(x["depth_after"] - x["depth_before"]),
                           "copy depth %d -> %d = consumer reset depth %d; copy->relay %s um"
                           % (x["copy_depth"][0], x["copy_depth"][1], x["consumer_depth"], x["copy_to_relay_um"])])
    held = {tn: r["held"] for tn, r in rows.items() if r.get("held")}
    Path(rep).write_text(json.dumps(dict(base=base, plan_in=pin, rows=rows, held=held), indent=1) + "\n")
    with open(eqf, "w") as f:
        f.write("type\tkind\tbefore\tafter\treset_release_cycles\tnote\n")
        for e in eq:
            f.write("\t".join(e) + "\n")
    n_st = sum(len(r["start_stages"]) for r in rows.values())
    n_lr = sum(len(r["local_resets"]) for r in rows.values())
    far = sum(1 for r in rows.values() for s in r["start_stages"] if s["stage_to_relay_um"] > 405)
    lfar = sum(1 for r in rows.values() for s in r["local_resets"] if s["copy_to_relay_um"] > 405)
    print("REPICK types", len(names), "start re-picks", n_st, "(>405:", far, ") local re-picks", n_lr, "(>405:", lfar,
          ") eq", len(eq), "held", held)


if __name__ == "__main__":
    main(*sys.argv[1:6])
