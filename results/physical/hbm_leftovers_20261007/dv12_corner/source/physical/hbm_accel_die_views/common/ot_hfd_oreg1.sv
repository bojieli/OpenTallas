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
// ot_hfd_oreg5: face_stages 5 (1.4 mm views: the last flop at the pin, four more carry the wire from the core at
// <= ~450 um a stage; qm_pd55 CTS put -198 / -135 ps on the first two stages of a 3-stage chain)
module ot_hfd_oreg5 (input wire clk, input wire d, output reg q);
    reg s0, s1, s2, s3;
    always @(posedge clk) begin s0 <= d; s1 <= s0; s2 <= s1; s3 <= s2; q <= s3; end
endmodule
// ot_hfd_oreg4: the last four stages of a face_stages 5 chain fed by a kept shared group copy (hbm_die_wrap.py
// share_tree: level-0 copy per die port, the chain's own four stages to the pin)
module ot_hfd_oreg4 (input wire clk, input wire d, output reg q);
    reg s0, s1, s2;
    always @(posedge clk) begin s0 <= d; s1 <= s0; s2 <= s1; q <= s2; end
endmodule
