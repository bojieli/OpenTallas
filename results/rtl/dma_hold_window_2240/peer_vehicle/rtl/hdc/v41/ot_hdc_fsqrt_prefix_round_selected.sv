// Explicit opt-in source selector for the same-cut prefix repair.
// Use this instead of ot_hdc_fsqrt.sv, never in addition to it.
`define OT_HDC_SQRT_PREFIX_ROUND 1
`include "rtl/hdc/v41/ot_hdc_fsqrt_prefix_round.sv"
`undef OT_HDC_SQRT_PREFIX_ROUND
