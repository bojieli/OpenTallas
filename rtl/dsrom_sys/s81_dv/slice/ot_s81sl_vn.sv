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
    output reg  [127:0]  y,              // packed BF16: y[16 k +: 16] = lane k (was [32 k + 16 +: 16] of a 256-bit
                                         // word whose low halves are constant 0; OWNER DECISION 8 (2026-10-24, S81-KITS-RTLA):)
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
    always @(posedge clk) begin p_d <= a_y; y_i <= gy_i[2:0];
        y <= {gy[255:240], gy[223:208], gy[191:176], gy[159:144], gy[127:112], gy[95:80], gy[63:48], gy[31:16]}; end
endmodule

// =====================================================================================================================
// S81/RTLSPLIT (2026-10-24, COORD C3 400k-cell cap: vn 385k cells, at the cap): ot_s81sl_vn cut into TWO hard cores along
// the lane halves the h store already has (plan: physical/die_plan/s81/cores/leaf/split.py, inputs/core_pins/
// ot_s81sl_vn_{a,b}.json).  The norm group ot_hbm_norm_grp G = 8 (D = 64, N = 8, NV = 8) is re-cut by lane:
//   ot_s81sl_vn_a  lanes 0..3: h half 0 macro, norm lanes 0..3 (hc_pre mix, square, x / w stores, scale x*r*w), the
//                  golden chunk-of-8 chain adders 1..3 -> the chain partial acc3 leaves on c_v / c_s (output flops;
//                  c_s[30:0]: acc3 is a sum of squares, its sign bit is constant 0 and dropped, OWNER DECISION 8),
//                  y lanes 0..3; replicated pin flops, norm sequencer and group control.
//   ot_s81sl_vn_b  lanes 4..7: h half 1 macro, norm lanes 4..7, chain adders 4..7 (acc3 from c_s through its pin flop;
//                  lane 4..7 squares delayed +2 to match), beat tree, p; y lanes 4..7 + y_v / y_i; replicated control.
//   ot_s81sl_vn_sp the leaf's u_vn (instances u_a / u_b): the ot_s81sl_vn ports; hq_d = hq_d_a | hq_d_b (each half
//                  answers its own half row, 0 for the other), hq_v / fault ORed -- the only glue.
// Both halves take hw_* (each writes its half), hr_* (each answers its half), n_go / n_pre / rb_* (broadcast), wl_v /
// wl_i and their 4-lane half of wl_d.
// Cost: +2 cycles on the norm partial p only (c_s output flop + pin flop): the chain sum s, its index and valid, the
// tree (its go clear delayed 2 alike) and p_v / p_d are r-old's exactly 2 edges later.  y / y_v / y_i, hq and the h
// writes are unchanged, edge for edge.  Arithmetic and association are the group's (ot_dsrom_su_norm_mix, qmul_lat,
// ot_dsrom_qadd chain in golden order, same issue offsets + 2).
// x / w stores: NV = 8 words a lane -> an 8-word flop register file per half (one-hot write, AND-OR read, registered
// read, read-before-write) in place of the half-empty 128 x 256 macro (8 of 128 words used); same read latency.
// Static schedule (no ready / credit); reset: ot_rst_relay regions + the group's replicated region flops, control
// state only.  Every partition pin is registered on both sides.
// Bench only: OT_S81SL_MUT_TREE / OT_S81SL_MUT_PRESTALE as r-old; OT_S81SL_SPMUT_C1 = vn_b chains from the c_s PIN (no
// pin flop: 1 edge early); OT_S81SL_SPMUT_HQ = vn_a answers hr_hf = 1 reads too (hq_d OR corrupted).
// =====================================================================================================================

