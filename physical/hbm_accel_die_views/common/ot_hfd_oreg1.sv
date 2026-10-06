// ot_hfd_oreg1: one die-view output register bit (tools/hbm_die_wrap.py kept_out_regs).  Routed with
// SYNTH_KEEP_MODULES=ot_hfd_oreg1 so equal-D output flops of a wrapper are never merged into one driver of many ports.
module ot_hfd_oreg1 (input wire clk, input wire d, output reg q);
    always @(posedge clk) q <= d;
endmodule
// ot_hfd_sink1: a kept local sink register for an RTL output the die interface does not carry (kept_out_regs wrappers).
module ot_hfd_sink1 (input wire clk, input wire d, output reg q);
    always @(posedge clk) q <= d;
endmodule
// ot_hfd_oreg2 / ot_hfd_oreg3: face_stages 2 / 3 output registers (owner margin-first rule 2026-10-06: the last flop
// sits at the output pin, the earlier ones carry the wire across the 1.4 mm view).
module ot_hfd_oreg2 (input wire clk, input wire d, output reg q);
    reg s0;
    always @(posedge clk) begin s0 <= d; q <= s0; end
endmodule
module ot_hfd_oreg3 (input wire clk, input wire d, output reg q);
    reg s0, s1;
    always @(posedge clk) begin s0 <= d; s1 <= s0; q <= s1; end
endmodule
// ot_hfd_oreg5: face_stages 5 output register (CLAUDE hbm-router: hfd_router out_ids fan out to 5 faces of the 1.4 mm
// view; at face_stages 3 the core flop -> first stage wire was -179 ps pre-CTS at 770 ps effective).
module ot_hfd_oreg5 (input wire clk, input wire d, output reg q);
    reg s0, s1, s2, s3;
    always @(posedge clk) begin s0 <= d; s1 <= s0; s2 <= s1; s3 <= s2; q <= s3; end
endmodule
