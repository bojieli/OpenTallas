#!/usr/bin/env python3
"""DIE-QC-97 11-10 (COORD re-ruling HOLD-TAP-SPLIT): hc0 die-clock taps on the real sink inventory, the 068bab0a7fd delta
(DIE-QC-70 delta_hc_bins.py) extended to the four hc rows it left out.

sle_hc0__cl05696ed1 (job dc1bbaa2ef39) FF hold -100.65 on 8,795 non-port endpoints, 5,584 of them reg->reg across taps:
without clock.sink_bins_file the density taps saw only plan pins and ft sinks, so 77k registers got 15 taps, 7-8 of them
above the 1200 cap (9.8k-18k sinks, insertion 172-256 ps).  Every other hc row has bins (125-132 taps, 0 over cap).

Each listed type gets clock.sink_bins_file = sink_bins/<type>.json (bins from the row's own wave 3_place.odb, clk-net
register sinks) and clock.tap_pair_affinity = {} when absent (gen_phys defaults; with no tap above cap the pair planner
can join short pairs).  Every other type and top-level key stays byte-identical.

Replay on the kit's own 3_place.odb (sle_hc0__cl05696ed1, kit clock_taps.tcl + tap_pair_affinity.tcl on the bins taps):
128 taps, 0 over cap, reach <= 194 um; cross-tap short pairs 6,486 -> 133; routed reg->reg hold violators still split
over taps 5,584 -> 1,369; leaf seam links xl0_k.wo_d -> xl0_k+1.wd still crossing: 1.

    python3 tools/die_plan/qc_hc0_bins_event.py BASE_PLAN OUT_PLAN EVENT_JSON      (run from the repo root)
"""
import hashlib
import json
import sys
from pathlib import Path

REL = "physical/die_plan/qwen_compute/plan_of_record/sink_bins"
TYPES = ["sle_hc0__cl05696ed1", "sle_hc0__cl929603c0__cl38badc56", "sle_hc0__cl929603c0__cl4baa7c9c",
         "slw_hc0__cl4f54b7a3"]


def apply(P, types=TYPES, root=Path(".")):
    """-> (new plan, {type: change list}); ValueError when a type is missing, has no density clock, already has bins
    or its bins file is absent / for another type."""
    Q = json.loads(json.dumps(P))
    T = Q["partition_types"]
    changes = {}
    for tn in types:
        if tn not in T:
            raise ValueError(f"type {tn} not in the plan")
        ck = T[tn].get("clock")
        if not isinstance(ck, dict) or ck.get("tap_mode") != "density":
            raise ValueError(f"type {tn}: no density clock")
        if ck.get("sink_bins_file"):
            raise ValueError(f"type {tn} already has clock.sink_bins_file")
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
    return Q, changes


def dumps_like(P, text):
    """re-serialise P in the style the input file used (plan-of-record compact / spaced, or kit-wave indent=1)"""
    R = json.loads(text)
    for kw in (dict(separators=(",", ":")), dict(separators=(", ", ": ")), dict(indent=1), dict(indent=2)):
        for nl in ("\n", ""):        # ctlch candidate plans (cand23d_fh) end without a newline
            if json.dumps(R, **kw) + nl == text:
                return json.dumps(P, **kw) + nl
    raise ValueError("base plan is not in a known JSON style")


def main(argv):
    base, out, ev = argv[1:4]
    text = Path(base).read_text()
    P = json.loads(text)
    Q, changes = apply(P)
    new = dumps_like(Q, text)
    Path(out).write_text(new)
    sha = lambda s: hashlib.sha256(s.encode()).hexdigest()
    rec = {"event": "DIE-QC-97 hc0 sink bins (HOLD-TAP-SPLIT)", "base": base, "base_sha256": sha(text), "out": out,
           "out_sha256": sha(new), "types": changes,
           "bins_sha256": {tn: hashlib.sha256(Path(f"{REL}/{tn}.json").read_bytes()).hexdigest() for tn in changes}}
    Path(ev).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