// 8-word register file, W bits, 7-bit addresses as the macro (words >= 8: never written, read 0)
module ot_s81sl_vn_rf8 #(parameter integer W = 128) (
    input  wire         clk,
    input  wire         we,
    input  wire [6:0]   wa,
    input  wire [W-1:0] wd,
    input  wire [6:0]   ra,
    output reg  [W-1:0] q
);
    reg [W-1:0] m [0:7];
    reg [W-1:0] rd;
    integer r;
    always @(posedge clk)
        for (r = 0; r < 8; r = r + 1) if (we && wa == r[6:0]) m[r] <= wd;
    always @* begin
        rd = {W{1'b0}};
        for (r = 0; r < 8; r = r + 1) rd = rd | (m[r] & {W{ra == r[6:0]}});
    end
    always @(posedge clk) q <= rd;
`ifndef SYNTHESIS
    initial for (r = 0; r < 8; r = r + 1) m[r] = {W{1'b0}};       // the macro model's power-up content
`endif
endmodule

// Four lanes of ot_hbm_norm_grp (G = 8, D = 64, N = 8): group pin flops, control (replicated per half), mix / square /
// scale lanes, x / w stores.  The chunk chain lives in the core tops (vn_a: adders 1..3, vn_b: 4..7).
module ot_s81sl_vn_ng4 #(
    parameter integer D = 64, N = 8, LM = 5, LA = 6, SXC = 1
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          go,
    input  wire          in_v,
    input  wire [511:0]  in_x,       // copy k of local lane l at [(4k + l)*32 +: 32]
    input  wire [127:0]  pre,
    input  wire          wl_v,
    input  wire [2:0]    wl_i,
    input  wire [127:0]  wl_d,
    input  wire          rb_v,
    input  wire [31:0]   rb_d,
    output wire          go_q,       // the group's go pin flop (fault clears)
    output wire          x_v,        // x valid (the squares follow by LM)
    output wire [7:0]    xi,
    output wire [127:0]  sq,
    output wire [127:0]  y,          // bf16 (upper half) per lane
    output wire          y_v,
    output wire [7:0]    y_i,
    output wire [3:0]    lf
);
    localparam integer NV  = D / N;
    localparam integer DM  = LM + 3 * LA + 1;
    localparam integer LMS = LM + SXC;
    localparam integer DY  = 2 * LMS + 1;
    function automatic [31:0] bf16(input [31:0] x);
        reg [32:0] t;
        begin
            t = {1'b0, x} + 33'h7FFF + {32'd0, x[16]};
            bf16 = {t[31:16], 16'd0};
        end
    endfunction
    // region flops (as the group's): [0] control, [1 + 2l] lane l mix / square, [2 + 2l] lane l scale
    localparam integer NR = 9;
    (* keep = "true", dont_touch = "true" *) reg [NR-1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= {NR{1'b0}}; else rs <= {NR{1'b1}};
    wire rstn = rs[0];
    reg go_c, in_v_c, wl_v_c, rb_v_c; reg [2:0] wl_i_c; reg [511:0] x_c; reg [127:0] pre_c;
    reg [127:0] wl_d_c; reg [31:0] rb_d_c;
    always @(posedge clk) begin
        go_c <= go; in_v_c <= in_v; wl_v_c <= wl_v; rb_v_c <= rb_v;
        wl_i_c <= wl_i; x_c <= in_x; pre_c <= pre; wl_d_c <= wl_d; rb_d_c <= rb_d;
    end
    assign go_q = go_c;
    reg [7:0] in_i;
    always @(posedge clk or negedge rstn)
        if (!rstn) in_i <= 8'd0;
        else if (go_c) in_i <= 8'd0;
        else if (in_v_c) in_i <= in_i + 8'd1;
    wire [DM:0] vm;
    ot_hdc_vline #(.D(DM)) u_vm (.clk(clk), .rst_n(rstn), .v(in_v_c), .vd(vm));
    ot_hdc_delay #(.W(8), .D(DM)) u_xi (.clk(clk), .rst_n(rstn), .d(in_i), .q(xi));
    assign x_v = vm[DM];
    reg         rbv;
    reg  [31:0] rh;
    always @(posedge clk or negedge rstn) if (!rstn) rbv <= 1'b0; else rbv <= rb_v_c;
    always @(posedge clk) if (rb_v_c) rh <= rb_d_c;
    reg         sc_run;
    reg  [7:0]  sc_i;
    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin sc_run <= 1'b0; sc_i <= 8'd0; end
        else if (rbv) begin sc_run <= (NV > 1); sc_i <= 8'd1; end
        else if (sc_run) begin
            if (sc_i == NV - 1) sc_run <= 1'b0;
            sc_i <= sc_i + 8'd1;
        end
    end
    wire        sc_go = rbv || sc_run;
    wire [7:0]  sc_x  = rbv ? 8'd0 : sc_i;
    wire [7:0]  sc_nx = rbv ? 8'd1 : sc_run ? sc_i + 8'd1 : 8'd0;
    wire        sc_run_n = rbv ? (NV > 1) : (sc_run && sc_i != NV - 1);
    wire [7:0]  sc_i_n   = rbv ? 8'd1 : sc_run ? sc_i + 8'd1 : sc_i;
    wire [7:0]  sc_nn    = rb_v_c ? 8'd1 : sc_run_n ? sc_i_n + 8'd1 : 8'd0;
    wire [DY:0] vy;
    ot_hdc_vline #(.D(DY)) u_vy (.clk(clk), .rst_n(rstn), .v(sc_go), .vd(vy));
    wire [7:0] yi_mm;
    ot_hdc_delay #(.W(8), .D(LMS > 1 ? LMS - 1 : 1)) u_yimm (.clk(clk), .rst_n(rstn), .d(sc_nx), .q(yi_mm));
    ot_hdc_delay #(.W(8), .D(DY)) u_yio (.clk(clk), .rst_n(rstn), .d(sc_x), .q(y_i));
    assign y_v = vy[DY];

    wire [127:0] xl_all, xmq, wmq;
    ot_s81sl_vn_rf8 #(.W(128)) u_x (.clk(clk), .we(x_v), .wa(xi[6:0]), .wd(xl_all), .ra(sc_nn[6:0]), .q(xmq));
    ot_s81sl_vn_rf8 #(.W(128)) u_w (.clk(clk), .we(wl_v_c), .wa({4'd0, wl_i_c}), .wd(wl_d_c), .ra(yi_mm[6:0]), .q(wmq));
    genvar l;
    generate for (l = 0; l < 4; l = l + 1) begin : g_lane
        wire [31:0] xl;
        wire [3:0] f;
        ot_dsrom_su_norm_mix #(.LM(LM), .LA(LA)) u_mix (.clk(clk), .rst_n(rs[1 + 2 * l]), .v(in_v_c),
            .h0(x_c[(0 * 4 + l) * 32 +: 32]), .h1(x_c[(1 * 4 + l) * 32 +: 32]),
            .h2(x_c[(2 * 4 + l) * 32 +: 32]), .h3(x_c[(3 * 4 + l) * 32 +: 32]), .pre(pre_c), .x(xl), .fault(f[0]));
        assign xl_all[l * 32 +: 32] = xl;
        reg [31:0] xo, wo;                       // store output registers (the macro output registers in the group)
        always @(posedge clk) begin xo <= xmq[l * 32 +: 32]; wo <= wmq[l * 32 +: 32]; end
        ot_hdc_qmul_lat #(LM) u_sq (clk, rs[1 + 2 * l], x_v, xl, xl, sq[l * 32 +: 32], f[1]);
        wire [31:0] p, q;
        ot_hdc_qmul_lat #(LMS) u_xr (clk, rs[2 + 2 * l], sc_go, xo, rh, p, f[2]);
        ot_hdc_qmul_lat #(LMS) u_w  (clk, rs[2 + 2 * l], vy[LMS], wo, p, q, f[3]);
        reg [31:0] yr;
        always @(posedge clk) yr <= bf16(q);
        assign y[l * 32 +: 32] = yr;
        assign lf[l] = |f;
    end endgenerate
endmodule

module ot_s81sl_vn_a #(
    parameter integer LM = 5,
    parameter integer LA = 6
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          hw_v,
    input  wire [2:0]    hw_j,
    input  wire          hw_hf,
    input  wire [255:0]  hw_d,
    input  wire          hr_v,
    input  wire [2:0]    hr_j,
    input  wire          hr_hf,
    output reg           hq_v,
    output reg  [255:0]  hq_d,           // half row 0 when hr_hf = 0, else 0 (the leaf ORs vn_b's)
    input  wire          wl_v,
    input  wire [2:0]    wl_i,
    input  wire [127:0]  wl_d,           // lanes 0..3 of the gain row
    input  wire          n_go,
    input  wire [127:0]  n_pre,
    input  wire          rb_v,
    input  wire [31:0]   rb_d,
    output reg  [63:0]   y,              // packed BF16 lanes 0..3
    output reg           c_v,            // chain partial acc3 (lanes 0..3) -> vn_b
    output reg  [30:0]   c_s,            // [31] (sign of a sum of squares) is constant 0: dropped (OWNER DECISION 8)
    (* keep *) output reg fault
);
    localparam integer DC = LM + 3 * LA;     // acc3 valid on the x-valid line
    wire [2:0] rsv;
    ot_rst_relay #(.REGIONS(3), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_c = rsv[0], rs_g = rsv[1], rs_o = rsv[2];

    reg hw_v_c, hr_v_c, go_c, wl_v_c, rb_v_c;
    reg [2:0] hw_j_c, hr_j_c, wl_i_c; reg hw_hf_c, hr_hf_c;
    reg [255:0] hw_d_c; reg [127:0] wl_d_c; reg [127:0] pre_in, pre_c; reg [31:0] rb_d_c;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin hw_v_c <= 1'b0; hr_v_c <= 1'b0; go_c <= 1'b0; wl_v_c <= 1'b0; rb_v_c <= 1'b0; end
        else begin hw_v_c <= hw_v; hr_v_c <= hr_v; go_c <= n_go; wl_v_c <= wl_v; rb_v_c <= rb_v; end
    always @(posedge clk) begin
        hw_j_c <= hw_j; hw_hf_c <= hw_hf; hw_d_c <= hw_d; hr_j_c <= hr_j; hr_hf_c <= hr_hf;
        pre_in <= n_pre;
        wl_i_c <= wl_i; wl_d_c <= wl_d; rb_d_c <= rb_d;
    end
    always @(posedge clk)
`ifdef OT_S81SL_MUT_PRESTALE
        if (n_go) pre_c <= pre_in;
`else
        if (go_c) pre_c <= pre_in;
`endif

    reg run; reg [2:0] nj; reg g_go, g_inv, g_inv0; reg [511:0] g_x;
    integer i, k;
    wire [255:0] hm0;
    wire         hre = hr_v_c || run;
    wire [6:0]   hra = run ? {4'd0, nj} : {4'd0, hr_j_c};
    ot_sram_1r1w_128x256_m1_r2c2 u_h0 (.clk(clk), .r_ce_in(hre && (run || !hr_hf_c)), .r_addr_in(hra), .rd_out(hm0),
        .w_ce_in(hw_v_c && !hw_hf_c), .w_addr_in({4'd0, hw_j_c}), .wd_in(hw_d_c), .w_mask_in({256{1'b1}}),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    reg hrv1, hrhf1;
    always @(posedge clk or negedge rs_o) if (!rs_o) begin hrv1 <= 1'b0; hq_v <= 1'b0; end
        else begin hrv1 <= hr_v_c && !run; hq_v <= hrv1; end
`ifdef OT_S81SL_SPMUT_HQ
    always @(posedge clk) begin hrhf1 <= hr_hf_c; hq_d <= hm0; end      // NEGATIVE CONTROL: answers the other half too
`else
    always @(posedge clk) begin hrhf1 <= hr_hf_c; hq_d <= hm0 & {256{!hrhf1}}; end
`endif
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin run <= 1'b0; nj <= 3'd0; g_go <= 1'b0; g_inv0 <= 1'b0; g_inv <= 1'b0; end
        else begin
            g_go <= go_c;
            g_inv0 <= run;
            g_inv <= g_inv0;
            if (go_c) begin run <= 1'b1; nj <= 3'd0; end
            else if (run) begin nj <= nj + 3'd1; if (nj == 3'd7) run <= 1'b0; end
        end
    always @(posedge clk)
        for (k = 0; k < 4; k = k + 1)
            for (i = 0; i < 4; i = i + 1)
                g_x[(4 * k + i) * 32 +: 32] <= {hm0[(4 * k + i) * 16 +: 16], 16'd0};

    wire gq, x_v, gy_v; wire [7:0] xi, gy_i; wire [127:0] sq, gy; wire [3:0] lf;
    ot_s81sl_vn_ng4 #(.D(64), .N(8), .LM(LM), .LA(LA)) u_g (.clk(clk), .rst_n(rs_g), .go(g_go), .in_v(g_inv), .in_x(g_x),
        .pre(pre_c), .wl_v(wl_v_c), .wl_i(wl_i_c), .wl_d(wl_d_c), .rb_v(rb_v_c), .rb_d(rb_d_c), .go_q(gq), .x_v(x_v),
        .xi(xi), .sq(sq), .y(gy), .y_v(gy_v), .y_i(gy_i), .lf(lf));

    // ---- chunk chain, lanes 0..3: acc0 = sq0, adder k (1..3) at vs[LM + LA (k - 1)] (the group's offsets)
    (* keep = "true", dont_touch = "true" *) reg [3:0] rc;     // [0] chain control, [k] stage k
    always @(posedge clk or negedge rs_g) if (!rs_g) rc <= 4'd0; else rc <= 4'hf;
    wire [DC:0] vs;
    ot_hdc_vline #(.D(DC)) u_vs (.clk(clk), .rst_n(rc[0]), .v(x_v), .vd(vs));
    wire [31:0] acc [0:3];
    wire [3:0]  cf;
    assign acc[0] = sq[31:0];
    assign cf[0] = 1'b0;
    genvar gk;
    generate for (gk = 1; gk < 4; gk = gk + 1) begin : g_j
        wire [31:0] sd;
        ot_hdc_delay #(.W(32), .D(LA * (gk - 1))) u_sd (.clk(clk), .rst_n(rc[gk]), .d(sq[gk * 32 +: 32]), .q(sd));
        ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rc[gk], vs[LM + LA * (gk - 1)], acc[gk - 1], sd, acc[gk], cf[gk]);
    end endgenerate
    // partition output flops toward vn_b (+1 edge)
    always @(posedge clk or negedge rs_o) if (!rs_o) c_v <= 1'b0; else c_v <= vs[DC];
    always @(posedge clk) c_s <= acc[3][30:0];

    // group fault (as the group's gf_o: lane faults one edge late, cleared by its go)
    reg [3:0] lf_r; reg gf;
    always @(posedge clk or negedge rc[0])
        if (!rc[0]) begin lf_r <= 4'd0; gf <= 1'b0; end
        else begin
            lf_r <= gq ? 4'd0 : lf;
            gf <= gq ? 1'b0 : ((|lf_r) || (|cf));
        end

    (* keep *) reg fault_s;
    wire fault_n = go_c ? run : (hr_v_c && run) ? 1'b1 : gf ? 1'b1 : fault_s;
    always @(posedge clk or negedge rs_o)
        if (!rs_o) begin fault <= 1'b0; fault_s <= 1'b0; end
        else begin fault_s <= fault_n; fault <= fault_n; end
    always @(posedge clk) y <= {gy[127:112], gy[95:80], gy[63:48], gy[31:16]};
endmodule

module ot_s81sl_vn_b #(
    parameter integer LM = 5,
    parameter integer LA = 6
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          hw_v,
    input  wire [2:0]    hw_j,
    input  wire          hw_hf,
    input  wire [255:0]  hw_d,
    input  wire          hr_v,
    input  wire [2:0]    hr_j,
    input  wire          hr_hf,
    output reg           hq_v,
    output reg  [255:0]  hq_d,           // half row 1 when hr_hf = 1, else 0 (the leaf ORs vn_a's)
    input  wire          wl_v,
    input  wire [2:0]    wl_i,
    input  wire [127:0]  wl_d,           // lanes 4..7 of the gain row
    input  wire          n_go,
    input  wire [127:0]  n_pre,
    input  wire          rb_v,
    input  wire [31:0]   rb_d,
    input  wire          c_v,            // chain partial acc3 from vn_a
    input  wire [30:0]   c_s,            // acc3 magnitude: its sign is constant 0 (OWNER DECISION 8)
    output reg           p_v,
    output reg  [31:0]   p_d,
    output reg           y_v,
    output reg  [2:0]    y_i,
    output reg  [63:0]   y,              // packed BF16 lanes 4..7
    (* keep *) output reg fault
);
    localparam integer DC = LM + 3 * LA + 2;     // acc3 at vn_b's chain (2 partition flops)
    localparam integer DS = LM + 7 * LA + 2;     // chain sum (group DS + 2)
    wire [3:0] rsv;
    ot_rst_relay #(.REGIONS(4), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_c = rsv[0], rs_g = rsv[1], rs_t = rsv[2], rs_o = rsv[3];

    reg hw_v_c, hr_v_c, go_c, wl_v_c, rb_v_c;
    reg [2:0] hw_j_c, hr_j_c, wl_i_c; reg hw_hf_c, hr_hf_c;
    reg [255:0] hw_d_c; reg [127:0] wl_d_c; reg [127:0] pre_in, pre_c; reg [31:0] rb_d_c;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin hw_v_c <= 1'b0; hr_v_c <= 1'b0; go_c <= 1'b0; wl_v_c <= 1'b0; rb_v_c <= 1'b0; end
        else begin hw_v_c <= hw_v; hr_v_c <= hr_v; go_c <= n_go; wl_v_c <= wl_v; rb_v_c <= rb_v; end
    always @(posedge clk) begin
        hw_j_c <= hw_j; hw_hf_c <= hw_hf; hw_d_c <= hw_d; hr_j_c <= hr_j; hr_hf_c <= hr_hf;
        pre_in <= n_pre;
        wl_i_c <= wl_i; wl_d_c <= wl_d; rb_d_c <= rb_d;
    end
    always @(posedge clk)
