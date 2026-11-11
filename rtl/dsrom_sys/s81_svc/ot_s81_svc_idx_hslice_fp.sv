`timescale 1ns/1ps
// die-s81-85 2026-11-09 IRG "fastpad" safe form of ot_hdc_v41x_idx_hslice (opt-in; the original module is unchanged).
// Spec: claude/s81-svc-7-1108 results/rtl/svc_irg_fastpad_1113/model.json.
//   * Q beat and key pass pin to pin in 2 edges (pin flop + output flop): the internal FPL-stage forwarding delays
//     (u_qp / u_qv / u_kp of the original, 7 x (568 + 1 + 544) flops) are removed.  Q beats and keys keep the same
//     relative order at every slice, so each key meets exactly the query it met in the original.
//   * Because the key now reaches slice p 7*p edges earlier, the already-rounded BF16 head term (16 b) and its fault
//     (1 b) are delayed by FPL * p edges in front of the UNCHANGED running FP32 add and seed / fault branches, so cs_in
//     (pin flopped) and the term meet at the original dates and cs_out keeps its original age.
//   * One uniform view for all positions: a packed (HC-1)*FPL x 17 b delay line (49 x 17 at FPL 7) and a static
//     ID-select mux over HC = 8 taps (0, FPL, ..., 7*FPL).  The local position is hid[2:0] (the chunk straps hid =
//     8*gc + i); it is the registered strap hid_p, registered once more (pos_r) before it drives the mux select.
//   * All rounding steps (q4dot, serial block sums, BF16 conversion, BF16 weight product, final FP32 running sum / seed)
//     and their order are unchanged.
// Pin-to-pin: key_out = key_in + 2; q_out = q_in + 2; cs_out = key_in + LAT_T + FPL + 2 + FPL * hid[2:0].
// Chunk ages (positions 0..7): key in 0,2,..,14; cs_out 41,50,..,104 (unchanged); terminal Q / key out 16 (was 72).
module ot_s81_svc_idx_hslice_fp #(
    parameter integer NB  = 4,
    parameter integer FPL = 7,
    parameter integer FML = 5,
    parameter integer QL  = 5,
    // S81-SVCRS-3 11-10 (COORD ruling): PR = 1 models the recipe-4 pin registers of the physical svc_lo IRG box
    // (physical/ref_tile/s81svc_irg_hsfp/pin_regs.json enable): one more flop on every data input and every data
    // output (clk / rst_n excluded), +2 edges a hop, +16 a chain (the reader's EL 124 -> 140 in the SAME bind).
    // PR = 0 (default): this netlist is unchanged.
    parameter integer PR  = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [7:0]        hid,        // absolute head of this slice (strap, registered); hid[2:0] = local position
    input  wire              first,      // strap: head 0 of the chunk (seeds the sum)
    // q load in / out
    input  wire              ql_v,
    input  wire [7:0]        ql_head,
    input  wire [NB*128-1:0] ql_codes,
    input  wire [NB*8-1:0]   ql_sc,
    input  wire [15:0]       ql_w,
    output wire              qo_v,
    output wire [7:0]        qo_head,
    output wire [NB*128-1:0] qo_codes,
    output wire [NB*8-1:0]   qo_sc,
    output wire [15:0]       qo_w,
    // key in / out
    input  wire [NB*136-1:0] k_key,
    output wire [NB*136-1:0] ko_key,
    // running sum in / out
    input  wire [31:0]       cs_in,
    input  wire              cf_in,
    output wire [31:0]       cs_out,
    output wire              cf_out
);
    localparam integer KW = NB * 136;
    localparam integer LAT_SC = QL + FPL * (NB - 1);
    localparam integer LAT_T  = LAT_SC + 1 + FML;
    localparam integer HC = 8;                       // slices per chunk column (local position = hid[2:0])
    localparam integer PD = FPL * (HC - 1);          // deepest pad (49 at FPL 7)
    localparam integer TW = 17;                      // padded word: {fault, BF16 term}
    // reset standard: the port drives only the relay
    wire [0:0] srr; wire rs = srr[0];
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(srr));
    // ---- PR pin-register stage (S81-SVCRS-3 11-10): inputs i_*, core outputs c_* -> ports
    wire [7:0] hid_i; wire first_i; wire qlv_i; wire [7:0] qlh_i; wire [NB*128-1:0] qlc_i; wire [NB*8-1:0] qls_i;
    wire [15:0] qlw_i; wire [NB*136-1:0] key_i; wire [31:0] csi_i; wire cfi_i;
    reg qo_v_c; reg [7:0] qo_head_c; reg [NB*128-1:0] qo_codes_c; reg [NB*8-1:0] qo_sc_c; reg [15:0] qo_w_c;
    reg [31:0] cs_out_c; reg cf_out_c; wire [NB*136-1:0] ko_key_c;
    if (PR == 0) begin : g_pr0
        assign {hid_i, first_i, qlv_i, qlh_i, qlc_i, qls_i, qlw_i, key_i, csi_i, cfi_i} =
               {hid, first, ql_v, ql_head, ql_codes, ql_sc, ql_w, k_key, cs_in, cf_in};
        assign {qo_v, qo_head, qo_codes, qo_sc, qo_w, ko_key, cs_out, cf_out} =
               {qo_v_c, qo_head_c, qo_codes_c, qo_sc_c, qo_w_c, ko_key_c, cs_out_c, cf_out_c};
    end else if (PR == 1) begin : g_pr1
        reg [7:0] hid_r; reg first_r; reg qlv_r; reg [7:0] qlh_r; reg [NB*128-1:0] qlc_r; reg [NB*8-1:0] qls_r;
        reg [15:0] qlw_r; reg [NB*136-1:0] key_r; reg [31:0] csi_r; reg cfi_r;
        reg qo_v_r; reg [7:0] qo_head_r; reg [NB*128-1:0] qo_codes_r; reg [NB*8-1:0] qo_sc_r; reg [15:0] qo_w_r;
        reg [NB*136-1:0] ko_key_r; reg [31:0] cs_out_r; reg cf_out_r;
        always @(posedge clk) begin
            {hid_r, first_r, qlv_r, qlh_r, qlc_r, qls_r, qlw_r, key_r, csi_r, cfi_r} <=
                {hid, first, ql_v, ql_head, ql_codes, ql_sc, ql_w, k_key, cs_in, cf_in};
            {qo_v_r, qo_head_r, qo_codes_r, qo_sc_r, qo_w_r, ko_key_r, cs_out_r, cf_out_r} <=
                {qo_v_c, qo_head_c, qo_codes_c, qo_sc_c, qo_w_c, ko_key_c, cs_out_c, cf_out_c};
        end
        assign {hid_i, first_i, qlv_i, qlh_i, qlc_i, qls_i, qlw_i, key_i, csi_i, cfi_i} =
               {hid_r, first_r, qlv_r, qlh_r, qlc_r, qls_r, qlw_r, key_r, csi_r, cfi_r};
        assign {qo_v, qo_head, qo_codes, qo_sc, qo_w, ko_key, cs_out, cf_out} =
               {qo_v_r, qo_head_r, qo_codes_r, qo_sc_r, qo_w_r, ko_key_r, cs_out_r, cf_out_r};
    end else begin : g_pr_bad
        initial $fatal(1, "ot_s81_svc_idx_hslice_fp: PR must be 0 or 1");
    end
    // ---- pin flops
    reg rn_p; reg [7:0] hid_p; reg first_p;
    reg qv_p; reg [7:0] qh_p; reg [NB*128-1:0] qc_p; reg [NB*8-1:0] qs_p; reg [15:0] qw_p;
    reg [KW-1:0] key_p; reg [31:0] csi_p; reg cfi_p;
    always @(posedge clk) begin
        rn_p <= rs; hid_p <= hid_i; first_p <= first_i;
        qv_p <= qlv_i && rn_p; qh_p <= qlh_i; qc_p <= qlc_i; qs_p <= qls_i; qw_p <= qlw_i;
        key_p <= key_i; csi_p <= csi_i; cfi_p <= cfi_i;
    end
    // static local position, registered once more from the registered strap before it selects the pad tap.
    // DIE-S81-85 11-09 native census (<= 32 load pins per dynamic driver): PRC kept copies, copy j selects pad bits
    // 3j .. 3j+2 (identical flops; keep so synthesis does not merge them back).
    localparam integer PRC = 6;
    (* keep = "true", dont_touch = "true" *) reg [3*PRC-1:0] pos_rc;
    always @(posedge clk) pos_rc <= {PRC{hid_p[2:0]}};
    // ---- q load: own head written one edge after the compare (unchanged)
    // DIE-S81-85 11-09 native census: the write enable as QWC kept copies, copy j enables 16 of the 560 bits
    localparam integer QWB = NB * 128 + NB * 8 + 16;
    localparam integer QWC = (QWB + 15) / 16;
    (* keep = "true", dont_touch = "true" *) reg [QWC-1:0] q_we;
    reg [NB*128-1:0] q2c; reg [NB*8-1:0] q2s; reg [15:0] q2w;
    reg [NB*128-1:0] qc; reg [NB*8-1:0] qs; reg [15:0] qw;
    wire [QWB-1:0] q2a = {q2w, q2s, q2c};
    reg  [QWB-1:0] qa;
    always @(posedge clk) begin
        q_we <= {QWC{qv_p && rn_p && (qh_p == hid_p)}};
        q2c <= qc_p; q2s <= qs_p; q2w <= qw_p;
    end
    genvar qb;
    generate for (qb = 0; qb < QWB; qb = qb + 1) begin : g_qa
        always @(posedge clk) if (q_we[qb / 16]) qa[qb] <= q2a[qb];
    end endgenerate
    always @(*) {qw, qs, qc} = qa;
    // ---- q beat pass-through: 2 edges pin to pin (pin flop + output flop), same as the key
    always @(posedge clk) begin
        qo_v_c <= qv_p && rn_p; {qo_head_c, qo_codes_c, qo_sc_c, qo_w_c} <= {qh_p, qc_p, qs_p, qw_p};
    end
    // ---- key pass-through: 2 edges pin to pin
    reg [KW-1:0] key_o;
    always @(posedge clk) key_o <= key_p;
    assign ko_key_c = key_o;
    // ---- the head term (chunk_l g_head arithmetic, unchanged)
    wire [NB*128-1:0] kc; wire [NB*8-1:0] ks;
    genvar bb;
    generate for (bb = 0; bb < NB; bb = bb + 1) begin : g_skew
        localparam integer DS = (bb == 0) ? 0 : FPL * (bb - 1);
        wire [135:0] kb_d;
        ot_hdc_delay #(.W(136), .D(DS)) u_sk (.clk(clk), .rst_n(1'b1),
            .d({key_p[NB*128 + 8*bb +: 8], key_p[128*bb +: 128]}), .q(kb_d));
        assign kc[128*bb +: 128] = kb_d[127:0];
        assign ks[8*bb +: 8] = kb_d[135:128];
    end endgenerate
    wire [NB*32-1:0] acc; wire [NB-1:0] afault;
    generate for (bb = 0; bb < NB; bb = bb + 1) begin : g_blk
        wire [31:0] bv; wire bo;
        ot_hdc_v41x_q4dot_l #(.QL(QL)) u_d (.clk(clk), .a(qc[bb*128 +: 128]), .b(kc[128*bb +: 128]),
                               .ua(qs[bb*8 +: 8]), .ub(ks[8*bb +: 8]), .y(bv), .ovf(bo));
        if (bb == 0) begin : g_first
            assign acc[31:0] = bv; assign afault[0] = bo;
        end else begin : g_add
            wire [1:0] err; wire vo_unused; wire pf, bo_d;
            ot_hdc_delay #(.W(1), .D(FPL)) u_pf (.clk(clk), .rst_n(1'b1), .d(afault[bb-1]), .q(pf));
            ot_s81_svc_fp32_add_lat_cs #(.LAT(FPL), .DRST(0), .SWREP(4)) u_a (.clk(clk), .rst_n(rs), .valid_in(1'b1),
                .a(acc[32*(bb-1) +: 32]), .b(bv), .y(acc[32*bb +: 32]), .err(err), .valid_out(vo_unused));
            ot_hdc_delay #(.W(1), .D(FPL)) u_bf (.clk(clk), .rst_n(1'b1), .d(bo), .q(bo_d));
            assign afault[bb] = pf || bo_d || (err != 2'd0);
        end
    end endgenerate
    wire [15:0] sc16; wire sco;
    ot_hdc_v41x_bf16 u_sb (.x(acc[32*(NB-1) +: 32]), .y(sc16), .ovf(sco));
    reg [15:0] rsc; reg rscf;
    always @(posedge clk) begin rsc <= sc16; rscf <= afault[NB-1] || sco; end
    wire [15:0] tm_e; wire tmo, rscf_d;
    ot_hdc_v41x_bmul_l #(.ML(FML)) u_m (.clk(clk), .a(rsc), .w(qw), .y(tm_e), .ovf(tmo));
    ot_hdc_delay #(.W(1), .D(FML)) u_tf (.clk(clk), .rst_n(1'b1), .d(rscf), .q(rscf_d));
    wire tf_e = rscf_d || tmo;
    // ---- position pad: the rounded term + fault delayed FPL * pos edges (packed whole-vector shift, no reset on data)
    reg  [TW*PD-1:0] pad;
    always @(posedge clk) pad <= {pad[TW*(PD-1)-1:0], {tf_e, tm_e}};
    reg  [TW-1:0] pad_q;
    wire [TW-1:0] pad_t0 = {tf_e, tm_e};
    integer pb;
    always @(*) begin
        for (pb = 0; pb < TW; pb = pb + 1)
            case (pos_rc[3*(pb/3) +: 3])
                3'd0:    pad_q[pb] = pad_t0[pb];
                3'd1:    pad_q[pb] = pad[TW*(1*FPL-1) + pb];
                3'd2:    pad_q[pb] = pad[TW*(2*FPL-1) + pb];
                3'd3:    pad_q[pb] = pad[TW*(3*FPL-1) + pb];
                3'd4:    pad_q[pb] = pad[TW*(4*FPL-1) + pb];
                3'd5:    pad_q[pb] = pad[TW*(5*FPL-1) + pb];
                3'd6:    pad_q[pb] = pad[TW*(6*FPL-1) + pb];
                default: pad_q[pb] = pad[TW*(7*FPL-1) + pb];
            endcase
    end
    wire [15:0] tm = pad_q[15:0];
    wire tf = pad_q[16];
    // ---- running sum: unchanged; the padded term meets cs_in (pin flopped) at the original date
    wire [1:0] err; wire vo_unused;
    wire [31:0] sum;
    ot_s81_svc_fp32_add_lat_cs #(.LAT(FPL), .DRST(0), .SWREP(4)) u_a (.clk(clk), .rst_n(rs), .valid_in(1'b1),
        .a(csi_p), .b({tm, 16'd0}), .y(sum), .err(err), .valid_out(vo_unused));
    wire [32:0] seed_d;
    ot_hdc_delay #(.W(33), .D(FPL)) u_sd (.clk(clk), .rst_n(1'b1),
        .d({tf, (tm[14:0] == 15'd0) ? 32'd0 : {tm, 16'd0}}), .q(seed_d));
    wire pf;
    ot_hdc_delay #(.W(1), .D(FPL)) u_pf (.clk(clk), .rst_n(1'b1), .d(cfi_p || tf), .q(pf));
    always @(posedge clk) begin
        cs_out_c <= first_p ? seed_d[31:0] : sum;
        cf_out_c <= first_p ? seed_d[32] : (pf || (err != 2'd0));
    end
endmodule
