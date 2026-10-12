`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// el1011-ds-misc/pqc 2026-10-11: the hardened sub-tiles of the DS-ROM PQ spine (ot_v41_spine_pqc_w17w10 v15-hier).
// Textbook audit class 1: the flat spine screen put one clock tree over 133k (R16) / 225k (R128) sinks (CTS hold stuck
// at -65 ps for 8 h).  v15 cuts the spine, cycle for cycle and bit for bit, into tiles with their own clock trees and
// reset relays; every seam is register to register (the cut follows existing registers, no added cycle):
//   ot_dsrom_aq12t   T_AQ  x2       FP8 quantiser, the x wait line in an SRAM ring (physical/s81_pq_tiles)
//   ot_v41_pqc_ix    T_IX  x4       BF16 x buffer partition kl in [4g, 4g+3] + its 16 read lanes (bb / bra / bt_d)
//   ot_v41_pqc_qb    T_QB  x1       FP8 x buffer qb / eb, its write decode and the qb / eb read (bt_q0/q1/e0/e1)
//   ot_v41_pqc_ret   T_RET x R/8    one return group of 8 regions (repeaters, stages 0-3, group fault, row popcount)
//   ot_v41_pqc_bcrel T_BC  x BST+RPT one broadcast relay stage (data unreset; only the valid / config bits reset)
//   ot_v41_pqc_ctl   T_CTL x1       op slots, loader, stream-ROM reader, streamer, beat control, row totals
// Datapath registers carry no reset; each tile resets its control flops from its own ot_rst_relay (2 sync + 1 tree).
// ---------------------------------------------------------------------------

// T_IX: the BF16 x-buffer words whose address bits [6:3] (the read lane index kl) lie in [4g, 4g+3], i.e. the blocks of
// parity `par` (= kl[3] = g[1]) and the words kw in [32 g[0], 32 g[0] + 31] (wired in as xw), and the 16 read lanes
// (ku 0..3) x (kl 4g..4g+3).  Same registers as the flat spine: ba (x high half + rounding increment), bwe copies (8 of
// its 16), bw_d (rounded), the buffer, the g_ixb row-index copies (8 of 32), bra, the g_ixc copies (16 of 64), bt_d.
module ot_v41_pqc_ix #(
    parameter integer KMAX = 6144,
    parameter integer VRD = 64,
    parameter integer WBW = $clog2(2 * KMAX / VRD)
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            par,              // the block parity this tile holds (tie: g[1])
    input  wire [1023:0]   xw,               // x_q words 32 g[0] .. 32 g[0] + 31
    input  wire            ba_v,             // the spine's BF16 write stage A (registers)
    input  wire [WBW-1:0]  ba_blk,
    input  wire [35:0]     h_hi,             // the streamer head's row indices (registers)
    input  wire [6:0]      hw7,              // the head word bits [7:1]
    output wire [255:0]    bt_d              // lane (ku, kl - 4g) at [64 ku + 16 (kl - 4g) +: 16]
);
    localparam integer NWB = 2 * KMAX / VRD;
    localparam integer PE = KMAX / 8;        // words per read lane index kl
    wire [0:0] rst_l;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rst_l));
    integer k;
    // stage A: x high half and rounding increment (the flat spine's ba_hi / ba_inc for these 32 words)
    reg [511:0] ba_hi;
    reg [31:0]  ba_inc;
    always @(posedge clk)
        for (k = 0; k < 32; k = k + 1) begin
            ba_hi[16*k +: 16] <= xw[32*k + 16 +: 16];
            ba_inc[k] <= xw[32*k + 15] & ((xw[32*k +: 15] != 15'd0) | xw[32*k + 16]);
        end
    // stage B: block enables (8 kept copies, one per 4 words) and the rounded words
    reg  [NWB-1:0] bwe_d;
    always @* for (k = 0; k < NWB; k = k + 1) bwe_d[k] = ba_v && (ba_blk == WBW'(k));
    wire [8*NWB-1:0] bwe;
    wire [511:0] bw_rn;
    reg  [511:0] bw_d;
    genvar gc;
    generate for (gc = 0; gc < 8; gc = gc + 1) begin : g_bwb
        ot_v41_kreg #(.W(NWB), .AR(1)) u_bwb (.clk(clk), .arst_n(rst_l[0]), .d(bwe_d), .q(bwe[NWB*gc +: NWB]));
    end
    for (gc = 0; gc < 32; gc = gc + 1) begin : g_rn
        ot_v41_inc #(.W(16)) u_rn (.a(ba_hi[16*gc +: 16]), .inc(ba_inc[gc]), .y(bw_rn[16*gc +: 16]), .co());
    end endgenerate
    always @(posedge clk) bw_d <= bw_rn;
    // stage 1 copies of the head's row index / sub-index / byte gate: copy c = 2 ku + (kl - 4g) / 2
    wire [8*9-1:0] p1_hi;
    wire [8*3-1:0] p1_bb;
    wire [7:0]     p1_bg;
    generate for (gc = 0; gc < 8; gc = gc + 1) begin : g_ixb
        ot_v41_kreg #(.W(13)) u_ix (.clk(clk), .arst_n(rst_l[0]), .d({h_hi[9*(gc / 2) +: 9], hw7[2:0], hw7[3 + gc / 2]}),
                                   .q({p1_hi[9*gc +: 9], p1_bb[3*gc +: 3], p1_bg[gc]}));
    end endgenerate
    // stage 3 copies (one per lane)
    wire [16*3-1:0] p2_bb;
    wire [15:0]     p2_bg;
    generate for (gc = 0; gc < 16; gc = gc + 1) begin : g_ixc
        ot_v41_kreg #(.W(4)) u_ix (.clk(clk), .arst_n(rst_l[0]), .d({p1_bb[3*(gc / 2) +: 3], p1_bg[gc / 2]}),
                                  .q({p2_bb[3*gc +: 3], p2_bg[gc]}));
    end endgenerate
    // the buffer: one array per lane index (kl - 4g); word {blk >> 1, kw[2:0]}; read {row, kj}
    genvar gl, gu;
    generate for (gl = 0; gl < 4; gl = gl + 1) begin : g_part
        reg [15:0]  bbk [0:PE-1];
        reg [127:0] brk [0:3];               // bra of lanes (ku, gl)
        reg [15:0]  btk [0:3];               // bt_d of lanes (ku, gl)
        integer w, q, u, j;
        always @(posedge clk)
            for (w = 0; w < 8; w = w + 1)
                for (q = 0; q < NWB; q = q + 1)
                    if ((q % 2) == (par ? 1 : 0) && bwe[NWB*((8*gl + w) / 4) + q])
                        bbk[(q / 2) * 8 + w] <= bw_d[16*(8*gl + w) +: 16];
        always @(posedge clk)
            for (u = 0; u < 4; u = u + 1) begin
                for (j = 0; j < 8; j = j + 1)
`ifdef OT_PQC_MUT_IX
                    brk[u][16*j +: 16] <= bbk[{p1_hi[9*(2*u + gl/2) +: 9], 3'(7 - j)}];   // mutant: words reversed
`else
                    brk[u][16*j +: 16] <= bbk[{p1_hi[9*(2*u + gl/2) +: 9], 3'(j)}];
`endif
                btk[u] <= p2_bg[4*u + gl] ? brk[u][16*p2_bb[3*(4*u + gl) +: 3] +: 16] : 16'd0;
            end
        for (gu = 0; gu < 4; gu = gu + 1) begin : g_o
            assign bt_d[64*gu + 16*gl +: 16] = btk[gu];
        end
    end endgenerate
endmodule

// T_QB: the FP8 x buffer.  The {v, block, parity} request copy (aqi_d, the spine's AQL - 2 delay output) is copied
// 8 times (one per 32-bit slice), decoded into per-row write enables, and qb / eb are written from the two quantisers;
// the read takes the head's indices through 8 kept copies (g_ixq) into bt_q0 / bt_q1 / bt_e0 / bt_e1.
module ot_v41_pqc_qb #(
    parameter integer KMAX = 6144,
    parameter integer BAW = $clog2(KMAX / 32)
) (
    input  wire           clk,
    input  wire           rst_n,
    input  wire [BAW+1:0] aqi_d,
    input  wire [511:0]   aq_q,
    input  wire [19:0]    aq_e,
    input  wire [15:0]    h_b0,
    input  wire [15:0]    h_b1,
    input  wire [1:0]     hw_sv,             // {hw[13], hw[12]}
    output reg  [255:0]   hq0,               // bt_q0 / bt_e0 / bt_q1 / bt_e1 registered once more: the broadcast's
    output reg  [255:0]   hq1,               // bc_hr stage of these fields (the flat spine's bc_hr bits)
    output reg  [9:0]     he0,
    output reg  [9:0]     he1
);
    reg [255:0] bt_q0, bt_q1;
    reg [9:0]   bt_e0, bt_e1;
    always @(posedge clk) begin hq0 <= bt_q0; hq1 <= bt_q1; he0 <= bt_e0; he1 <= bt_e1; end
    localparam integer NBLK = KMAX / 32;
    localparam integer NQR = 2 * NBLK;
    wire [0:0] rst_l;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rst_l));
    wire [8*(BAW+2)-1:0] aqi;
    wire [8*2*NQR-1:0] qwe;
    genvar gq2;
    generate for (gq2 = 0; gq2 < 8; gq2 = gq2 + 1) begin : g_aqi
        ot_v41_kreg #(.W(BAW + 2), .AR(1)) u_c (.clk(clk), .arst_n(rst_l[0]), .d(aqi_d), .q(aqi[(BAW+2)*gq2 +: BAW+2]));
    end
    for (gq2 = 0; gq2 < 8; gq2 = gq2 + 1) begin : g_qwe
        wire [BAW+1:0] c = aqi[(BAW+2)*gq2 +: BAW+2];
        wire [15:0]    b = (c[0] ? 16'(NBLK) : 16'd0) + 16'(c[BAW:1]);
        reg  [2*NQR-1:0] dec;
        integer r;
        always @* for (r = 0; r < NQR; r = r + 1) begin
            dec[r] = c[BAW+1] && (b == 16'(r));
            dec[NQR + r] = c[BAW+1] && (b + 16'd1 == 16'(r));
        end
        ot_v41_kreg #(.W(2 * NQR), .AR(1)) u_we (.clk(clk), .arst_n(rst_l[0]), .d(dec), .q(qwe[2*NQR*gq2 +: 2*NQR]));
    end endgenerate
    reg [255:0] qb [0:NQR-1];
    reg [9:0]   eb [0:NQR-1];
    integer kw, kq2, kc;
    always @(posedge clk) begin
        for (kq2 = 0; kq2 < 8; kq2 = kq2 + 1)
            for (kw = 0; kw < NQR; kw = kw + 1) begin
                if (qwe[2*NQR*kq2 + kw]) qb[kw][32*kq2 +: 32] <= aq_q[32*kq2 +: 32];
                else if (qwe[2*NQR*kq2 + NQR + kw]) qb[kw][32*kq2 +: 32] <= aq_q[256 + 32*kq2 +: 32];
            end
        for (kw = 0; kw < NQR; kw = kw + 1) begin
            if (qwe[kw]) eb[kw] <= aq_e[9:0];
            else if (qwe[NQR + kw]) eb[kw] <= aq_e[19:10];
        end
    end
    wire [127:0] p1_i0, p1_i1;
    wire [7:0]   p1_g0, p1_g1;
    genvar gc;
    generate for (gc = 0; gc < 8; gc = gc + 1) begin : g_ixq
        ot_v41_kreg #(.W(34)) u_ix (.clk(clk), .arst_n(rst_l[0]), .d({h_b0, h_b1, hw_sv[1], hw_sv[0]}),
                                   .q({p1_i0[16*gc +: 16], p1_i1[16*gc +: 16], p1_g1[gc], p1_g0[gc]}));
    end endgenerate
    always @(posedge clk) begin
        for (kc = 0; kc < 8; kc = kc + 1) begin
            bt_q0[32*kc +: 32] <= p1_g0[kc] ? qb[p1_i0[16*kc +: 16]][32*kc +: 32] : 32'd0;