`ifdef OT_S81SL_MUT_PRESTALE
        if (n_go) pre_c <= pre_in;
`else
        if (go_c) pre_c <= pre_in;
`endif
    // partition pin flops from vn_a (+1 edge)
    reg c_v_q; reg [30:0] c_s_q;
    always @(posedge clk or negedge rs_c) if (!rs_c) c_v_q <= 1'b0; else c_v_q <= c_v;
    always @(posedge clk) c_s_q <= c_s;

    reg run; reg [2:0] nj; reg g_go, g_inv, g_inv0; reg [511:0] g_x;
    integer i, k;
    wire [255:0] hm1;
    wire         hre = hr_v_c || run;
    wire [6:0]   hra = run ? {4'd0, nj} : {4'd0, hr_j_c};
    ot_sram_1r1w_128x256_m1_r2c2 u_h1 (.clk(clk), .r_ce_in(hre && (run || hr_hf_c)), .r_addr_in(hra), .rd_out(hm1),
        .w_ce_in(hw_v_c && hw_hf_c), .w_addr_in({4'd0, hw_j_c}), .wd_in(hw_d_c), .w_mask_in({256{1'b1}}),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    reg hrv1, hrhf1;
    always @(posedge clk or negedge rs_o) if (!rs_o) begin hrv1 <= 1'b0; hq_v <= 1'b0; end
        else begin hrv1 <= hr_v_c && !run; hq_v <= hrv1; end
    always @(posedge clk) begin hrhf1 <= hr_hf_c; hq_d <= hm1 & {256{hrhf1}}; end
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin run <= 1'b0; nj <= 3'd0; g_go <= 1'b0; g_inv0 <= 1'b0; g_inv <= 1'b0; end
        else begin
            g_go <= go_c;
            g_inv0 <= run;
            g_inv <= g_inv0;
            if (go_c) begin run <= 1'b1; nj <= 3'd0; end
            else if (run) begin nj <= nj + 3'd1; if (nj == 3'd7) run <= 1'b0; end
        end
    always @(posedge clk)
        for (k = 0; k < 4; k = k + 1)
            for (i = 0; i < 4; i = i + 1)
                g_x[(4 * k + i) * 32 +: 32] <= {hm1[(4 * k + i) * 16 +: 16], 16'd0};

    wire gq, x_v, gy_v; wire [7:0] xi, gy_i; wire [127:0] sq, gy; wire [3:0] lf;
    ot_s81sl_vn_ng4 #(.D(64), .N(8), .LM(LM), .LA(LA)) u_g (.clk(clk), .rst_n(rs_g), .go(g_go), .in_v(g_inv), .in_x(g_x),
        .pre(pre_c), .wl_v(wl_v_c), .wl_i(wl_i_c), .wl_d(wl_d_c), .rb_v(rb_v_c), .rb_d(rb_d_c), .go_q(gq), .x_v(x_v),
        .xi(xi), .sq(sq), .y(gy), .y_v(gy_v), .y_i(gy_i), .lf(lf));

    // ---- chunk chain, lanes 4..7: adder k (4..7) at vs[LM + LA (k - 1) + 2], operand acc3 = c_s through its pin flop,
    // lane k's square delayed LA (k - 1) + 2
    (* keep = "true", dont_touch = "true" *) reg [4:0] rc;     // [0] chain control / output, [1 + j] stage 4 + j
    always @(posedge clk or negedge rs_g) if (!rs_g) rc <= 5'd0; else rc <= 5'h1f;
    wire [DS:0] vs;
    ot_hdc_vline #(.D(DS)) u_vs (.clk(clk), .rst_n(rc[0]), .v(x_v), .vd(vs));
    wire [7:0] si;
    ot_hdc_delay #(.W(8), .D(DS)) u_si (.clk(clk), .rst_n(rc[0]), .d(xi), .q(si));
    wire [31:0] acc [0:4];
    wire [4:0]  cf;
`ifdef OT_S81SL_SPMUT_C1
    assign acc[0] = {1'b0, c_s};           // NEGATIVE CONTROL: acc3 from the pin, one edge early
`else
    assign acc[0] = {1'b0, c_s_q};          // acc3 >= 0: a sum of squares
`endif
    // lockstep: vn_a's acc3 valid must land on vn_b's own chain slot
    assign cf[0] = c_v_q != vs[DC];
    genvar gj;
    generate for (gj = 0; gj < 4; gj = gj + 1) begin : g_j
        wire [31:0] sd;
        ot_hdc_delay #(.W(32), .D(LA * (gj + 3) + 2)) u_sd (.clk(clk), .rst_n(rc[1 + gj]), .d(sq[gj * 32 +: 32]), .q(sd));
        ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rc[1 + gj], vs[LM + LA * (gj + 3) + 2], acc[gj], sd, acc[gj + 1], cf[gj + 1]);
    end endgenerate
    reg s_v; reg [7:0] s_i; reg [31:0] s;
    always @(posedge clk or negedge rc[0]) if (!rc[0]) s_v <= 1'b0; else s_v <= vs[DS];
    always @(posedge clk) begin s_i <= si; s <= acc[4]; end

    reg [3:0] lf_r; reg gf;
    always @(posedge clk or negedge rc[0])
        if (!rc[0]) begin lf_r <= 4'd0; gf <= 1'b0; end
        else begin
            lf_r <= gq ? 4'd0 : lf;
            gf <= gq ? 1'b0 : ((|lf_r) || (|cf));
        end

    // ---------------------------------------------------------------- beat tree (r-old's, 2 edges late: go clear too)
    reg [1:0] go_d;
    always @(posedge clk or negedge rs_t) if (!rs_t) go_d <= 2'd0; else go_d <= {go_d[0], go_c};
    wire go_t = go_d[1];
    reg [31:0] lv [0:7];  reg [7:0] lp;
    reg [31:0] nv [0:6];  reg [6:0] np, ni;
    wire [6:0] rdy;
