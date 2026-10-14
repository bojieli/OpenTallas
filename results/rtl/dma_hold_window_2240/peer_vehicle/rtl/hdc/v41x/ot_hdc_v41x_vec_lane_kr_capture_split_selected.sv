// Explicit opt-in source swap; never compile beside the original lane.
`define OT_HDC_KR_CAPTURE_SPLIT 1
`include "rtl/hdc/v41x/ot_hdc_bf16_capture_split.sv"
`include "rtl/hdc/v41x/ot_hdc_v41x_vec_lane_kr_capture_split.sv"
`undef OT_HDC_KR_CAPTURE_SPLIT
