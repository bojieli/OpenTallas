// el1013-qwen-stalls 2026-10-13: listed FIRST in the ot_hdc_vstream_lane_t lane-CLUSTER (tools/ref_tile kind=cluster)
// sources: the lane head (ot_hdc_vstream_lane_h) and the three special-function tiles (ot_hdc_sfu_exp_t / _rcp_t /
// _rsq_t) are its hard children (no parameter overrides, bodies excluded from the cluster synthesis).  Simulation and
// the leaf kits do not read this file (same words, children as RTL).
`define OT_SU_LANE_HARD
