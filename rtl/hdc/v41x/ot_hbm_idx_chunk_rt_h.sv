`timescale 1ns/1ps
`default_nettype none
// IDX-SCORE leaf core, HALF-COLUMN SPLIT (HBM-P4-SPLIT 2026-10-23): ot_hbm_idx_chunk_rt re-cut into hard cores of
// <= 350k Yosys cells for the HBM d4g top-down plan (over_cap: ot_hbm_idx_score_quarter_static, 12.56M cells measured,
// leaf 1.55M, one key column ~374k > the 350k core budget).  Same ports and the SAME cycle-exact outputs as
// ot_hbm_idx_chunk_rt (rtl/test/hbm_idx_static/tb_idx_chunk_rt_h_equiv.sv: lock-step against chunk_rt, every output
// every edge); the region bodies are ot_hbm_idx_chunk_rt's g_rgn body verbatim.
//   ot_hbm_idx_chunk_rt_h = ot_hbm_idx_chunk_rt glue (reset relays, input registers, head ids, valid line, online)
//     + 8 x ot_hidx_score_hcol #(HALF): column g, heads 4*HALF .. 4*HALF+3 = clock regions 2*HALF, 2*HALF+1.
//   Glue -> half column: query broadcast {qv_b, q_b} (569 b, glue reg -> region pin reg), the column's key slice (544 b,
//     rkey reg -> key_p reg), its 4 head ids (32 b, hid reg -> hid_p reg), the column reset (rr[g], reset relay input).
//   HALF 0 -> HALF 1: running sum cs[4] (32 b) + cf[4] (1 b): cs_o reg (head 3) -> csi_p reg (head 4).
//   HALF 1 -> glue: cs[8] + cf[8] (cs_o reg -> c_sum / the leaf's sum-bus register); both halves -> glue: 2 region
//     online bits each (onl reg -> rdy1 reg).  Every crossing is register to register: no cycle cost.
// MUT (bench only): 1 = the HALF 0 -> HALF 1 seam of column 0 one edge late (must FAIL the lock-step bench).  With
// MUT 0 every column binds the same two masters (HALF 0: 195,127 / HALF 1: 186,410 Yosys cells, r18h5 flags).
module ot_hidx_score_hcol #(
    parameter integer HALF = 0,
    parameter integer MUT  = 0           // bench mutant (the parent passes it to column 0 only)
) (
    input  wire [1:0]      clk_pair,     // regions 2*HALF, 2*HALF+1 of this column
    input  wire            rst_col,      // rr[g] of the glue (column reset relay output)
    input  wire            qv_b,
    input  wire [QW-1:0]   q_b,
    input  wire [KW-1:0]   key,
    input  wire [4*8-1:0]  hid4,         // head ids 4*HALF .. 4*HALF+3
    input  wire [31:0]     cs_in,        // cs[4*HALF] (HALF 0: tie 0)
    input  wire            cf_in,
    output wire [31:0]     cs_out,       // cs[4*HALF+4]
    output wire            cf_out,
    output wire [1:0]      prdy
);
    localparam integer NB = 4, FPL = 7, FML = 5, QL = 5;
    localparam integer KW = NB * 136;
    localparam integer QW = 8 + NB * 128 + NB * 8 + 16;
    wire [31:0] cs [0:4]; wire cf [0:4];
    assign cs[0] = cs_in; assign cf[0] = cf_in;
    genvar r, hh, bb;
    generate for (r = 0; r < 2; r = r + 1) begin : g_rgn
        localparam integer RR = 2 * HALF + r;            // region within the column (0..3)
        wire ck = clk_pair[r];
        wire [0:0] srr; wire rs = srr[0];
        ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(ck), .rst_n_in(rst_col), .rst_n(srr));
        reg rn_p, onl;
        always @(posedge ck) rn_p <= rs;
        always @(posedge ck or negedge rs) if (!rs) onl <= 1'b0; else onl <= rs && rn_p;
        assign prdy[r] = onl;
        reg qv_p; reg [QW-1:0] q_p; reg [KW-1:0] key_p;
        always @(posedge ck) begin qv_p <= qv_b && rn_p; q_p <= q_b; key_p <= key; end
        wire [7:0] qh_p = q_p[QW-1 -: 8];
        for (hh = 0; hh < 2; hh = hh + 1) begin : g_h
            localparam integer H = 2 * RR + hh;          // head within the chunk column (0..7)
            localparam integer HL = 2 * r + hh;          // head within this half (0..3)
            reg [7:0] hid_p; always @(posedge ck) hid_p <= hid4[8*HL +: 8];
            reg q_we; reg [QW-9:0] q2; reg [NB*128-1:0] qc; reg [NB*8-1:0] qs; reg [15:0] qw;
            always @(posedge ck) begin
                q_we <= qv_p && rn_p && (qh_p == hid_p);
                q2 <= q_p[QW-9:0];
                if (q_we) {qc, qs, qw} <= q2;
            end
            wire [NB*32-1:0] acc; wire [NB-1:0] afault;
            for (bb = 0; bb < NB; bb = bb + 1) begin : g_blk
                localparam integer DS = (bb == 0) ? 0 : FPL * (bb - 1);
                wire [31:0] bv0; wire bo0; wire [31:0] bv; wire bo;
                ot_hdc_v41x_q4dot_l #(.QL(QL)) u_d (.clk(ck), .a(qc[bb*128 +: 128]), .b(key_p[128*bb +: 128]),
                    .ua(qs[bb*8 +: 8]), .ub(key_p[NB*128 + 8*bb +: 8]), .y(bv0), .ovf(bo0));
                ot_hdc_delay #(.W(33), .D(DS)) u_bd (.clk(ck), .rst_n(1'b1), .d({bo0, bv0}), .q({bo, bv}));
                if (bb == 0) begin : g_first
                    assign acc[31:0] = bv; assign afault[0] = bo;
                end else begin : g_add
                    wire [1:0] err; wire vo_unused; wire pf, bo_d;
                    ot_hdc_delay #(.W(1), .D(FPL)) u_pf (.clk(ck), .rst_n(1'b1), .d(afault[bb-1]), .q(pf));
                    ot_hdc_v41x_faddl #(.LAT(FPL)) u_a (.clk(ck), .rst_n(rs), .valid_in(1'b1),
                        .a(acc[32*(bb-1) +: 32]), .b(bv), .y(acc[32*bb +: 32]), .err(err), .valid_out(vo_unused));
                    ot_hdc_delay #(.W(1), .D(FPL)) u_bf (.clk(ck), .rst_n(1'b1), .d(bo), .q(bo_d));
                    assign afault[bb] = pf || bo_d || (err != 2'd0);
                end
            end
            wire [15:0] sc16; wire sco;
            ot_hdc_v41x_bf16 u_sb (.x(acc[32*(NB-1) +: 32]), .y(sc16), .ovf(sco));
            reg [15:0] rsc; reg rscf;
            always @(posedge ck) begin rsc <= sc16; rscf <= afault[NB-1] || sco; end
            wire [15:0] tm0; wire tmo, rscf_d;
            ot_hdc_v41x_bmul_l #(.ML(FML)) u_m (.clk(ck), .a(rsc), .w(qw), .y(tm0), .ovf(tmo));
            ot_hdc_delay #(.W(1), .D(FML)) u_tf (.clk(ck), .rst_n(1'b1), .d(rscf), .q(rscf_d));
            wire [15:0] tm; wire tf;
            ot_hdc_delay #(.W(17), .D((FPL + 2) * H)) u_td (.clk(ck), .rst_n(1'b1), .d({rscf_d || tmo, tm0}), .q({tf, tm}));
            reg [31:0] csi_p; reg cfi_p; reg [31:0] cs_o; reg cf_o;
            if (MUT == 1 && H == 4) begin : g_mseam   // bench mutant (column 0 only): the half seam one edge late
                reg [31:0] cs_x; reg cf_x;
                always @(posedge ck) begin cs_x <= cs[HL]; cf_x <= cf[HL]; csi_p <= cs_x; cfi_p <= cf_x; end
            end else begin : g_nseam
                always @(posedge ck) begin csi_p <= cs[HL]; cfi_p <= cf[HL]; end
            end
            if (H == 0) begin : g_seed
                wire [32:0] seed_d;
                ot_hdc_delay #(.W(33), .D(FPL)) u_sd (.clk(ck), .rst_n(1'b1),
                    .d({tf, (tm[14:0] == 15'd0) ? 32'd0 : {tm, 16'd0}}), .q(seed_d));
                always @(posedge ck) begin cs_o <= seed_d[31:0]; cf_o <= seed_d[32]; end
            end else begin : g_sum
                wire [1:0] err; wire vo_unused; wire [31:0] sum; wire pf;
                ot_hdc_v41x_faddl #(.LAT(FPL)) u_a (.clk(ck), .rst_n(rs), .valid_in(1'b1),
                    .a(csi_p), .b({tm, 16'd0}), .y(sum), .err(err), .valid_out(vo_unused));
                ot_hdc_delay #(.W(1), .D(FPL)) u_pf (.clk(ck), .rst_n(1'b1), .d(cfi_p || tf), .q(pf));
                always @(posedge ck) begin cs_o <= sum; cf_o <= pf || (err != 2'd0); end
            end
            assign cs[HL + 1] = cs_o; assign cf[HL + 1] = cf_o;
        end
    end endgenerate
    assign cs_out = cs[4]; assign cf_out = cf[4];
endmodule

module ot_hbm_idx_chunk_rt_h #(
    parameter integer QLATE = 0,
    parameter integer MUT   = 0          // bench mutant (ot_hidx_score_hcol MUT)
) (
    input  wire                  clk, input wire [15:0] clk_pair,
    input  wire                  rst_n,
    input  wire [7:0]            hb,
    input  wire                  ql_v,
    input  wire [7:0]            ql_head,
    input  wire [NB*128-1:0]     ql_codes,
    input  wire [NB*8-1:0]       ql_sc,
    input  wire [15:0]           ql_w,
    input  wire                  k_v,
    input  wire [NKT-1:0]        k_kv,
    input  wire [NKT*NB*136-1:0] k_key,
    output reg                   c_v,
    output reg  [NKT-1:0]        c_kv,
    output reg  [NKT*32-1:0]     c_sum,
    output reg  [NKT-1:0]        c_fault,
    output reg                   online,
    output wire                  n_v,
    output wire [NKT-1:0]        n_kv,
    output wire [NKT*32-1:0]     n_sum,
    output wire [NKT-1:0]        n_fault
);
    localparam integer NB = 4, NKT = 4, FPL = 7, FML = 5, QL = 5, HC = 8;
    localparam integer KW = NB * 136;
    localparam integer QW = 8 + NB * 128 + NB * 8 + 16;
    localparam integer LAT_SC = QL + FPL * (NB - 1);
    localparam integer LAT_T  = LAT_SC + 1 + FML;
    localparam integer XLAT   = FPL + 16;
    localparam integer LATE   = LAT_T + FPL * (HC - 1) + XLAT;
    // ---- glue (clk): verbatim ot_hbm_idx_chunk_rt
    wire [15:0] prdy; reg [15:0] rdy1, rdy2;
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin rdy1 <= 0; rdy2 <= 0; online <= 0; end
      else begin rdy1 <= prdy; rdy2 <= rdy1; online <= (&rdy2); end
    wire [NKT:0] rr;
    ot_rst_relay #(.REGIONS(NKT + 1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    wire rn = rr[NKT];
    reg rql_v; reg [QW-1:0] rq; reg rv; reg [NKT-1:0] rkv; reg [NKT*KW-1:0] rkey; reg [7:0] hb_p; reg [7:0] hid [0:HC-1];
    integer i;
    always @(posedge clk) begin
        rql_v <= ql_v && rn; rq <= {ql_head, ql_codes, ql_sc, ql_w};
        rv <= k_v && rn; rkv <= k_kv; rkey <= k_key; hb_p <= hb;
`ifdef OT_IDX_RT_MUT_SWAP
        for (i = 0; i < HC; i = i + 1) hid[i] <= (hb_p ^ 8'd8) + 8'(i);
`else
        for (i = 0; i < HC; i = i + 1) hid[i] <= hb_p + 8'(i);
`endif
    end
    wire [NKT:0] vl;
    ot_hdc_delay #(.W(NKT + 1), .D(LATE), .RESET(1)) u_vl (.clk(clk), .rst_n(rn), .d({rkv, rv}), .q(vl));
    wire qv_b; wire [QW-1:0] q_b;
    ot_hdc_delay #(.W(1 + QW), .D(QLATE)) u_qlate (.clk(clk), .rst_n(1'b1), .d({rql_v, rq}), .q({qv_b, q_b}));
    wire [8*HC-1:0] hidv;
    genvar g, hf;
    generate
        for (g = 0; g < HC; g = g + 1) begin : g_hid
            assign hidv[8*g +: 8] = hid[g];
        end
        for (g = 0; g < NKT; g = g + 1) begin : g_col
            wire [31:0] cs [0:2]; wire cf [0:2];
            assign cs[0] = 32'd0; assign cf[0] = 1'b0;
            for (hf = 0; hf < 2; hf = hf + 1) begin : g_half
                ot_hidx_score_hcol #(.HALF(hf), .MUT((g == 0) ? MUT : 0)) u_hc (.clk_pair(clk_pair[4*g + 2*hf +: 2]), .rst_col(rr[g]),
                    .qv_b(qv_b), .q_b(q_b), .key(rkey[g*KW +: KW]), .hid4(hidv[32*hf +: 32]),
                    .cs_in(cs[hf]), .cf_in(cf[hf]), .cs_out(cs[hf+1]), .cf_out(cf[hf+1]), .prdy(prdy[4*g + 2*hf +: 2]));
            end
            assign n_sum[32*g +: 32] = cs[2]; assign n_fault[g] = cf[2];
            always @(posedge clk) begin c_sum[32*g +: 32] <= cs[2]; c_fault[g] <= cf[2]; end
        end
    endgenerate
    assign n_v = vl[0] && rn; assign n_kv = vl[NKT:1];
    always @(posedge clk) begin c_v <= n_v; c_kv <= n_kv; end
endmodule
`default_nettype wire