`ifdef OT_PQC_MUT_QB
            bt_q1[32*kc +: 32] <= p1_g1[kc] ? qb[p1_i0[16*kc +: 16]][32*kc +: 32] : 32'd0;     // mutant: q1 reads index 0
`else
            bt_q1[32*kc +: 32] <= p1_g1[kc] ? qb[p1_i1[16*kc +: 16]][32*kc +: 32] : 32'd0;
`endif
        end
        bt_e0 <= p1_g0[0] ? eb[p1_i0[15:0]] : 10'd0;
        bt_e1 <= p1_g1[0] ? eb[p1_i1[15:0]] : 10'd0;
    end
endmodule

// T_RET: one return group of NR (<= 8) regions, the flat spine's g_reg logic for those regions with the group's
// configuration replica (rep, from the spine's g_mdr2), the RPT repeaters on both sides, the group fault (q2f) and
// the stage-A row popcount per tag (ga[4 t +: 4]).  PIN = 1 (physical screen): the screen's own pin registers on
// r_* (in) and w_* (out) live here too, so the screen's top level keeps no per-region flops.
module ot_v41_pqc_ret #(
    parameter integer NR = 8,
    parameter integer VAW = 19,
    parameter integer PQ = 1,
    parameter integer RPT = 2,
    parameter integer PIN = 0,
    parameter integer CFW = 5 * VAW + 18,
    parameter integer GRW = 4 * CFW + 4 + 2
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [NR-1:0]     r_v,
    input  wire [16*NR-1:0]  r_row,
    input  wire [3*NR-1:0]   r_pos,
    input  wire [32*NR-1:0]  r_fp32,
    input  wire [16*NR-1:0]  r_bf16,
    input  wire [NR-1:0]     r_e,
    input  wire [GRW-1:0]    mdr,
    output wire [NR-1:0]     w_we,
    output wire [NR*VAW-1:0] w_addr,
    output wire [NR*32-1:0]  w_data,
    output reg               q2f,
    output reg  [15:0]       ga
);
    wire [0:0] rst_l;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rst_l));
    // screen pin registers (PIN = 1)
    wire [NR-1:0]    i_v, i_e;
    wire [16*NR-1:0] i_row, i_bf;
    wire [3*NR-1:0]  i_pos;
    wire [32*NR-1:0] i_f32;
    wire [NR-1:0]     o_we;
    wire [NR*VAW-1:0] o_addr;
    wire [NR*32-1:0]  o_data;
    generate if (PIN != 0) begin : g_pin
        reg [NR-1:0] a_v, a_e; reg [16*NR-1:0] a_row, a_bf; reg [3*NR-1:0] a_pos; reg [32*NR-1:0] a_f32;
        reg [NR-1:0] b_we; reg [NR*VAW-1:0] b_addr; reg [NR*32-1:0] b_data;
        always @(posedge clk) begin
            a_v <= r_v; a_e <= r_e; a_row <= r_row; a_bf <= r_bf16; a_pos <= r_pos; a_f32 <= r_fp32;
            b_we <= o_we; b_addr <= o_addr; b_data <= o_data;
        end
        assign {i_v, i_e, i_row, i_bf, i_pos, i_f32} = {a_v, a_e, a_row, a_bf, a_pos, a_f32};
        assign {w_we, w_addr, w_data} = {b_we, b_addr, b_data};
    end else begin : g_nopin
        assign {i_v, i_e, i_row, i_bf, i_pos, i_f32} = {r_v, r_e, r_row, r_bf16, r_pos, r_fp32};
        assign {w_we, w_addr, w_data} = {o_we, o_addr, o_data};
    end endgenerate
    // stage 0: repeaters and the registered root inputs
    reg [NR-1:0]    q0_v, q0_e;
    reg [14*NR-1:0] q0_row;
    reg [16*NR-1:0] q0_bf;
    reg [3*NR-1:0]  q0_pos;
    reg [32*NR-1:0] q0_f32;
    wire [NR-1:0]    p_v, p_e;
    wire [16*NR-1:0] p_row, p_bf;
    wire [3*NR-1:0]  p_pos;
    wire [32*NR-1:0] p_f32;
    ot_hdc_delay #(.W(NR), .D(RPT), .RESET(1)) u_prv (.clk(clk), .rst_n(rst_l[0]), .d(i_v), .q(p_v));
    ot_hdc_delay #(.W(NR + 16*NR + 16*NR + 3*NR + 32*NR), .D(RPT)) u_prd (.clk(clk), .rst_n(rst_l[0]),
        .d({i_e, i_row, i_bf, i_pos, i_f32}), .q({p_e, p_row, p_bf, p_pos, p_f32}));
    always @(posedge clk or negedge rst_l[0])
        if (!rst_l[0]) q0_v <= {NR{1'b0}};
        else q0_v <= p_v;
    integer kr0;
    always @(posedge clk) begin
        q0_e <= p_e; q0_bf <= p_bf; q0_pos <= p_pos; q0_f32 <= p_f32;
        for (kr0 = 0; kr0 < NR; kr0 = kr0 + 1) q0_row[14*kr0 +: 14] <= p_row[16*kr0 +: 14];
    end
    // the group's configuration replica (kept)
    wire [GRW-1:0] rep;
    ot_v41_kreg #(.W(GRW)) u_rep (.clk(clk), .arst_n(rst_l[0]), .d(mdr), .q(rep));
    reg [NR-1:0]     w_we_r;
    reg [NR*VAW-1:0] w_addr_r;
    reg [NR*32-1:0]  w_data_r;
    reg [NR-1:0]     q1_v, q1_f;
    reg [NR*VAW-1:0] q1_a, q1_p;
    reg [NR*32-1:0]  q1_f32;
    reg [NR*16-1:0]  q1_bf;
    wire [4*NR-1:0]  oh_cnt;
    genvar gk;
    generate for (gk = 0; gk < NR; gk = gk + 1) begin : g_reg
        wire [1:0] rtag = (PQ != 0) ? p_row[16*gk + 14 +: 2] : rep[4*CFW + 4 +: 2];
        wire [3:0] ohd = 4'b0001 << rtag;
        wire [19:0] oh;
        ot_v41_kreg #(.W(4)) u_oh0 (.clk(clk), .arst_n(rst_l[0]), .d(ohd), .q(oh[3:0]));
        ot_v41_kreg #(.W(4)) u_oh1 (.clk(clk), .arst_n(rst_l[0]), .d(ohd), .q(oh[7:4]));
        ot_v41_kreg #(.W(4)) u_oh2 (.clk(clk), .arst_n(rst_l[0]), .d(ohd), .q(oh[11:8]));
        ot_v41_kreg #(.W(4), .AR(1)) u_oh3 (.clk(clk), .arst_n(rst_l[0]), .d(ohd & {4{p_v[gk]}}), .q(oh[15:12]));
        ot_v41_kreg #(.W(4), .AR(1)) u_oh4 (.clk(clk), .arst_n(rst_l[0]), .d(ohd & {4{p_v[gk]}}), .q(oh[19:16]));
        assign oh_cnt[4*gk +: 4] = oh[19:16];
        reg  [17:0]   rsfm_d;
        wire [13:0]   rs_m;
        wire [3:0]    fm_m;
        integer t0, t2;
        always @* begin
            rsfm_d = '0;
            for (t0 = 0; t0 < 4; t0 = t0 + 1) rsfm_d = rsfm_d | (rep[CFW*t0 +: 18] & {18{ohd[t0]}});
        end
        ot_v41_kreg #(.W(18)) u_rsfm (.clk(clk), .arst_n(rst_l[0]), .d(rsfm_d), .q({rs_m, fm_m}));
        reg [VAW-1:0] ob_m, o1_m, o3_m, o5_m, o7_m;
        reg           live_m;
        integer t;
        always @* begin
            ob_m = '0; o1_m = '0; o3_m = '0; o5_m = '0; o7_m = '0; live_m = 1'b0;
            for (t = 0; t < 4; t = t + 1) begin
                ob_m = ob_m | (rep[CFW*t + 4*VAW + 18 +: VAW] & {VAW{oh[t]}});
                o7_m = o7_m | (rep[CFW*t + 3*VAW + 18 +: VAW] & {VAW{oh[8 + t]}});
                o5_m = o5_m | (rep[CFW*t + 2*VAW + 18 +: VAW] & {VAW{oh[8 + t]}});
                o3_m = o3_m | (rep[CFW*t + VAW + 18 +: VAW] & {VAW{oh[4 + t]}});
                o1_m = o1_m | (rep[CFW*t + 18 +: VAW] & {VAW{oh[4 + t]}});
                live_m = live_m | (rep[4*CFW + t] & oh[12 + t]);
            end
        end
        wire [VAW-1:0] a_s;
        wire           row_ge;
        ot_v41_ksadd #(.W(VAW)) u_a (.a(ob_m), .b(VAW'(q0_row[14*gk +: 14])), .cin(1'b0), .s(a_s), .cout());
        ot_v41_ksadd #(.W(14)) u_rs (.a(q0_row[14*gk +: 14]), .b(~rs_m), .cin(1'b1), .s(), .cout(row_ge));
        always @(posedge clk) begin
            q1_a[VAW*gk +: VAW] <= a_s;
            case (q0_pos[3*gk +: 3])
                3'd0: q1_p[VAW*gk +: VAW] <= '0;
                3'd1: q1_p[VAW*gk +: VAW] <= o1_m;
                3'd2: q1_p[VAW*gk +: VAW] <= {o1_m[VAW-2:0], 1'b0};
                3'd3: q1_p[VAW*gk +: VAW] <= o3_m;
                3'd4: q1_p[VAW*gk +: VAW] <= {o1_m[VAW-3:0], 2'b0};
                3'd5: q1_p[VAW*gk +: VAW] <= o5_m;
                3'd6: q1_p[VAW*gk +: VAW] <= {o3_m[VAW-2:0], 1'b0};
                default: q1_p[VAW*gk +: VAW] <= o7_m;
            endcase
            q1_f32[32*gk +: 32] <= q0_f32[32*gk +: 32];
            q1_bf[16*gk +: 16] <= q0_bf[16*gk +: 16];
        end
        always @(posedge clk or negedge rst_l[0])
            if (!rst_l[0]) begin q1_v[gk] <= 1'b0; q1_f[gk] <= 1'b0; end
            else begin
                q1_v[gk] <= q0_v[gk];
                q1_f[gk] <= q0_v[gk] && (q0_e[gk] || !live_m);
            end
        wire       s_hi = fm_m[0] || (fm_m[1] && fm_m[3]);
        wire       s_lo = fm_m[0] || (fm_m[1] && fm_m[2]);
        reg [2:0]  q1_gs;
        always @(posedge clk) q1_gs <= {row_ge, s_hi, s_lo};
        wire [VAW-1:0] w_s;
        ot_v41_ksadd #(.W(VAW)) u_w (.a(q1_a[VAW*gk +: VAW]), .b(q1_p[VAW*gk +: VAW]), .cin(1'b0), .s(w_s), .cout());
        reg [VAW-1:0] q1b_w;
        reg [31:0]    q1b_f32;
        reg [15:0]    q1b_bf;
        always @(posedge clk) begin
            q1b_w <= w_s; q1b_f32 <= q1_f32[32*gk +: 32]; q1b_bf <= q1_bf[16*gk +: 16];
        end
        wire [3:0] q2_sel;
        genvar gsl;
        for (gsl = 0; gsl < 4; gsl = gsl + 1) begin : g_sel
            wire [2:0] q1_g;
            ot_v41_kreg #(.W(3)) u_g (.clk(clk), .arst_n(rst_l[0]), .d(q1_gs), .q(q1_g));
            ot_v41_kreg #(.W(1)) u_s (.clk(clk), .arst_n(rst_l[0]), .d(q1_g[2] ? q1_g[1] : q1_g[0]), .q(q2_sel[gsl]));
        end
        reg [VAW-1:0] q2_a;
        reg [31:0]    q2_f32;
        reg [15:0]    q2_bf;
        always @(posedge clk) begin
            q2_a <= q1b_w; q2_f32 <= q1b_f32; q2_bf <= q1b_bf;
        end
        always @(posedge clk) begin
            w_addr_r[VAW*gk +: VAW] <= q2_a;
            for (t2 = 0; t2 < 4; t2 = t2 + 1)
`ifdef OT_PQC_MUT_RET
                w_data_r[32*gk + 8*t2 +: 8] <= q2_sel[t2] ? q2_f32[8*(3-t2) +: 8] : ((t2 < 2) ? 8'd0 : q2_bf[8*(t2-2) +: 8]);
`else
                w_data_r[32*gk + 8*t2 +: 8] <= q2_sel[t2] ? q2_f32[8*t2 +: 8] : ((t2 < 2) ? 8'd0 : q2_bf[8*(t2-2) +: 8]);
`endif
        end
    end endgenerate
    ot_hdc_delay #(.W(NR), .D(RPT), .RESET(1)) u_pwv (.clk(clk), .rst_n(rst_l[0]), .d(w_we_r), .q(o_we));
    ot_hdc_delay #(.W(NR*VAW + NR*32), .D(RPT)) u_pwd (.clk(clk), .rst_n(rst_l[0]), .d({w_addr_r, w_data_r}),
                                                       .q({o_addr, o_data}));
    reg [NR-1:0] q2_v, q1b_v;
    integer kt, kr;
    reg [7:0] gm;
    always @(posedge clk or negedge rst_l[0])
        if (!rst_l[0]) begin w_we_r <= {NR{1'b0}}; q2_v <= {NR{1'b0}}; q1b_v <= {NR{1'b0}}; q2f <= 1'b0; ga <= 16'd0; end
        else begin
            q1b_v <= q1_v; q2_v <= q1b_v; w_we_r <= q2_v;
            q2f <= |q1_f;
            for (kt = 0; kt < 4; kt = kt + 1) begin
                gm = 8'd0;
                for (kr = 0; kr < NR; kr = kr + 1) gm[kr] = oh_cnt[4 * kr + kt];
                ga[4*kt +: 4] <= 4'($countones(gm));
            end
        end
endmodule

// T_BC: one broadcast relay stage (a register column placed on the broadcast's wire); the valid / configuration bits
// (the top RT bits and bit RB) are reset, the data is not.
module ot_v41_pqc_bcrel #(
    parameter integer W = 1617,
    parameter integer RT = 15,
    parameter integer RB = 1063
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    wire [0:0] rst_l;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rst_l));
    reg [W-1:0] qd;                          // data (bits under reset unused)
    reg [RT:0]  qc;                          // {top RT bits, bit RB}
`ifdef OT_PQC_MUT_BC
    always @(posedge clk) qd <= {d[W-1:1024], 1024'd0};             // mutant: the BF16 lanes dropped
`else
    always @(posedge clk) qd <= d;
`endif
    always @(posedge clk or negedge rst_l[0])
        if (!rst_l[0]) qc <= '0;
        else qc <= {d[W-1 -: RT], d[RB]};
    integer k;
    always @* begin
        q = qd;
        q[W-1 -: RT] = qc[RT:1];
        q[RB] = qc[0];
    end
endmodule
