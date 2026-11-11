#!/usr/bin/env python3
"""DIE-QC-97 11-10 (COORD PLAN-GEN-RULES-1 rule B, owner-approved): the density types rule B lists as "die-owner form"
(density taps under-tapped for their measured sinks) take the QC hc0 sink_bins mechanism -- the qc_hc0_bins_event.py
form (claude/die-qc-97-hc0-hold-1110) extended to the rule-B list.

Each listed type gets clock.sink_bins_file = plan_of_record/sink_bins/<type>.json (die-clock register sinks of the row's
own wave 3_place.odb: every register on the clk / clk_t<i> tap nets, edge-clock fclk_in_* ring flops excluded; 10.8-um
bins, the binsrep.py form) and clock.tap_pair_affinity = {} when absent.  A listed type that already has a
clock.sink_bins_file (or a clock.tap_group) keeps it: reported as overlap, not changed.  A listed type without a
density clock (named-tap / explicit coll, glue, native59 rows) cannot take bins: reported, not changed.  Every other
type and top-level key stays byte-identical, and the base serialization style is kept.

    python3 -I tools/die_plan/qc_pgr_bins_event.py BASE_PLAN OUT_PLAN EVENT_JSON [TYPES_JSON]   (from the repo root)
"""
import hashlib
import json
import sys
from pathlib import Path

REL = "physical/die_plan/qwen_compute/plan_of_record/sink_bins"
# PLAN-GEN-RULES-1 rule B density rows on the DIE-QC-97 lineage (cand23d_fh_hc0bins_stmdq_ra 886a8ffae774)
TYPES = ["sle_ctl__cl372cea1c", "sle_fw_v2__cl6740750e", "sle_st_a_v2", "sle_st_b_v1__pv0e7b1dcc",
         "sle_st_b_v1__pvc5a85fd4", "sle_st_b_v2__cl14c98df5", "sle_st_b_v2__clfde1249e", "slw_fe_v2__clf110fab2",
         "slw_fw_v2__cl8f84514c", "slw_st_b_v1__cl6357f1cc__pv6ace3e48", "slw_st_b_v1__cl6357f1cc__pvffd43fdc",
         "slw_st_b_v1__cle6023ec2", "slw_st_b_v2__pva66d0f22", "slw_st_b_v2__pvc2ec5bfb"]


def apply(P, types=TYPES, root=Path(".")):
    """-> (new plan, {type: change list}, {type: why kept}); ValueError when a type is missing or its bins file is
    absent / empty / for another type."""
    Q = json.loads(json.dumps(P))
    T = Q["partition_types"]
    changes, kept = {}, {}
    for tn in types:
        if tn not in T:
            raise ValueError(f"type {tn} not in the plan")
        ck = T[tn].get("clock")
        if not isinstance(ck, dict) or ck.get("tap_mode") != "density":
            kept[tn] = f"tap_mode {(ck or {}).get('tap_mode') if isinstance(ck, dict) else None}: no density clock"
            continue
        if ck.get("sink_bins_file") or "tap_group" in ck:
            kept[tn] = "keeps " + ", ".join(f"clock.{k} {ck[k]}" for k in ("sink_bins_file", "tap_group") if k in ck)
            continue
        rel = f"{REL}/{tn}.json"
        doc = json.loads((root / rel).read_text())
        if doc.get("type") != tn or not doc.get("bins") or doc.get("n", 0) <= 0:
            raise ValueError(f"type {tn}: bins file {rel} empty or for another type")
        ck["sink_bins_file"] = rel
        ch = ["clock.sink_bins_file"]
        if "tap_pair_affinity" not in ck:
            ck["tap_pair_affinity"] = {}
            ch.append("clock.tap_pair_affinity = {}")
        changes[tn] = ch
    return Q, changes, kept


def dumps_like(P, text):
    """re-serialise P in the style the input file used (compact / spaced / indent=1 / indent=2, newline or not)"""
    R = json.loads(text)
    for kw in (dict(separators=(",", ":")), dict(separators=(", ", ": ")), dict(indent=1), dict(indent=2)):
        for nl in ("\n", ""):
            if json.dumps(R, **kw) + nl == text:
                return json.dumps(P, **kw) + nl
    raise ValueError("base plan is not in a known JSON style")


def main(argv):
    base, out, ev = argv[1:4]
    types = json.loads(Path(argv[4]).read_text()) if len(argv) > 4 else TYPES
    text = Path(base).read_text()
    P = json.loads(text)
    Q, changes, kept = apply(P, types)
    new = dumps_like(Q, text)
    Path(out).write_text(new)
    sha = lambda s: hashlib.sha256(s.encode()).hexdigest()
    rec = {"event": "DIE-QC-97 PLAN-GEN-RULES-1 rule B density rows -> sink bins", "base": base,
           "base_sha256": sha(text), "out": out, "out_sha256": sha(new), "types": changes, "kept": kept,
           "rtl_change": False, "data_cycles": 0, "pin_cycles": 0,
           "bins_sha256": {tn: hashlib.sha256(Path(f"{REL}/{tn}.json").read_bytes()).hexdigest() for tn in changes}}
    Path(ev).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
