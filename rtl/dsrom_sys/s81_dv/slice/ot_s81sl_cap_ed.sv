`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// LEAD2-S81/TOK (2026-10-19): ot_s81sl_cap_ed = static E-column delay of the capture root (TOK.DS.BENCH.1 calendar fix).
//
// Why: the first coupled QF diagnostic (757a340ff, unit 627409) proved the CAP root takes ONE word per edge and the six
// frames' rows never merge, so all frame partials need distinct root edges.  The shared XS stream gives every frame the
// same segment dates; the root's possible exit window is 37 edges (9 pairs) / 39 edges (12 pairs) against >= 44 real
// partials.  An EXACT uncapped packing (root_pack.py, results/rtl/s81_qf_producer_1019/cap_ed_calendar) finds NO legal
// six-frame calendar for 9 or 12 pairs with shared-stream gaps 0/8/16/24/32, but finds one per column (3 frames, 12
// pairs, gap 0: 22 words, edges 1773..1802), and a six-frame one with the E column delayed by D = 23 edges.
// So the E tree's output word (u_te nc RST flop) is delayed by exactly D edges before n6's E port: W and E columns
// interleave on n6 at disjoint edges, no arbitration, no queue, no backpressure (static calendar; the compiler owns D).
//
// Structure: ot_hdc_delay_rf (pin input reg -> (D-2)-row circular RF -> pin output reg; no flop->flop hold chain).
// 66 bits x (D-2) = 1,386 bits at D = 23 (< 2 kb: register file, SAFE item 5).  The RF holds no reset; the valid bit
// leaving the line is masked for the first D edges after reset (primed counter) so no stale/X word is ever valid.
// The E fault bit is sticky and phase-end checked: it bypasses the line (plus one pin flop).
// Cost: +D edges on every E-column return word (latency only; throughput unchanged: epoch period 600 >> D).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_cap_ed #(
    parameter integer D = 23
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        i_v,
    input  wire [31:0] i_t,
    input  wire [31:0] i_d,
    input  wire        i_e,
    input  wire        i_f,
    output wire        o_v,
    output wire [31:0] o_t,
    output wire [31:0] o_d,
    output wire        o_e,
`ifdef OT_S81_CAP_ED_FACE_DELAYED_FAULT
    output wire        o_f
`else
    output reg         o_f
`endif
);
    wire [1:0] rsv;
    ot_rst_relay #(.REGIONS(2), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire [65:0] q;
`ifndef OT_S81_CAP_ED_FACE_DELAYED_FAULT
    ot_hdc_delay_rf #(.W(66), .D(D)) u_dl (.clk(clk), .rst_n(rsv[0]), .d({i_e, i_d, i_t, i_v}), .q(q));
`else
    // Same D-edge register-file delay; capture the post-edge valid mask in
    // the existing output register. No payload or calendar edge moves.
    localparam integer FACE_N = D - 2;
    localparam integer FACE_K = (FACE_N <= 2) ? 1 : $clog2(FACE_N);
    localparam [FACE_K-1:0] FACE_LAST = FACE_N - 1;
    reg [65:0] face_din;
    reg [65:0] face_mem [0:FACE_N-1];
    reg [FACE_K-1:0] face_wptr;
    reg [64:0] face_dout;
    reg face_valid;
`ifndef SYNTHESIS
    initial face_wptr = 0;
`endif
    always @(posedge clk) begin
        face_din <= {i_e, i_d, i_t, i_v};
        face_mem[face_wptr] <= face_din;
        face_dout <= face_mem[face_wptr][65:1];
        face_wptr <= (face_wptr >= FACE_LAST) ? 0 : face_wptr + 1'b1;
    end
    always @(posedge clk or negedge rsv[1])
        if (!rsv[1]) face_valid <= 1'b0;
        else face_valid <= face_mem[face_wptr][0] && (primed || cnt == D[CW-1:0]);
    assign q = {face_dout, face_valid};
`endif
    localparam integer CW = $clog2(D + 2);
    reg [CW-1:0] cnt; reg primed;
    always @(posedge clk or negedge rsv[1])
        if (!rsv[1]) begin cnt <= {CW{1'b0}}; primed <= 1'b0; end
        else if (!primed) begin cnt <= cnt + 1'b1; primed <= (cnt == D[CW-1:0]); end
`ifdef OT_S81_CAP_ED_FACE_DELAYED_FAULT
    assign o_v = q[0];
`else
    assign o_v = q[0] && primed;
`endif
    assign o_t = q[32:1];
    assign o_d = q[64:33];
    assign o_e = q[65];
`ifdef OT_S81_CAP_ED_FACE_DELAYED_FAULT
    // OWNER (A) 2026-10-30 00:1x, ADOPTED for the S81 CAP_ED hard child via the recipe define
    // (physical/die_plan/s81/cores/legacy/recipes.json ot_s81sl_cap_ed): data edges unchanged, fault visibility +1 edge,
    // priced in results/s81_cap_ed_owner_option_2356/fault_budget.json (phase-end check slack 63 -> 62 edges).
    // Raw input pin capture precedes sticky accumulation; isolated face copy
    // samples that sticky next state on the same edge as the private state.
    reg face_fault_i, face_fault_state, face_fault_next;
    always @* begin
        face_fault_next = face_fault_state;
        if (face_fault_i) face_fault_next = 1'b1;
    end
    always @(posedge clk or negedge rsv[1])
        if (!rsv[1]) begin face_fault_i <= 0; face_fault_state <= 0; end
        else begin face_fault_i <= i_f; face_fault_state <= face_fault_next; end
    ot_s81sl_cap_ed_fault_face u_fault_face (
        .clk(clk), .rst_n(rsv[1]), .d(face_fault_next), .q(o_f));
`else
    always @(posedge clk or negedge rsv[1]) if (!rsv[1]) o_f <= 1'b0; else if (i_f) o_f <= 1'b1;
`endif
endmodule
`ifdef OT_S81_CAP_ED_FACE_DELAYED_FAULT
(* keep_hierarchy, keep *)
module ot_s81sl_cap_ed_fault_face(input wire clk,rst_n,d,output reg q);
 always @(posedge clk or negedge rst_n)
  if(!rst_n) q<=1'b0; else q<=d;
endmodule
`endif
`default_nettype wire
