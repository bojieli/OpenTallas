`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-SLICE (stream 0cm, 2026-10-17): vn = the h-resident + RMSNorm sub-leaf of one BEAT of a DV vector slice (p4: the
// slice is a cluster of 5 beat leaves; beat leaf k owns elements [64k, 64k+64) of the slice's 320, i.e. global element
// e = 320 g + 64 k + 8 j + l, sub-beat j = 0..7, lane l = 0..7).  One hardened master, x5 per slice, own clock root.
//
//   h store   4 HC copies x 64 elements BF16 in two ot_sram_1r1w_128x256 macros, one per half row (half hf = lanes
//             4 hf .. 4 hf + 3 of all 4 copies, 256 b; address = sub-beat j): written in half rows by vp (hc_post results /
//             stage h load), read in half rows by vp (hc_post residual operands) and both halves together by the norm.
//             The read port is shared (the norm's issue and vp's reads never overlap: compiler slots; overlap = fault).
//   norm      ONE ot_hbm_norm_grp G = 8 (the HBM norm group, unchanged arithmetic) run over the beat's 8 golden chunks as
//             8 sub-beats (D = 64, N = 8, NV = 8): per sub-beat the hc_pre mix of the 4 copies, the square and the
//             golden chunk-of-8 chain -> the chunk sum s_j; x waits in the group's x SRAM; the gains are loaded per norm
//             (wl, 8 rows of 8 lanes) by vp; after rstd (rb) the scale emits y_j = bf16(w * (x * r)) for j = 0..7.
//   beat tree the 3 golden pairwise levels above the 8 chunk sums (((s0+s1)+(s2+s3))+((s4+s5)+(s6+s7))): the beat is an
//             aligned 64-element subtree of the golden csum, so the result is bit-identical to the flat engine's (and
//             to G64's) beat partial.  One ot_dsrom_qadd walks the 7 nodes in dataflow order (operands and order fixed
//             per node: exact by construction).
// Pins: every input lands in a flop (robust first cell, no hold padding: FLOW-HOLD recipe 4 / hold_budget die); every
// output leaves a flop.  Reset: rst_n -> ot_rst_relay (regional synchronous release, replicated per region).
// Static schedule: no ready / credit; a second norm go while one is running, or a tree-node collision, is a sticky fault.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_vn #(
    parameter integer LM = 5,
    parameter integer LA = 6
) (
    input  wire          clk,
    input  wire          rst_n,
    // h half-row write (vp): copy k of lane 4*hw_hf + i at hw_d[(4k + i)*16 +: 16]
    input  wire          hw_v,
    input  wire [2:0]    hw_j,
    input  wire          hw_hf,
    input  wire [255:0]  hw_d,
    // h half-row read (vp): data two edges after the request at the output flops
    input  wire          hr_v,
    input  wire [2:0]    hr_j,
    input  wire          hr_hf,
    output reg           hq_v,
    output reg  [255:0]  hq_d,
    // norm: go with the hc_pre coefficients; gains (row i = lanes 0..7 of sub-beat i, FP32); rstd broadcast
    input  wire          n_go,
    input  wire [127:0]  n_pre,
    input  wire          wl_v,
    input  wire [2:0]    wl_i,
    input  wire [255:0]  wl_d,
    input  wire          rb_v,
    input  wire [31:0]   rb_d,
    // beat partial (to the xfin) and y (8 lanes, FP32 word holding the BF16 value)
    output reg           p_v,
    output reg  [31:0]   p_d,
    output reg           y_v,
    output reg  [2:0]    y_i,
    output reg  [255:0]  y,
    (* keep *) output reg           fault
);
    wire [3:0] rsv;
    ot_rst_relay #(.REGIONS(4), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_c = rsv[0], rs_g = rsv[1], rs_t = rsv[2], rs_o = rsv[3];

    // ---------------------------------------------------------------- input pin flops
    reg hw_v_c, hr_v_c, go_c, wl_v_c, rb_v_c;
    reg [2:0] hw_j_c, hr_j_c, wl_i_c; reg hw_hf_c, hr_hf_c;
    reg [255:0] hw_d_c, wl_d_c; reg [127:0] pre_in, pre_c; reg [31:0] rb_d_c;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin hw_v_c <= 1'b0; hr_v_c <= 1'b0; go_c <= 1'b0; wl_v_c <= 1'b0; rb_v_c <= 1'b0; end
        else begin hw_v_c <= hw_v; hr_v_c <= hr_v; go_c <= n_go; wl_v_c <= wl_v; rb_v_c <= rb_v; end
    always @(posedge clk) begin
        hw_j_c <= hw_j; hw_hf_c <= hw_hf; hw_d_c <= hw_d; hr_j_c <= hr_j; hr_hf_c <= hr_hf;
        pre_in <= n_pre;
        wl_i_c <= wl_i; wl_d_c <= wl_d; rb_d_c <= rb_d;
    end
    // NATIVE-SWEEP/NS-VN 10-18 (native capture n_go 205.4 > 190 on fa3312cfc): n_go used to be the load-enable of the
    // 128 pre_c flops (fanout 129 straight from the pin).  Now n_go lands in go_c alone (fanout 1) and n_pre in its own
    // pin flops pre_in; the coefficients move pre_in -> pre_c one edge later under the go_c enable.  pre_c is new one
    // edge before g_go, and the norm group first reads it with in_v (g_inv = run + 2 edges): 0 cycles on the schedule,
    // same values (the coefficients only change one edge later, never earlier).
    always @(posedge clk)
`ifdef OT_S81SL_MUT_PRESTALE
        // NEGATIVE CONTROL: the enable taken from the pin (n_go) one edge early -> pre_c takes the PREVIOUS coefficients
        if (n_go) pre_c <= pre_in;
