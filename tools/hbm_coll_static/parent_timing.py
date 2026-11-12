#!/usr/bin/env python3
"""COLL quadrant parent timing constants for the static compiler (host_v4 vs hard_v5), with the lockstep check.

The static COLL compiler / programme lowering reserves fixed edges around the quadrant's HOST F20 programme target and
its 1536b issuer (tools/hbm_coll_static/program_transport.py, tools/uarch_model_hcoll_program_join.py).  The hard
hierarchy parent ot_hfd_coll_q{2,3}_hard_v5 (H-NETLIST/COLL 1045, V5 issue timing) shifts some of them:

  HOST frames   captured at the fj leaf's pin registers: the programme target sees every F20 / descriptor / launch
                write 1 edge later, so its configured / init_busy / program_fault outputs are +1 (SHP).  Frame-to-frame
                gaps (55-edge row drain, 66-edge descriptor scan before launch) are RELATIVE to the target's own
                capture and are unchanged.
  issue path    launch capture +1, issuer input pin registers +1 (COLLPIN 10-18, coordinator 0gd), uop stream delayed
                +3 for the pipelined iteration products (ot_hgi_coll_iter_mul, V6): every issue-path output (first uop
                effect, busy, done, injects, VM requests, rails, deliveries) is +5 (SH).  Host launch -> first uop
                effect: 5 -> 10 edges.  The programme target's occupancy view of the issuer is UNCHANGED (the issuer
                exports busy | start_q), so frame/descriptor/launch legality windows are as before.
  child faults  registered once more at the fj pins: host-visible fault = (V4 edge) + SH + 1 for a fault raised on the
                issue path; a programme-frame fault is + SHP.

The facts are read from the lockstep bench that proves them, rtl/hbm_accel/generic/collective/p2p/tb_hgi_coll_q_hard_v5.sv
(`localparam integer SH=..,SHP=..` and the fault-edge rule `(scen==6||scen==8)?SHP:SH+1`).  Compiling for a parent with another
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
sys.path.insert(0, str(Path(__file__).resolve().parent))
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
    "issuer_input_pin_edges": 0,                # issuer leaf pin stage on cfg/start/start_pc (part of issue_path_shift)
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
                issuer_input_pin_edges=1 if sh >= 5 else 0,
                issue_path_shift_edges=sh,
                child_fault_extra_edges=1,
                program_fault_shift_edges=shp)


HARD_V5 = _hard_v5(5, 1)          # tb_hgi_coll_q_hard_v5.sv COLLPIN: SH=5, SHP=1, child fault +SH+1 (V6 SH=4; V5 5bb671b57 SH=3)
# hard_v8x_iss2e = ot_hfd_coll_q3_hard_v8x_s with -DOT_COLL_ISSUER256_ISS2E (HBM-TAPS ISS2E issuer ot_hgi_coll_issuer_m256v8e): the
# fetch loop advances at most every 2nd edge (row k issues at v8 first-row edge + 2k).  The issue-path edge constants are
# the hard_v5/v8 ones (not independently re-proven here: HBM-TAPS owns them); only the row cadence and the issuer pad mask are
# new.  The pad mask (-DOT_COLL_ISS8E_PAD_MASK, 1536 bits) delays the masked uop bits by one edge so a field with an odd v8
# offset can sit on the 2-edge row grid.  Bits are static_uop_layout_v4.json positions (capture_slot 0..9, sink_slot 10..25,
# sink_select 26..89, ar_high 688..711): capture_slot[5..8] (v8 capture, NPT 3), sink_slot[3] + sink_select nibble 3 (delivery sink),
# ar_high bits 17..19 = ar start / flush / publish.
ISS2E_PAD_BITS = (*range(5, 9), 13, *range(38, 42), 705, 706, 707)
ISS2E_PAD_FIELDS = dict(vm_rq=0, capture_slot=1, sink_vm=0, in_slot=0, start=1, flush=1, publish=1, capture_arg=0,
                        sink_delivery=1, del_obase=0)
HARD_V8X_ISS2E = dict(HARD_V5, parent="hard_v8x_iss2e", issue_row_cadence_edges=2,
                      issue_pad_bits=list(ISS2E_PAD_BITS), issue_pad_fields=dict(ISS2E_PAD_FIELDS))
PARENTS = {"host_v4": HOST_V4, "hard_v5": HARD_V5, "hard_v8x_iss2e": HARD_V8X_ISS2E}


def iss2e_variant(start_reg: bool = False, pr_source: bool = False) -> dict:
    """pad bits / per-field parity of hard_v8x_iss2e for the ARG variant the parent carries (all edges relative to in_slot, parity 0):
      base (ot_hgi_coll_argmax_static):  start in-1 (1), capture_arg publish+1 (0), delivery sink publish+2 (1), del_obase publish+3 (0)
      start_reg (argmax_m_tp192): start in-2 -> parity 0: bit 705 leaves the mask
      pr_source (_pr, publish +1 edge): capture_arg publish+2 (1), delivery sink +3 (0), del_obase +4 (1)
    The mask is ONE define per parent build, so a parent that runs several programmes needs the union of their bits and no
    parity conflicts (row_gather_rows reports its own bits)."""
    f = dict(ISS2E_PAD_FIELDS)
    if start_reg:
        f["start"] = 0
    if pr_source:
        f.update(capture_arg=1, sink_delivery=0, del_obase=1)
    import iss2e_pad
    bits = [b for b, p in iss2e_pad.arg_bit_parity(f).items() if p]
    return dict(HARD_V8X_ISS2E, issue_pad_bits=sorted(bits), issue_pad_fields=f, issue_hold_bits=iss2e_pad.arg_hold_bits())


def pad_mask_literal(c: dict) -> str:
    """the issuer pad mask as the Verilog literal -DOT_COLL_ISS8E_PAD_MASK takes"""
    v = 0
    for b in c["issue_pad_bits"]:
        v |= 1 << b
    return f"1536'h{v:0384x}"


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
    f = re.search(r"scen\s*==\s*6\s*(?:\|\|\s*scen\s*==\s*\d+\s*\)\s*)?\?\s*SHP\s*:\s*SH\s*\+\s*(\d+)", t)
    if not f:
        raise ValueError(f"{tb}: no fault-edge rule `scen==6?SHP:SH+n`")
    return {"SH": int(m.group(1)), "SHP": int(m.group(2)), "child_fault_plus": int(f.group(1)), "tb": str(tb)}


def check(parent: str, c: dict, tb: Path = TB) -> list:
    """failures of constants c for parent against the evidence (host_v4: the identity; hard_v5: the lockstep bench)"""
    if parent == "host_v4":
        return [f"{k}: {c.get(k)} != host_v4 {v}" for k, v in HOST_V4.items() if k != "parent" and c.get(k) != v]
    if parent == "hard_v8x_iss2e":
        ref = HARD_V8X_ISS2E
        return [f"{k}: {c.get(k)} != {ref[k]}" for k in ("issue_row_cadence_edges", "issue_pad_bits", "issue_pad_fields")
                if c.get(k) != ref[k]]
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
