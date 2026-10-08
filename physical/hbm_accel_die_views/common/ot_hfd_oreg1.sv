// OT_HFD_OUTLATCH (router-h1 2026-10-08, pin-output stage under rule H1): the pin flop of every ot_hfd_oregN drives the
// port through a negative-level latch (transparent while clk is low), as tools/qwen_core_out_latch.py does for Qwen
// core_kv.  The port changes only at the falling edge, so the sender's H1 output hold (50 ps link skew + 25 ps unc) gains
// ~T/2; a rising-edge receiver sees the same value in the same cycle (0 added cycles).  Setup cost: port valid at
// T/2 + latch delay.  OT_HFD_OUTLATCH_MUTANT replaces the latch by a rising-edge flop (+1 cycle): the lockstep bench
// must FAIL on it (negative control).  Default (neither define): unchanged.
`ifdef OT_HFD_OUTLATCH_MUTANT
`define OT_HFD_OL
`endif
`ifdef OT_HFD_OUTLATCH
`define OT_HFD_OL
`endif
`ifdef OT_HFD_OL
`define OT_HFD_PIN(R) ot_hfd_opin u_opin (.clk(clk), .d(R), .q(q));
module ot_hfd_opin (input wire clk, input wire d, output reg q);
`ifdef OT_HFD_OUTLATCH_MUTANT
    always @(posedge clk) q <= d;
`else
    always @* if (!clk) q = d;
`endif
endmodule
module ot_hfd_oreg1 (input wire clk, input wire d, output wire q);
    reg r; always @(posedge clk) r <= d;
    `OT_HFD_PIN(r)
endmodule
module ot_hfd_oreg2 (input wire clk, input wire d, output wire q);
    reg s0, r;
    always @(posedge clk) begin s0 <= d; r <= s0; end
    `OT_HFD_PIN(r)
endmodule
module ot_hfd_oreg3 (input wire clk, input wire d, output wire q);
    reg s0, s1, r;
    always @(posedge clk) begin s0 <= d; s1 <= s0; r <= s1; end
    `OT_HFD_PIN(r)
endmodule
module ot_hfd_oreg5 (input wire clk, input wire d, output wire q);
    reg s0, s1, s2, s3, r;
    always @(posedge clk) begin s0 <= d; s1 <= s0; s2 <= s1; s3 <= s2; r <= s3; end
    `OT_HFD_PIN(r)
endmodule
module ot_hfd_oreg4 (input wire clk, input wire d, output wire q);
    reg s0, s1, s2, r;
    always @(posedge clk) begin s0 <= d; s1 <= s0; s2 <= s1; r <= s2; end
    `OT_HFD_PIN(r)
endmodule
`else
module ot_hfd_oreg1 (input wire clk, input wire d, output reg q);
    always @(posedge clk) q <= d;
endmodule
module ot_hfd_oreg2 (input wire clk, input wire d, output reg q);
    reg s0;
    always @(posedge clk) begin s0 <= d; q <= s0; end
endmodule
module ot_hfd_oreg3 (input wire clk, input wire d, output reg q);
    reg s0, s1;
    always @(posedge clk) begin s0 <= d; s1 <= s0; q <= s1; end
endmodule
module ot_hfd_oreg5 (input wire clk, input wire d, output reg q);
    reg s0, s1, s2, s3;
    always @(posedge clk) begin s0 <= d; s1 <= s0; s2 <= s1; s3 <= s2; q <= s3; end
endmodule
module ot_hfd_oreg4 (input wire clk, input wire d, output reg q);
    reg s0, s1, s2;
    always @(posedge clk) begin s0 <= d; s1 <= s0; s2 <= s1; q <= s2; end
endmodule
`endif
// ot_hfd_oreg1: one die-view output register bit (tools/hbm_die_wrap.py kept_out_regs).  Routed with
// SYNTH_KEEP_MODULES=ot_hfd_oreg1 so equal-D output flops of a wrapper are never merged into one driver of many ports.
// ot_hfd_sink1: a kept local sink register for an RTL output the die interface does not carry (kept_out_regs wrappers).
module ot_hfd_sink1 (input wire clk, input wire d, output reg q);
    always @(posedge clk) q <= d;
endmodule
// ot_hfd_oreg2 / ot_hfd_oreg3: face_stages 2 / 3 output registers (owner margin-first rule 2026-10-06: the last flop
// sits at the output pin, the earlier ones carry the wire across the 1.4 mm view).
// ot_hfd_oreg5: face_stages 5 (1.4 mm views: the last flop at the pin, four more carry the wire from the core at
// <= ~450 um a stage; qm_pd55 CTS put -198 / -135 ps on the first two stages of a 3-stage chain)
// ot_hfd_oreg4: the last four stages of a face_stages 5 chain fed by a kept shared group copy (hbm_die_wrap.py
// share_tree: level-0 copy per die port, the chain's own four stages to the pin)
// ot_hfd_rsync: a kept local reset synchroniser (views agent 2026-10-06, simplification rule 5: fanout replicas).
// Asynchronous assert, release two clocks after the parent reset; one per engine so no single reset flop drives a
// 1.4 mm view (ldm8: rst_s[1] -> 30 buffer levels -> -18 ps recovery even at the 2-cycle release multicycle).
// Routed with SYNTH_KEEP_MODULES=ot_hfd_rsync so the equal copies are never merged.
module ot_hfd_rsync (input wire clk, input wire rst_n, output wire q_n);
    reg [1:0] s;
    always @(posedge clk or negedge rst_n) if (!rst_n) s <= 2'b00; else s <= {s[0], 1'b1};
    assign q_n = s[1];
endmodule