`else
        if (go_c) pre_c <= pre_in;
`endif

    // ---------------------------------------------------------------- norm issue state (drives the h read port)
    reg       run; reg [2:0] nj; reg g_go, g_inv, g_inv0; reg [1023:0] g_x;
    integer i, k;
    // ---------------------------------------------------------------- h store: half 0 / half 1 macros, address j
    wire [255:0] hm0, hm1;
    wire         hre = hr_v_c || run;
    wire [6:0]   hra = run ? {4'd0, nj} : {4'd0, hr_j_c};
    ot_sram_1r1w_128x256_m1_r2c2 u_h0 (.clk(clk), .r_ce_in(hre && (run || !hr_hf_c)), .r_addr_in(hra), .rd_out(hm0),
        .w_ce_in(hw_v_c && !hw_hf_c), .w_addr_in({4'd0, hw_j_c}), .wd_in(hw_d_c), .w_mask_in({256{1'b1}}),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    ot_sram_1r1w_128x256_m1_r2c2 u_h1 (.clk(clk), .r_ce_in(hre && (run || hr_hf_c)), .r_addr_in(hra), .rd_out(hm1),
        .w_ce_in(hw_v_c && hw_hf_c), .w_addr_in({4'd0, hw_j_c}), .wd_in(hw_d_c), .w_mask_in({256{1'b1}}),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    // half-row read (vp): the macro output register is the output flop (pin flop, macro edge, output flop: 2 edges)
    reg hrv1, hrhf1;
    always @(posedge clk or negedge rs_o) if (!rs_o) begin hrv1 <= 1'b0; hq_v <= 1'b0; end
        else begin hrv1 <= hr_v_c && !run; hq_v <= hrv1; end
    always @(posedge clk) begin hrhf1 <= hr_hf_c; hq_d <= hrhf1 ? hm1 : hm0; end
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin run <= 1'b0; nj <= 3'd0; g_go <= 1'b0; g_inv0 <= 1'b0; g_inv <= 1'b0; end
        else begin
            g_go <= go_c;
            g_inv0 <= run;
            g_inv <= g_inv0;
            if (go_c) begin run <= 1'b1; nj <= 3'd0; end
            else if (run) begin nj <= nj + 3'd1; if (nj == 3'd7) run <= 1'b0; end
        end
    // in_x: copy k of lane l at [(8k + l)*32]: the BF16 h as its FP32 bit pattern (half row hf = lanes 4 hf + i at
    // (4k + i) * 16), registered from the macro outputs one edge after the read (g_inv follows run by 2 edges)
    always @(posedge clk)
        for (k = 0; k < 4; k = k + 1)
            for (i = 0; i < 4; i = i + 1) begin
                g_x[(8 * k + i) * 32 +: 32]     <= {hm0[(4 * k + i) * 16 +: 16], 16'd0};
                g_x[(8 * k + 4 + i) * 32 +: 32] <= {hm1[(4 * k + i) * 16 +: 16], 16'd0};
            end
    wire s_v, gy_v, gf; wire [7:0] s_i, gy_i; wire [31:0] s; wire [255:0] gy;
    ot_hbm_norm_grp #(.G(8), .D(64), .N(8), .LM(LM), .LA(LA)) u_g (.clk(clk), .rst_n(rs_g), .go(g_go), .in_v(g_inv),
        .in_x(g_x), .pre(pre_c), .wl_v(wl_v_c), .wl_i({5'd0, wl_i_c}), .wl_d(wl_d_c), .rb_v(rb_v_c), .rb_d(rb_d_c),
        .s_v(s_v), .s_i(s_i), .s(s), .y_v(gy_v), .y_i(gy_i), .y(gy), .gf(gf));

    // ---------------------------------------------------------------- beat tree: 7 nodes, one adder, dataflow issue
    // node n: 0..3 = level 1 (s[2n] + s[2n+1]), 4 = n0 + n1, 5 = n2 + n3, 6 = n4 + n5 (the beat partial)
    reg [31:0] lv [0:7];  reg [7:0] lp;   // chunk sums and their presence
    reg [31:0] nv [0:6];  reg [6:0] np, ni;   // node values / presence / issued
    wire [6:0] rdy;
`ifdef OT_S81SL_MUT_TREE
    // NEGATIVE CONTROL: level 1 pairs (s0 + s2), (s1 + s3) -- the golden association broken, same operands
    assign rdy[0] = &lp[3:0] & !ni[0];
    assign rdy[1] = &lp[3:0] & !ni[1];
`else
    assign rdy[0] = lp[0] & lp[1] & !ni[0];
    assign rdy[1] = lp[2] & lp[3] & !ni[1];
`endif
    assign rdy[2] = lp[4] & lp[5] & !ni[2];
    assign rdy[3] = lp[6] & lp[7] & !ni[3];
    assign rdy[4] = np[0] & np[1] & !ni[4];
    assign rdy[5] = np[2] & np[3] & !ni[5];
    assign rdy[6] = np[4] & np[5] & !ni[6];
    reg [2:0] sel; reg any;
    always @(*) begin
        any = |rdy; sel = 3'd0;
        for (i = 6; i >= 0; i = i - 1) if (rdy[i]) sel = i[2:0];
    end
    reg [31:0] ta, tb;
    always @(*) begin
        case (sel)
`ifdef OT_S81SL_MUT_TREE
            3'd0: begin ta = lv[0]; tb = lv[2]; end
            3'd1: begin ta = lv[1]; tb = lv[3]; end
`else
            3'd0: begin ta = lv[0]; tb = lv[1]; end
            3'd1: begin ta = lv[2]; tb = lv[3]; end
`endif
            3'd2: begin ta = lv[4]; tb = lv[5]; end
            3'd3: begin ta = lv[6]; tb = lv[7]; end
            3'd4: begin ta = nv[0]; tb = nv[1]; end
            3'd5: begin ta = nv[2]; tb = nv[3]; end
            default: begin ta = nv[4]; tb = nv[5]; end
        endcase
    end
    // issue register -> adder (LA) ; the node tag rides a matching delay line
    reg a_v; reg [2:0] a_n; reg [31:0] a_a, a_b;
    wire [31:0] a_y; wire a_f; wire [LA:0] avl; wire [2:0] a_no;
    always @(posedge clk or negedge rs_t)
        if (!rs_t) begin a_v <= 1'b0; lp <= 8'd0; np <= 7'd0; ni <= 7'd0; end
        else begin
            a_v <= any;
            if (go_c) begin lp <= 8'd0; np <= 7'd0; ni <= 7'd0; end
            else begin
                if (s_v) lp[s_i[2:0]] <= 1'b1;
                if (any) ni[sel] <= 1'b1;
                if (avl[LA]) np[a_no] <= 1'b1;
            end
        end
    always @(posedge clk) begin
        if (s_v) lv[s_i[2:0]] <= s;
        a_n <= sel; a_a <= ta; a_b <= tb;
        if (avl[LA]) nv[a_no] <= a_y;
    end
    ot_dsrom_qadd #(.LAT(LA)) u_add (clk, rs_t, a_v, a_a, a_b, a_y, a_f);
    ot_hdc_vline #(.D(LA)) u_avl (.clk(clk), .rst_n(rs_t), .v(a_v), .vd(avl));
    ot_hdc_delay #(.W(3), .D(LA)) u_ano (.clk(clk), .rst_n(rs_t), .d(a_n), .q(a_no));

    // ---------------------------------------------------------------- output flops and the sticky fault
    // S81-KITS-RTLA 10-24 (face_guard: register on every pin): the fault state lives in fault_s; the pin flop fault
    // is an output-only copy loaded with the SAME next value every edge (was: fault fed back into its own D).
    // 0 cycles, bit / cycle identical.  Both kept so opt_merge cannot fold them.
    (* keep *) reg fault_s;
    wire fault_n = go_c ? run                               // a go while the previous norm still issues
                 : (hr_v_c && run) ? 1'b1                   // a vp h read while the norm issues
                 : (gf || (avl[LA] && a_f) || (s_v && s_i > 8'd7)) ? 1'b1 : fault_s;
    always @(posedge clk or negedge rs_o)
        if (!rs_o) begin p_v <= 1'b0; y_v <= 1'b0; fault <= 1'b0; fault_s <= 1'b0; end
        else begin
            p_v <= avl[LA] && a_no == 3'd6;
            y_v <= gy_v;
            fault_s <= fault_n;
            fault <= fault_n;
        end
    always @(posedge clk) begin p_d <= a_y; y_i <= gy_i[2:0]; y <= gy; end
endmodule
