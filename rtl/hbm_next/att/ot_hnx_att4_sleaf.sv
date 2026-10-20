`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HNEXT.ATT4 cluster-leaf successor of the P3 shared attention merge tile (claude/hnx-att4-leaf-1020, 2026-10-20).
// The one-tile kits (hnx_rp3a3_spvm_safe / _nf, 432 x 432, 18 SRAMs, 18.5k flops) failed: r2 = fenced band GPL
// congestion ~4 + DPL legalisation; _nf = one 18.5k-sink root fed from the E face (TT / FF pin-flop spread 127 / 114 ps)
// and a GRT the 4 h GATE_STALL watchdog killed (rc 137 = SIGKILL, not OOM) while looping congestion extra iterations.
// Structure here (parent = cluster kind, wires only):
//   u_n = ot_hnx_att4_sleaf_n  (N face of the parent; words 0..7 of every lane; 9 SRAMs; control replica)
//   u_s = ot_hnx_att4_sleaf_s  (S face of the parent; words 8..15 of every lane; 9 SRAMs; control replica)
// Each leaf = ot_hnx_att4_smerge_h (one word half of the datapath + an IDENTICAL control replica, see that file), its own
// clock root, every pin registered.  The leaves exchange only REGISTERED feed-throughs over the seam:
//   N -> S: the N-face inputs the S half needs (reset, ev, lanes 0-1 words 8..15, tags, publication request) straight
//           from the N leaf's pin registers, the N half's publication word and its sticky fault (one register stage);
//   S -> N: lane 2.. words 0..7 and lane 2.. tags straight from the S leaf's pin registers.
// Uniform schedule (every added cycle is a fixed constant for the compiler; no credit / ready / stall):
//   inputs: parent pin -> 2 register stages -> core in BOTH leaves (own face: pin reg + local pad; other face: the
//           other leaf's pin reg + own seam pin reg) = +1 edge vs the spvm (1 pin register);
//   reset : parent pin -> 2-stage landing (single flops) -> kept split stage (<= 32 loads a copy) -> core = +2 edges vs
//           the spvm; the core's residue counter resets to PH0 = 1, so the residue of every input edge is unchanged;
//   outputs: core -> 2 stages (N word: seam out reg + S seam in reg; S own: 2 pads) -> output pin reg = +2 edges.
//   => every output appears 3 edges later than the spvm's for the same pin stimulus (publication request -> first word
//      2 + 3 = 5 edges at the tile pins; COMPILER: +3 on the ATT publication read, nothing else moves).
// Mutants (cluster bench negative controls; 1..6 are the core's): MUT 7 = the S -> N lane-2 seam lands one edge late;
// MUT 8 = the S leaf's seam event bits land one edge late (its control replica sees events after its data); MUT 9 =
// the S leaf picks the wrong half's publication word.  (A reset-run skew between the leaves is NOT a fault: with idle
// inputs at reset release the merge is time-invariant, a later release only relabels the residues of that leaf
// consistently -- bench 10-20 run m8r: an S reset one stage late passed 576 nodes + lockstep, so it is no mutant.)
// ---------------------------------------------------------------------------------------------------------------------
module ot_hnx_att4_sleaf_n #(
    parameter integer NL  = 3,
    parameter integer LV  = 3,
    parameter integer MUT = 0
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire [NL-1:0]           ev,
    input  wire [1023:0]           sum_lo,     // lanes 0, 1 (512 b each)
    input  wire [31:0]             tag_lo,
    input  wire                    pub_start,
    input  wire [1:0]              pub_lane,
    input  wire [2:0]              pub_slot,
    input  wire [(NL-2)*256-1:0]   xs_in,      // seam from S: lanes 2.. words 0..7
    input  wire [(NL-2)*16-1:0]    xt_in,      // seam from S: lanes 2.. tags
    output wire                    f_rst,      // seam to S: N-face pin registers (feed-through)
    output wire [NL-1:0]           f_ev,
    output wire [511:0]            f_sum,      // lanes 0, 1 words 8..15
    output wire [31:0]             f_tag,
    output wire                    f_ps,
    output wire [1:0]              f_pl,
    output wire [2:0]              f_psl,
    output reg  [31:0]             f_pd,       // this half's publication word
    output reg                     f_flt
);
    initial if (NL < 3 || NL > 4) $fatal(1, "ot_hnx_att4_sleaf_n: 3 <= NL <= 4");
    localparam integer RK = 1;                           // the core lands its own kept per-group copies
    // reset: 2-stage landing at the face (single flops), then the kept split stage
    (* keep = "true" *) reg r1, r2;
    (* keep = "true", ot_rst_split = 1 *) reg [RK-1:0] r3v;
    wire r3 = r3v[0];
    always @(posedge clk) begin r1 <= rst_n; r2 <= r1; r3v <= {RK{r2}}; end
    // stage 1: N-face pin registers
    reg [NL-1:0] ev_a; reg [1023:0] sum_a; reg [31:0] tag_a; reg ps_a; reg [1:0] pl_a; reg [2:0] psl_a;
    always @(posedge clk) begin
        ev_a <= ev; sum_a <= sum_lo; tag_a <= tag_lo; ps_a <= pub_start; pl_a <= pub_lane; psl_a <= pub_slot;
    end
    assign f_rst = r1; assign f_ev = ev_a; assign f_tag = tag_a; assign f_ps = ps_a; assign f_pl = pl_a; assign f_psl = psl_a;
    assign f_sum = {sum_a[1023:768], sum_a[511:256]};
    // stage 2: local pad (own half) = the spvm pin register shifted one edge
    reg [NL-1:0] ev_b; reg ps_b; reg [511:0] sum_b; reg [31:0] tag_b; reg [1:0] pl_b; reg [2:0] psl_b;
    always @(posedge clk or negedge r3)
        if (!r3) begin ev_b <= {NL{1'b0}}; ps_b <= 1'b0; end
        else begin ev_b <= ev_a; ps_b <= ps_a; end
    always @(posedge clk) begin
        sum_b <= {sum_a[767:512], sum_a[255:0]}; tag_b <= tag_a; pl_b <= pl_a; psl_b <= psl_a;
    end
    // seam pin registers from the S leaf (its pin register + this one = 2 stages)
    reg [(NL-2)*256-1:0] xs_g, xs_g2; reg [(NL-2)*16-1:0] xt_g;
    always @(posedge clk) begin xs_g <= xs_in; xs_g2 <= xs_g; xt_g <= xt_in; end
    wire [(NL-2)*256-1:0] xs_c = (MUT == 7) ? xs_g2 : xs_g;
    wire c_pv, c_flt; wire [31:0] c_pd; wire [3:0] c_pw; wire [2:0] c_ps; wire [1:0] c_pl; wire [15:0] c_pt;
    ot_hnx_att4_smerge_h #(.NL(NL), .L(16), .TAGW(16), .ALAT(7), .LV(LV), .MUT(MUT), .HALF(0), .PH0(1)) u_h (
        .clk(clk), .rst_n(r3), .ev(ev_b), .sum({xs_c, sum_b}), .tag_d({xt_g, tag_b}),
        .pub_start(ps_b), .pub_lane(pl_b), .pub_slot(psl_b), .pub_v(c_pv), .pub_data(c_pd), .pub_word(c_pw),
        .pub_out_slot(c_ps), .pub_out_lane(c_pl), .pub_tag(c_pt), .fault(c_flt));
    always @(posedge clk) begin f_pd <= c_pd; f_flt <= c_flt; end
endmodule

module ot_hnx_att4_sleaf_s #(
    parameter integer NL  = 3,
    parameter integer LV  = 3,
    parameter integer MUT = 0
) (
    input  wire                    clk,
    input  wire                    f_rst,      // seam from N
    input  wire [NL-1:0]           f_ev,
    input  wire [511:0]            f_sum,
    input  wire [31:0]             f_tag,
    input  wire                    f_ps,
    input  wire [1:0]              f_pl,
    input  wire [2:0]              f_psl,
    input  wire [31:0]             f_pd,
    input  wire                    f_flt,
    input  wire [(NL-2)*512-1:0]   sum_hi,     // S face: lanes 2..
    input  wire [(NL-2)*16-1:0]    tag_hi,
    output wire [(NL-2)*256-1:0]   xs_out,     // seam to N: S-face pin registers (feed-through)
    output wire [(NL-2)*16-1:0]    xt_out,
    output reg                     pub_v,
    output reg  [31:0]             pub_data,
    output reg  [3:0]              pub_word,
    output reg  [2:0]              pub_out_slot,
    output reg  [1:0]              pub_out_lane,
    output reg  [15:0]             pub_tag,
    output reg                     fault
);
    initial if (NL < 3 || NL > 4) $fatal(1, "ot_hnx_att4_sleaf_s: 3 <= NL <= 4");
    localparam integer RK = 1;                           // the core lands its own kept per-group copies
    // reset: the N leaf's landing flop r1 -> seam pin register g1 (stage 2) -> kept split stage (stage 3, as the N leaf)
    (* keep = "true" *) reg g1;
    (* keep = "true", ot_rst_split = 1 *) reg [RK-1:0] g2v;
    wire g2 = g2v[0];
    always @(posedge clk) begin g1 <= f_rst; g2v <= {RK{g1}}; end
    // seam pin registers (stage 2 of the N-face inputs)
    reg [NL-1:0] ev_g, ev_g2; reg ps_g; reg [511:0] sum_g; reg [31:0] tag_g; reg [1:0] pl_g; reg [2:0] psl_g;
    reg [31:0] pd_g; reg flt_g;
    always @(posedge clk or negedge g2)
        if (!g2) begin ev_g <= {NL{1'b0}}; ps_g <= 1'b0; end
        else begin ev_g <= f_ev; ps_g <= f_ps; end
    always @(posedge clk) begin
        ev_g2 <= ev_g;                                   // MUT 8 only (dead otherwise)
        sum_g <= f_sum; tag_g <= f_tag; pl_g <= f_pl; psl_g <= f_psl; pd_g <= f_pd; flt_g <= f_flt;
    end
    // S-face pin registers (stage 1) and the local pad (stage 2)
    reg [(NL-2)*512-1:0] sum_hb; reg [(NL-2)*16-1:0] tag_hb, tag_hc; reg [(NL-2)*256-1:0] sum_hc;
    integer k;
    always @(posedge clk) begin
        sum_hb <= sum_hi; tag_hb <= tag_hi; tag_hc <= tag_hb;
        for (k = 0; k < NL - 2; k = k + 1) sum_hc[k*256 +: 256] <= sum_hb[k*512 + 256 +: 256];
    end
    genvar gk;
    generate for (gk = 0; gk < NL - 2; gk = gk + 1) begin : g_xs
        assign xs_out[gk*256 +: 256] = sum_hb[gk*512 +: 256];
    end endgenerate
    assign xt_out = tag_hb;
    wire c_pv, c_flt; wire [31:0] c_pd; wire [3:0] c_pw; wire [2:0] c_ps; wire [1:0] c_pl; wire [15:0] c_pt;
    ot_hnx_att4_smerge_h #(.NL(NL), .L(16), .TAGW(16), .ALAT(7), .LV(LV), .MUT(MUT), .HALF(1), .PH0(1)) u_h (
        .clk(clk), .rst_n(g2), .ev((MUT == 8) ? ev_g2 : ev_g), .sum({sum_hc, sum_g}), .tag_d({tag_hc, tag_g}),
        .pub_start(ps_g), .pub_lane(pl_g), .pub_slot(psl_g), .pub_v(c_pv), .pub_data(c_pd), .pub_word(c_pw),
        .pub_out_slot(c_ps), .pub_out_lane(c_pl), .pub_tag(c_pt), .fault(c_flt));
    // two pads = the N word's seam (N out reg + S in reg)
    reg p1_v, p2_v, p1_f, p2_f;
    (* keep = "true" *) reg p2_vb, p2_w3b;              // copies for the upper 16 bits of the output word mux
    reg [31:0] p1_d, p2_d; reg [3:0] p1_w, p2_w; reg [2:0] p1_s, p2_s;
    reg [1:0] p1_l, p2_l; reg [15:0] p1_t, p2_t;
    always @(posedge clk) begin
        p1_v <= c_pv; p1_f <= c_flt; p1_d <= c_pd; p1_w <= c_pw; p1_s <= c_ps; p1_l <= c_pl; p1_t <= c_pt;
        p2_v <= p1_v; p2_vb <= p1_v; p2_w3b <= p1_w[3]; p2_f <= p1_f; p2_d <= p1_d; p2_w <= p1_w; p2_s <= p1_s; p2_l <= p1_l; p2_t <= p1_t;
    end
    // S-face output pin registers
    always @(posedge clk or negedge g2)
        if (!g2) begin pub_v <= 1'b0; fault <= 1'b0; end
        else begin pub_v <= p2_v; fault <= fault | p2_f | flt_g; end
    always @(posedge clk) begin
        pub_word <= p2_w; pub_out_slot <= p2_s; pub_out_lane <= p2_l; pub_tag <= p2_t;
        if (p2_v)  pub_data[15:0]  <= (p2_w[3] ^ (MUT == 9)) ? p2_d[15:0]  : pd_g[15:0];
        if (p2_vb) pub_data[31:16] <= (p2_w3b  ^ (MUT == 9)) ? p2_d[31:16] : pd_g[31:16];
    end
endmodule

// Cluster parent (kind cluster): wires only; same ports as ot_hnx_att4_spvm.
module ot_hnx_att4_scl #(
    parameter integer NL  = 3,
    parameter integer LV  = 3,
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [NL-1:0]     ev,
    input  wire [1023:0]     sum_lo,
    input  wire [31:0]       tag_lo,
    input  wire [(NL-2)*512-1:0] sum_hi,
    input  wire [(NL-2)*16-1:0]  tag_hi,
    input  wire              pub_start,
    input  wire [1:0]        pub_lane,
    input  wire [2:0]        pub_slot,
    output wire              pub_v,
    output wire [31:0]       pub_data,
    output wire [3:0]        pub_word,
    output wire [2:0]        pub_out_slot,
    output wire [1:0]        pub_out_lane,
    output wire [15:0]       pub_tag,
    output wire              fault
);
    wire f_rst, f_ps, f_flt; wire [NL-1:0] f_ev; wire [511:0] f_sum; wire [31:0] f_tag, f_pd; wire [1:0] f_pl;
    wire [2:0] f_psl; wire [(NL-2)*256-1:0] xs; wire [(NL-2)*16-1:0] xt;
    ot_hnx_att4_sleaf_n #(.NL(NL), .LV(LV), .MUT(MUT)) u_n (
        .clk(clk), .rst_n(rst_n), .ev(ev), .sum_lo(sum_lo), .tag_lo(tag_lo), .pub_start(pub_start), .pub_lane(pub_lane),
        .pub_slot(pub_slot), .xs_in(xs), .xt_in(xt), .f_rst(f_rst), .f_ev(f_ev), .f_sum(f_sum), .f_tag(f_tag),
        .f_ps(f_ps), .f_pl(f_pl), .f_psl(f_psl), .f_pd(f_pd), .f_flt(f_flt));
    ot_hnx_att4_sleaf_s #(.NL(NL), .LV(LV), .MUT(MUT)) u_s (
        .clk(clk), .f_rst(f_rst), .f_ev(f_ev), .f_sum(f_sum), .f_tag(f_tag), .f_ps(f_ps), .f_pl(f_pl), .f_psl(f_psl),
        .f_pd(f_pd), .f_flt(f_flt), .sum_hi(sum_hi), .tag_hi(tag_hi), .xs_out(xs), .xt_out(xt), .pub_v(pub_v),
        .pub_data(pub_data), .pub_word(pub_word), .pub_out_slot(pub_out_slot), .pub_out_lane(pub_out_lane),
        .pub_tag(pub_tag), .fault(fault));
endmodule
`default_nettype wire
