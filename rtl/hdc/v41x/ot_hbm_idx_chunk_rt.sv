`timescale 1ns/1ps
`default_nettype none
// IDX-SCORE leaf core (H-NETLIST/IDX-SCORE 2026-10-17): the RETIMED chunk. Same ports' meaning, same cycle-exact outputs as
// ot_hbm_idx_chunk_owned_native (32 systolic hslices), under the IDX protocol (a key never arrives within 3 edges of a query
// load beat: ot_hbm_idx_engine_static settle fault). The 590k-flop leaf was 64 % alignment delay lines (query and key
// passed through 8 slices at FPL+2 a hop, key blocks skewed); here the SAME values meet in the SAME fp32 add order with the
// delays moved to the narrow point:
//   (a) query load: registered broadcast to every head (head compare), no pass-through chain;
//   (b) every head computes its term when the key arrives; the 17-bit term (+fault) waits 9h edges, not the 544-bit key;
//   (c) block dots computed at once; the 32-bit block partial (+fault) waits FPL*(bb-1), not the 136-bit key block;
//   (d) no per-slice pin flops: one pin stage per clock region.
// CLOCK REGIONS (H-DIE 10-17: 16 roots per leaf, one per head pair): region r = column g = r/4, heads 2(r%4), 2(r%4)+1,
// clocked by clk_pair[r]; the chunk glue (input/output registers, valid line, online) on clk. Every inter-region hop is
// register-to-register (KIND1 rule: no shared mid-pipeline hop):
//   clk  rkey/rql (input reg)      -> region key_p / q pin regs                     (reg -> reg)
//   region r cs_out (head 2k+1)    -> region r+1 csi_p (head 2k+2)                  (reg -> reg)
//   region 4g+3 cs_out (head 7)    -> clk c_sum/c_fault regs                        (reg -> reg)
//   region online                  -> clk rdy1                                      (reg -> reg)
// The term delay lines of head h live in head h's region (its key_p is its own region's pin reg).
module ot_hbm_idx_chunk_rt #(
    parameter integer QLATE = 0          // bench mutant: the query broadcast reaches the heads QLATE edges late
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
    output reg                   online
);
    localparam integer NB = 4, NKT = 4, FPL = 7, FML = 5, QL = 5, HC = 8;
    localparam integer KW = NB * 136;
    localparam integer QW = 8 + NB * 128 + NB * 8 + 16;
    localparam integer LAT_SC = QL + FPL * (NB - 1);
    localparam integer LAT_T  = LAT_SC + 1 + FML;
    localparam integer XLAT   = FPL + 16;
    localparam integer LATE   = LAT_T + FPL * (HC - 1) + XLAT;
    // ---- glue (clk): reset relays, input registers, valid line, online (as ot_hbm_idx_chunk_owned_native)
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
        for (i = 0; i < HC; i = i + 1) hid[i] <= (hb_p ^ 8'd8) + 8'(i);   // mutant: this leaf computes its neighbour's heads
`else
        for (i = 0; i < HC; i = i + 1) hid[i] <= hb_p + 8'(i);
`endif
    end
    wire [NKT:0] vl;
    ot_hdc_delay #(.W(NKT + 1), .D(LATE), .RESET(1)) u_vl (.clk(clk), .rst_n(rn), .d({rkv, rv}), .q(vl));
    // mutant: the query broadcast late (proves the settle rule the retiming relies on)
    wire qv_b; wire [QW-1:0] q_b;
    ot_hdc_delay #(.W(1 + QW), .D(QLATE)) u_qlate (.clk(clk), .rst_n(1'b1), .d({rql_v, rq}), .q({qv_b, q_b}));
    genvar g, r, hh, bb;
    generate for (g = 0; g < NKT; g = g + 1) begin : g_col
        wire [31:0] cs [0:HC]; wire cf [0:HC];
        for (r = 0; r < 4; r = r + 1) begin : g_rgn
            localparam integer RG = 4 * g + r;
            wire ck = clk_pair[RG];
            // region reset relay + online (as the old per-slice relay, one per region)
            wire [0:0] srr; wire rs = srr[0];
            ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(ck), .rst_n_in(rr[g]), .rst_n(srr));
            reg rn_p, onl;
            always @(posedge ck) rn_p <= rs;
            always @(posedge ck or negedge rs) if (!rs) onl <= 1'b0; else onl <= rs && rn_p;
            assign prdy[RG] = onl;
            // region pin registers (reg -> reg from the glue)
            reg qv_p; reg [QW-1:0] q_p; reg [KW-1:0] key_p;
            always @(posedge ck) begin qv_p <= qv_b && rn_p; q_p <= q_b; key_p <= rkey[g*KW +: KW]; end
            wire [7:0] qh_p = q_p[QW-1 -: 8];
            for (hh = 0; hh < 2; hh = hh + 1) begin : g_h
                localparam integer H = 2 * r + hh;
                reg [7:0] hid_p; always @(posedge ck) hid_p <= hid[H];
                // ---- (a) query store: own head written one edge after the compare
                reg q_we; reg [QW-9:0] q2; reg [NB*128-1:0] qc; reg [NB*8-1:0] qs; reg [15:0] qw;
                always @(posedge ck) begin
                    q_we <= qv_p && rn_p && (qh_p == hid_p);
                    q2 <= q_p[QW-9:0];
                    if (q_we) {qc, qs, qw} <= q2;
                end
                // ---- (c) block dots now, partials delayed FPL*(bb-1)
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
                // ---- (b) the head term waits 9h edges (the old key/sum hop FPL+2 per head)
                wire [15:0] tm; wire tf;
                ot_hdc_delay #(.W(17), .D((FPL + 2) * H)) u_td (.clk(ck), .rst_n(1'b1), .d({rscf_d || tmo, tm0}), .q({tf, tm}));
                // ---- running sum (cs pin register = the old slice pin flop; reg -> reg across regions)
                reg [31:0] csi_p; reg cfi_p; reg [31:0] cs_o; reg cf_o;
`ifdef OT_IDX_RT_MUT_SEAM
                // mutant: the region seam of column 0 between regions 0 and 1 (head 1 -> head 2) one edge late
                if (g == 0 && H == 2) begin : g_mseam
                    reg [31:0] cs_x; reg cf_x;
                    always @(posedge ck) begin cs_x <= cs[H]; cf_x <= cf[H]; csi_p <= cs_x; cfi_p <= cf_x; end
                end else begin : g_nseam
                    always @(posedge ck) begin csi_p <= cs[H]; cfi_p <= cf[H]; end
                end
`else
                always @(posedge ck) begin csi_p <= cs[H]; cfi_p <= cf[H]; end
`endif
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
                assign cs[H + 1] = cs_o; assign cf[H + 1] = cf_o;
            end
        end
        assign cs[0] = 32'd0; assign cf[0] = 1'b0;
        always @(posedge clk) begin c_sum[32*g +: 32] <= cs[HC]; c_fault[g] <= cf[HC]; end
    end endgenerate
    always @(posedge clk) begin c_v <= vl[0] && rn; c_kv <= vl[NKT:1]; end
endmodule
`default_nettype wire
