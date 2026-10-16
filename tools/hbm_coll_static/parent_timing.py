#!/usr/bin/env python3
"""COLL quadrant parent timing constants for the static compiler (host_v4 vs hard_v5), with the lockstep check.

The static COLL compiler / programme lowering reserves fixed edges around the quadrant's HOST F20 programme target and
its 1536b issuer (tools/hbm_coll_static/program_transport.py, tools/uarch_model_hcoll_program_join.py).  The hard
hierarchy parent ot_hfd_coll_q{2,3}_hard_v5 (H-NETLIST/COLL 1045, V5 issue timing) shifts some of them:

  HOST frames   captured at the fj leaf's pin registers: the programme target sees every F20 / descriptor / launch
                write 1 edge later, so its configured / init_busy / program_fault outputs are +1 (SHP).  Frame-to-frame
                gaps (55-edge row drain, 66-edge descriptor scan before launch) are RELATIVE to the target's own
                capture and are unchanged.
  issue path    launch capture +1, uop stream delayed +2 for the pipelined iteration products (ot_hgi_coll_iter_mul):
                every issue-path output (first uop effect, busy, done, injects, VM requests, rails, deliveries) is +3
                (SH).  Host launch -> first uop effect: 5 -> 8 edges.
  child faults  registered once more at the fj pins: host-visible fault = (V4 edge) + SH + 1 for a fault raised on the
                issue path; a programme-frame fault is + SHP.

The facts are read from the lockstep bench that proves them, rtl/hbm_accel/generic/collective/p2p/tb_hgi_coll_q_hard_v5.sv
(`localparam integer SH=..,SHP=..` and the fault-edge rule `scen==6?SHP:SH+1`).  Compiling for a parent with another
parent's constants FAILS `check` (a negative: hard_v5 with the V4 constants).

    python3 tools/hbm_coll_static/parent_timing.py show [--parent hard_v5]
    python3 tools/hbm_coll_static/parent_timing.py check --parent hard_v5 [--constants host_v4] [--tb PATH]
    python3 tools/hbm_coll_static/parent_timing.py selftest        (positive + the V4-constant negative)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TB = ROOT / "rtl/hbm_accel/generic/collective/p2p/tb_hgi_coll_q_hard_v5.sv"

# host_v4 = the values every existing V4 receipt was compiled with (tools/uarch_model_hcoll_program_join.py).
HOST_V4 = {
    "parent": "host_v4",
    "host_frame_capture_edges": 0,              # extra edges before the programme target sees an F20/desc/launch write
    "program_output_shift_edges": 0,            # configured / init_busy / program_fault vs host_v4
    "host_last_frame_to_first_cfg_edges": 2,
    "host_last_frame_to_row_complete_edges": 55,
    "host_next_row_frame_gap_edges": 55,        # relative: unchanged by a uniform capture shift
    "host_descriptor_to_launch_gap_edges": 66,  # relative: unchanged by a uniform capture shift
    "host_launch_to_issuer_start_edges": 2,
    "host_launch_to_first_uop_edges": 5,
    "issue_path_shift_edges": 0,                # every issue-path output (busy/done/injects/VM/rails/deliveries)
    "child_fault_extra_edges": 0,               # child fault -> host fault, beyond the issue-path shift
    "program_fault_shift_edges": 0,
}


def _hard_v5(sh: int, shp: int) -> dict:
    return dict(HOST_V4, parent="hard_v5",
                host_frame_capture_edges=shp,
                program_output_shift_edges=shp,
                host_last_frame_to_first_cfg_edges=HOST_V4["host_last_frame_to_first_cfg_edges"] + shp,
                host_last_frame_to_row_complete_edges=HOST_V4["host_last_frame_to_row_complete_edges"] + shp,
                host_launch_to_issuer_start_edges=HOST_V4["host_launch_to_issuer_start_edges"] + shp,
                host_launch_to_first_uop_edges=HOST_V4["host_launch_to_first_uop_edges"] + sh,
                issue_path_shift_edges=sh,
                child_fault_extra_edges=1,
                program_fault_shift_edges=shp)


HARD_V5 = _hard_v5(3, 1)          # tb_hgi_coll_q_hard_v5.sv at 5bb671b57: SH=3, SHP=1, child fault +SH+1
PARENTS = {"host_v4": HOST_V4, "hard_v5": HARD_V5}


def constants(parent: str = "host_v4") -> dict:
    """the compiler constants for one COLL quadrant parent (default host_v4: existing V4 receipts unchanged)"""
    if parent not in PARENTS:
        raise ValueError(f"unknown COLL parent {parent!r} (one of {sorted(PARENTS)})")
    return dict(PARENTS[parent])


def tb_facts(tb: Path = TB) -> dict:
    """SH / SHP and the child-fault rule as the lockstep bench states and checks them"""
    t = tb.read_text()
    m = re.search(r"localparam\s+integer\s+SH\s*=\s*(\d+)\s*,\s*SHP\s*=\s*(\d+)\s*;", t)
    if not m:
        raise ValueError(f"{tb}: no `localparam integer SH=..,SHP=..;`")
    f = re.search(r"scen\s*==\s*6\s*\?\s*SHP\s*:\s*SH\s*\+\s*(\d+)", t)
    if not f:
        raise ValueError(f"{tb}: no fault-edge rule `scen==6?SHP:SH+n`")
    return {"SH": int(m.group(1)), "SHP": int(m.group(2)), "child_fault_plus": int(f.group(1)), "tb": str(tb)}


def check(parent: str, c: dict, tb: Path = TB) -> list:
    """failures of constants c for parent against the evidence (host_v4: the identity; hard_v5: the lockstep bench)"""
    if parent == "host_v4":
        return [f"{k}: {c.get(k)} != host_v4 {v}" for k, v in HOST_V4.items() if k != "parent" and c.get(k) != v]
    if parent != "hard_v5":
        return [f"unknown parent {parent}"]
    e = tb_facts(tb)
    want = {
        "issue_path_shift_edges": e["SH"],
        "host_launch_to_first_uop_edges": HOST_V4["host_launch_to_first_uop_edges"] + e["SH"],
        "program_output_shift_edges": e["SHP"],
        "host_frame_capture_edges": e["SHP"],
        "program_fault_shift_edges": e["SHP"],
        "child_fault_extra_edges": e["child_fault_plus"],
        "host_next_row_frame_gap_edges": HOST_V4["host_next_row_frame_gap_edges"],
        "host_descriptor_to_launch_gap_edges": HOST_V4["host_descriptor_to_launch_gap_edges"],
    }
    return [f"{k}: compiled {c.get(k)} but {Path(e['tb']).name} proves {v} (SH={e['SH']} SHP={e['SHP']})"
            for k, v in want.items() if c.get(k) != v]


def selftest(tb: Path = TB) -> dict:
    pos = check("hard_v5", constants("hard_v5"), tb)
    neg = check("hard_v5", constants("host_v4"), tb)
    v4 = check("host_v4", constants("host_v4"), tb)
    ok = not pos and bool(neg) and not v4
    return {"positive_hard_v5": "PASS" if not pos else pos,
            "negative_hard_v5_with_v4_constants": "FAIL (as required): " + "; ".join(neg) if neg else "SURVIVED",
            "host_v4_unchanged": "PASS" if not v4 else v4, "facts": tb_facts(tb),
            "verdict": "PARENT_TIMING_SELFTEST PASS" if ok else "PARENT_TIMING_SELFTEST FAIL"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show"); s.add_argument("--parent", default="host_v4")
    c = sub.add_parser("check"); c.add_argument("--parent", required=True); c.add_argument("--constants")
    c.add_argument("--tb", type=Path, default=TB)
    t = sub.add_parser("selftest"); t.add_argument("--tb", type=Path, default=TB)
    a = ap.parse_args(argv)
    if a.cmd == "show":
        print(json.dumps(constants(a.parent), indent=1))
        return 0
    if a.cmd == "check":
        bad = check(a.parent, constants(a.constants or a.parent), a.tb)
        print("\n".join(bad) if bad else f"PARENT_TIMING {a.parent} PASS")
        if bad:
            print(f"PARENT_TIMING {a.parent} FAIL ({len(bad)})")
        return 1 if bad else 0
    r = selftest(a.tb)
    print(json.dumps(r, indent=1))
    return 0 if r["verdict"].endswith("PASS") else 1


if __name__ == "__main__":
    sys.exit(main())
