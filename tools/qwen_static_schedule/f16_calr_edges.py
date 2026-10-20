#!/usr/bin/env python3
"""QW-F16PROG4 10-19: edge prices of the F16 witness face and the PRIVATE_CALR table-ROM load lane, handed to the
static schedule (no runtime waiter, no credit: every edge here is a compile-time constant).

F16 witness (qfd_tt_ctlm_dv_wtn = SAFE_PHYS qfd_dv_typed_witness_control in qfd_tt_ctlm_dv_gi, F16WTN=1):
  every status output (template_ready, context_active, all_witnesses_complete, group_complete/user/group, fault) is the
  legacy decision delayed by WTN_OUT_EDGES = 2 (pin register + output register); the CTLM cluster then adds its own
  landed output offset (u_thru, CTLM_OUT_EDGES, owned by tools/landed_parent spec) like every other core output.
  Inputs (start / observation / retire) are consumed 1 edge after they arrive (pin register) -- an observation due at
  context cycle d must reach the face pin at start_pin_edge + d (the controller counts from its own pin edge).
  No SU / token cycle is added: the witness is an observer with fault ownership only.

CALR table load (qfd_tt_ctlm_dv_gi g_calr -> die lane -> qfd_dv_slice2 g_tld -> qfd_dv_slice_tload):
  cal table_load edge E -> CTLM treq_q E+1 -> die lane T_die (GEN) -> slice k face (k row hops) ->
  tload face register +1 -> loader sample +1 -> first VM table write +3 / last +90 after the sample.
  Bench (results/arch/qwen_calendar_integration_1019/f16_tload): first write visible 5 edges after the request edge at
  the tload face (TLOAD first_age=5), 88 slots.
"""
WTN_OUT_EDGES = 2
WTN_IN_EDGES = 1
CTLM_TREQ_EDGES = 1          # treq_q in qfd_tt_ctlm_dv_gi
SLICE_ROW_HOP_EDGES = 1      # treq_o register per slice (beside cmd_o)
TLOAD_FACE_EDGES = 1         # rq_* in qfd_dv_slice_tload
LOADER_SAMPLE_EDGES = 1      # p_start in qfd_dv_table_rom_loader
LOADER_FIRST_WRITE = 3       # after the sample (inherited contract)
LOADER_LAST_WRITE = 90
LOADER_SLOTS = 88


def table_write_window(cal_edge: int, die_lane_edges: int, slice_index: int) -> tuple[int, int]:
    """First / last VM table-write edge in slice `slice_index` for a table_load issued at `cal_edge`.

    The compiler reserves [first, last] on that slice's VM table-write port exclusively (no stream table write in the
    window: a same-edge write is a collision fault, both writes suppressed)."""
    if die_lane_edges is None or die_lane_edges < 0:
        raise ValueError("die lane edges must come from the generated die (GEN), not a guess")
    sample = (cal_edge + CTLM_TREQ_EDGES + die_lane_edges + slice_index * SLICE_ROW_HOP_EDGES
              + TLOAD_FACE_EDGES + LOADER_SAMPLE_EDGES)
    return sample + LOADER_FIRST_WRITE, sample + LOADER_LAST_WRITE


def wtn_status_edge(decision_edge: int) -> int:
    """Edge at which a witness status bit is visible at the face output (before the CTLM landed offset)."""
    return decision_edge + WTN_OUT_EDGES