`ifdef OT_S81SL_MUT_TREE
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
    reg a_v; reg [2:0] a_n; reg [31:0] a_a, a_b;
    wire [31:0] a_y; wire a_f; wire [LA:0] avl; wire [2:0] a_no;
    always @(posedge clk or negedge rs_t)
        if (!rs_t) begin a_v <= 1'b0; lp <= 8'd0; np <= 7'd0; ni <= 7'd0; end
        else begin
            a_v <= any;
            if (go_t) begin lp <= 8'd0; np <= 7'd0; ni <= 7'd0; end
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

    (* keep *) reg fault_s;
    wire fault_n = go_c ? run
                 : (hr_v_c && run) ? 1'b1
                 : (gf || (avl[LA] && a_f) || (s_v && s_i > 8'd7)) ? 1'b1 : fault_s;
    always @(posedge clk or negedge rs_o)
        if (!rs_o) begin p_v <= 1'b0; y_v <= 1'b0; fault <= 1'b0; fault_s <= 1'b0; end
        else begin
            p_v <= avl[LA] && a_no == 3'd6;
            y_v <= gy_v;
            fault_s <= fault_n;
            fault <= fault_n;
        end
    always @(posedge clk) begin p_d <= a_y; y_i <= gy_i[2:0];
        y <= {gy[127:112], gy[95:80], gy[63:48], gy[31:16]}; end
endmodule

module ot_s81sl_vn_sp #(
    parameter integer LM = 5,
    parameter integer LA = 6
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          hw_v,
    input  wire [2:0]    hw_j,
    input  wire          hw_hf,
    input  wire [255:0]  hw_d,
    input  wire          hr_v,
    input  wire [2:0]    hr_j,
    input  wire          hr_hf,
    output wire          hq_v,
    output wire [255:0]  hq_d,
    input  wire          n_go,
    input  wire [127:0]  n_pre,
    input  wire          wl_v,
    input  wire [2:0]    wl_i,
    input  wire [255:0]  wl_d,
    input  wire          rb_v,
    input  wire [31:0]   rb_d,
    output wire          p_v,
    output wire [31:0]   p_d,
    output wire          y_v,
    output wire [2:0]    y_i,
    output wire [127:0]  y,
    output wire          fault
);
    wire hqv_a, hqv_b, f_a, f_b, c_v; wire [255:0] hqd_a, hqd_b; wire [30:0] c_s; wire [63:0] y_a, y_b;
    ot_s81sl_vn_a #(.LM(LM), .LA(LA)) u_a (.clk(clk), .rst_n(rst_n), .hw_v(hw_v), .hw_j(hw_j), .hw_hf(hw_hf), .hw_d(hw_d),
        .hr_v(hr_v), .hr_j(hr_j), .hr_hf(hr_hf), .hq_v(hqv_a), .hq_d(hqd_a), .wl_v(wl_v), .wl_i(wl_i), .wl_d(wl_d[127:0]),
        .n_go(n_go), .n_pre(n_pre), .rb_v(rb_v), .rb_d(rb_d), .y(y_a), .c_v(c_v), .c_s(c_s), .fault(f_a));
    ot_s81sl_vn_b #(.LM(LM), .LA(LA)) u_b (.clk(clk), .rst_n(rst_n), .hw_v(hw_v), .hw_j(hw_j), .hw_hf(hw_hf), .hw_d(hw_d),
        .hr_v(hr_v), .hr_j(hr_j), .hr_hf(hr_hf), .hq_v(hqv_b), .hq_d(hqd_b), .wl_v(wl_v), .wl_i(wl_i), .wl_d(wl_d[255:128]),
        .n_go(n_go), .n_pre(n_pre), .rb_v(rb_v), .rb_d(rb_d), .c_v(c_v), .c_s(c_s), .p_v(p_v), .p_d(p_d),
        .y_v(y_v), .y_i(y_i), .y(y_b), .fault(f_b));
    assign hq_v = hqv_a | hqv_b;
    assign hq_d = hqd_a | hqd_b;
    assign y = {y_b, y_a};
    assign fault = f_a | f_b;
endmodule
