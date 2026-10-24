#!/usr/bin/env python3
"""HBM-P6-CMP (10-23): the HBM d4g over-cap LEAF-SPLIT latency shifts, ONE table for every compiler / pricer.

The HBM plan (physical/die_plan/hbm, 400k-cell core cap) splits five over-cap leaves into hard cores.  Each split is an
RTL twin of the pinned unit with pin registers on the new core crossings; every twin was benched lock-step against the
pinned unit (positive PASS at exactly the shift below, mutant FAIL).  The compiler must schedule the twin's latency.
Index: physical/die_plan/hbm/over_cap_split/index.json (+ <master>.split.json rtl.cycle_cost_edges / bench_result).

Opt-in (AGENTS.md: behind a parameter, off by default until the exact gate passes): the shifts apply only when
OT_HBM_LEAF_SPLIT=1 is set in the environment, or when a caller passes leaf_split=True explicitly.  With it off every
compiler emits byte-identical programmes to the pinned die (shift 0).

Edges are in the clock of the unit's own programme (SFU/SU/HC: serial-domain core edges; COLL/TKM: stream edges).
"""
from __future__ import annotations

import os

ENV = "OT_HBM_LEAF_SPLIT"

# name: (edges, unit / where the compiler applies it, source (twin + bench of record))
SHIFTS = {
    # SFU core split3 -> twin _sp2 (store-side pin registers)
    "sfu_op_horizon": (3, "SFU: every op's control held 3 edges longer (sfu_vector_calendar drain horizon +3)",
                       "ot_hgi_sfu_core_split3_sp2 (claude/hbm-p5-rtla-1023 b40e763de); SP2_LOCKSTEP PASS 7168 words "
                       "@3cb21933b, horizon_extra=3, mutant RDX1 FAIL"),
    "sfu_operand_read": (2, "SFU: operand read request -> data at the lane +2 (store request pin +1, data pin +1)",
                         "same bench: read_shift 0 at the pins, result_shift 2"),
    "sfu_vm_write": (1, "SFU: output-group VM write +1 after the result (write_shift 3 = result 2 + 1)",
                     "same bench: write_shift 3"),
    # SU pgslice_lg -> PIN_REG 1 (pin-registered lanes) + side split
    "su_pin_reg": (1, "SU: die su_<q><g> PIN_REG parameter 0 -> 1 (su_top_compile --pin-reg 1)",
                   "ot_hbm_su_static_pgslice_lg_s (claude/hbm-p5-rtlb-1023 8f38f3246); leaf benches kind0/1/2 PASS "
                   "first_output 36 -> 40 @2ec95b72b, mutants ADDR/DATA/PHASE FAIL; QID 0 G 0 FULL lane+side PASS 9000"),
    "su_request": (2, "SU: lane store / RF requests +2 edges (2 x PIN_REG)", "same: su_top_compile pin_reg rule"),
    "su_write": (4, "SU: lane writes / reducer operands / first lane output +4 edges (4 x PIN_REG)",
                 "same: first_output 36 -> 40 measured"),
    # HC root -> sinkhorn_s twin (one sink edge = SDIV core edges)
    "hc_tail_result": (7, "HC: tail launch -> result +7 core edges (L 496 -> 503); every HC tail emit +7",
                       "ot_hbm_hc_root_static_s / tail_unit_static_s (claude/hbm-p5-rtlb-1023 2ec95b72b): tail_unit_s "
                       "PASS seeds 1/7 (launch->result 495 -> 502), SMUT 1 FAIL; root eng4 ring HC_ENG PASS --tail-extra 7"),
    # COLL q2 hard v8g -> reduce_static_pr (reduce input pin registers)
    "coll_reduce_pub": (1, "COLL: reduce runs 1 edge later -> reduce-source qslots capture slot and every "
                           "publication-relative constant +1 (one per AR reduce publication)",
                        "ot_hgi_coll_reduce_static_pr / ot_hfd_coll_q2_hard_v8g_s (claude/hbm-p5-rtlb-1023 23e4c440d): "
                        "PASS DENS 1/2/4 (+1 every publication), MUT 1/2 FAIL"),
    "coll_reduce_fault": (2, "COLL: reduce fault status +2 (status only, not scheduled)", "same bench"),
    # TKM TP192 -> ot_hgi_coll_tkm_static_p #(PIPE 1)
    "tkm_done": (2, "TKM: finish/done/stat_cycles and every write +2 edges a TOPK_MERGE (same words/order)",
                 "ot_hgi_coll_tkm_static_p PIPE 1 (claude/hbm-p5-rtla-1023 e03ce0eb5): TKM_LOCKSTEP shift 2 PASS "
                 "rank128_zeros + syn_sel (syn_cand pending), PIPE0 identity, mutant MUTP1 FAIL"),
}


def enabled(leaf_split=None):
    """explicit argument wins; else the OT_HBM_LEAF_SPLIT environment switch (default off)."""
    if leaf_split is not None:
        return bool(leaf_split)
    return os.environ.get(ENV, "0") not in ("", "0", "false", "no")


def shift(name, leaf_split=None):
    """the edges of SHIFTS[name] when the leaf split is on, else 0."""
    return SHIFTS[name][0] if enabled(leaf_split) else 0


def table():
    return {k: dict(edges=v[0], applies=v[1], source=v[2]) for k, v in SHIFTS.items()}


if __name__ == "__main__":
    import json
    print(json.dumps(dict(enabled=enabled(), table=table()), indent=1))
