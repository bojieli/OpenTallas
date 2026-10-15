// Lint declaration of the actual CLOSED qfd_bl_lane hard child.
// Functional simulations use the real module in ot_qwen_band_lanes_slots.sv;
// physical synthesis/STA binds its existing LEF and TT/FF/SS Liberty views.
(* blackbox *)
module qfd_bl_lane (
 input wire ck,rst_n,b0,
 input wire [5:0] lnk,
 input wire [255:0] tw,
 input wire [25:0] c,
 input wire [97:0] tt,
 output wire [32:0] pw,
 output wire [255:0] ty,
 output wire f
);
endmodule
