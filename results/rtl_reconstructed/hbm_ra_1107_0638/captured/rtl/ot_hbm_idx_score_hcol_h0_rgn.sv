`timescale 1ns/1ps
`default_nettype none
// DIE-HBM-61/SPLIT 11-03 (OWNER TWO-STRIKES RE-FORM, HBM batch HBM-RF1 / plan event d44v): ot_hbm_idx_score_hcol_h0
// (= ot_hidx_score_hcol #(HALF 0), 180k cells measured, > 150k) cut at its clock-region seam into two hardened
// sub-blocks of ONE region each (heads 0-1 = region 0 on clk_pair[0], heads 2-3 = region 1 on clk_pair[1]).
// The region body is ot_hidx_score_hcol's g_rgn body (rtl/hdc/v41x/ot_hbm_idx_chunk_rt_h.sv) verbatim, HALF = 0.
//
//   ot_hbm_idx_score_hcol_h0_ra = region 0 (heads 0, 1): out cs/cf after head 1 (= cs[2]/cf[2] of the hcol)
//   ot_hbm_idx_score_hcol_h0_rb = region 1 (heads 2, 3): in  cs/cf (cs[2]), out cs/cf after head 3 (= cs_out)
//
// Every sub-block pin is registered at the face by the kit face shell (+1 in / +1 out).  The only crossing between
// the two sub-blocks is the 33-bit running sum (cs[2], cf[2]); it gains the two face flops (ra out + rb in) = +2 edges.
// Region 0 pays them back inside: its seed line (head 0, pure delay D = FPL) and its head-1 term delay (pure delay
// D = (FPL+2)*1) are both SEAM = 2 edges shorter, so cs[2] leaves ra 2 edges earlier and reaches rb's head-2 seam
// register on the SAME edge as in the uncut core.  Result: the composition is cycle-exact with the uncut
// ot_hbm_idx_score_hcol_h0 on every output (0 added cycles on every port); proven by the lock-step bench
// physical/die_plan/hbm/over_cap_split/reform_1103/bench/hcol_h0 (+ mutants that must FAIL).
// MUT (bench only): 1 = ra without the 2-edge advance (seam 2 late), 2 = rb head-3 term delay one edge short.
module ot_hbm_idx_score_hcol_h0_rgn #(
    parameter integer RR   = 0,          // region within the half column (0: heads 0-1, 1: heads 2-3)
    parameter integer SEAM = 2,          // face flops on the ra -> rb crossing (kit face shell: out + in)
    parameter integer MUT  = 0
) (
    input  wire            clk,
    input  wire            rst_col,
    input  wire            qv_b,
    input  wire [QW-1:0]   q_b,
    input  wire [KW-1:0]   key,
    input  wire [15:0]     hid2,         // head ids 2*RR, 2*RR+1
    input  wire [31:0]     cs_in,        // RR 1: cs[2] from ra (RR 0: unused)
    input  wire            cf_in,
    output wire [31:0]     cs_out,       // cs[2*RR+2]
    output wire            cf_out,
    output wire            prdy
);
    localparam integer NB = 4, FPL = 7, FML = 5, QL = 5;
    localparam integer KW = NB * 136;
    localparam integer QW = 8 + NB * 128 + NB * 8 + 16;
    localparam integer ADV = (RR == 0 && MUT != 1) ? SEAM : 0;   // edges region 0 runs ahead of the uncut core
    wire [31:0] cs [0:2]; wire cf [0:2];
    assign cs[0] = cs_in; assign cf[0] = cf_in;
    genvar hh, bb;
    wire ck = clk;
    wire [0:0] srr; wire rs = srr[0];
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(ck), .rst_n_in(rst_col), .rst_n(srr));
    reg rn_p, onl;
    always @(posedge ck) rn_p <= rs;
    always @(posedge ck or negedge rs) if (!rs) onl <= 1'b0; else onl <= rs && rn_p;
    assign prdy = onl;
    reg qv_p; reg [QW-1:0] q_p; reg [KW-1:0] key_p;
    always @(posedge ck) begin qv_p <= qv_b && rn_p; q_p <= q_b; key_p <= key; end
    wire [7:0] qh_p = q_p[QW-1 -: 8];
    generate for (hh = 0; hh < 2; hh = hh + 1) begin : g_h
        localparam integer H = 2 * RR + hh;              // head within the chunk column (0..3)
        localparam integer HL = hh;                      // head within this region
        localparam integer TD = (FPL + 2) * H - ((RR == 0 && hh == 1) ? ADV : 0) - ((MUT == 2 && H == 3) ? 1 : 0);
        reg [7:0] hid_p; always @(posedge ck) hid_p <= hid2[8*HL +: 8];
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
        ot_hdc_delay #(.W(17), .D(TD)) u_td (.clk(ck), .rst_n(1'b1), .d({rscf_d || tmo, tm0}), .q({tf, tm}));
        reg [31:0] csi_p; reg cfi_p; reg [31:0] cs_o; reg cf_o;
        always @(posedge ck) begin csi_p <= cs[HL]; cfi_p <= cf[HL]; end
        if (H == 0) begin : g_seed
            // seed low half is 0 by construction: 17 live bits down the unreset line (HBM-CORES-KITS-21 form)
            wire [16:0] seed_d;
            ot_hdc_delay #(.W(17), .D(FPL - ADV)) u_sd (.clk(ck), .rst_n(1'b1),
                .d({tf, (tm[14:0] == 15'd0) ? 16'd0 : tm}), .q(seed_d));
            always @(posedge ck) begin cs_o <= {seed_d[15:0], 16'd0}; cf_o <= seed_d[16]; end
        end else begin : g_sum
            wire [1:0] err; wire vo_unused; wire [31:0] sum; wire pf;
            ot_hdc_v41x_faddl #(.LAT(FPL)) u_a (.clk(ck), .rst_n(rs), .valid_in(1'b1),
                .a(csi_p), .b({tm, 16'd0}), .y(sum), .err(err), .valid_out(vo_unused));
            ot_hdc_delay #(.W(1), .D(FPL)) u_pf (.clk(ck), .rst_n(1'b1), .d(cfi_p || tf), .q(pf));
            always @(posedge ck) begin cs_o <= sum; cf_o <= pf || (err != 2'd0); end
        end
        assign cs[HL + 1] = cs_o; assign cf[HL + 1] = cf_o;
    end endgenerate
    assign cs_out = cs[2]; assign cf_out = cf[2];
endmodule

// The two hardened sub-blocks (two masters; every hcol_h0 instance = one ra + one rb).
module ot_hbm_idx_score_hcol_h0_ra__fcore #(parameter integer MUT = 0) (
    input wire clk, input wire rst_col, input wire qv_b, input wire [567:0] q_b, input wire [543:0] key,
    input wire [15:0] hid2, output wire [31:0] cs_out, output wire cf_out, output wire prdy);
    ot_hbm_idx_score_hcol_h0_rgn #(.RR(0), .MUT(MUT)) u_rgn (.clk(clk), .rst_col(rst_col), .qv_b(qv_b), .q_b(q_b), .key(key),
        .hid2(hid2), .cs_in(32'd0), .cf_in(1'b0), .cs_out(cs_out), .cf_out(cf_out), .prdy(prdy));
endmodule

module ot_hbm_idx_score_hcol_h0_rb #(parameter integer MUT = 0) (
    input wire clk, input wire rst_col, input wire qv_b, input wire [567:0] q_b, input wire [543:0] key,
    input wire [15:0] hid2, input wire [31:0] cs_in, input wire cf_in, output wire [31:0] cs_out, output wire cf_out,
    output wire prdy);
    ot_hbm_idx_score_hcol_h0_rgn #(.RR(1), .MUT(MUT)) u_rgn (.clk(clk), .rst_col(rst_col), .qv_b(qv_b), .q_b(q_b), .key(key),
        .hid2(hid2), .cs_in(cs_in), .cf_in(cf_in), .cs_out(cs_out), .cf_out(cf_out), .prdy(prdy));
endmodule
`default_nettype wire
