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
module ot_hdc_v41x_idx_hslice_fp #(
    parameter integer NB  = 4,
    parameter integer FPL = 7,
    parameter integer FML = 5,
    parameter integer QL  = 5
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
    output reg               qo_v,
    output reg  [7:0]        qo_head,
    output reg  [NB*128-1:0] qo_codes,
    output reg  [NB*8-1:0]   qo_sc,
    output reg  [15:0]       qo_w,
    // key in / out
    input  wire [NB*136-1:0] k_key,
    output wire [NB*136-1:0] ko_key,
    // running sum in / out
    input  wire [31:0]       cs_in,
    input  wire              cf_in,
    output reg  [31:0]       cs_out,
    output reg               cf_out
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
    // ---- pin flops
    reg rn_p; reg [7:0] hid_p; reg first_p;
    reg qv_p; reg [7:0] qh_p; reg [NB*128-1:0] qc_p; reg [NB*8-1:0] qs_p; reg [15:0] qw_p;
    reg [KW-1:0] key_p; reg [31:0] csi_p; reg cfi_p;
    always @(posedge clk) begin
        rn_p <= rs; hid_p <= hid; first_p <= first;
        qv_p <= ql_v && rn_p; qh_p <= ql_head; qc_p <= ql_codes; qs_p <= ql_sc; qw_p <= ql_w;
        key_p <= k_key; csi_p <= cs_in; cfi_p <= cf_in;
    end
    // static local position, registered once more from the registered strap before it selects the pad tap
    reg [2:0] pos_r;
    always @(posedge clk) pos_r <= hid_p[2:0];
    // ---- q load: own head written one edge after the compare (unchanged)
    reg q_we; reg [NB*128-1:0] q2c; reg [NB*8-1:0] q2s; reg [15:0] q2w;
    reg [NB*128-1:0] qc; reg [NB*8-1:0] qs; reg [15:0] qw;
    always @(posedge clk) begin
        q_we <= qv_p && rn_p && (qh_p == hid_p);
        q2c <= qc_p; q2s <= qs_p; q2w <= qw_p;
        if (q_we) begin qc <= q2c; qs <= q2s; qw <= q2w; end
    end
    // ---- q beat pass-through: 2 edges pin to pin (pin flop + output flop), same as the key
    always @(posedge clk) begin
        qo_v <= qv_p && rn_p; {qo_head, qo_codes, qo_sc, qo_w} <= {qh_p, qc_p, qs_p, qw_p};
    end
    // ---- key pass-through: 2 edges pin to pin
    reg [KW-1:0] key_o;
    always @(posedge clk) key_o <= key_p;
    assign ko_key = key_o;
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
            ot_hdc_v41x_faddl #(.LAT(FPL)) u_a (.clk(clk), .rst_n(rs), .valid_in(1'b1),
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
    always @(*) begin
        case (pos_r)
            3'd0:    pad_q = {tf_e, tm_e};
            3'd1:    pad_q = pad[TW*(1*FPL)-1 -: TW];
            3'd2:    pad_q = pad[TW*(2*FPL)-1 -: TW];
            3'd3:    pad_q = pad[TW*(3*FPL)-1 -: TW];
            3'd4:    pad_q = pad[TW*(4*FPL)-1 -: TW];
            3'd5:    pad_q = pad[TW*(5*FPL)-1 -: TW];
            3'd6:    pad_q = pad[TW*(6*FPL)-1 -: TW];
            default: pad_q = pad[TW*(7*FPL)-1 -: TW];
        endcase
    end
    wire [15:0] tm = pad_q[15:0];
    wire tf = pad_q[16];
    // ---- running sum: unchanged; the padded term meets cs_in (pin flopped) at the original date
    wire [1:0] err; wire vo_unused;
    wire [31:0] sum;
    ot_hdc_v41x_faddl #(.LAT(FPL)) u_a (.clk(clk), .rst_n(rs), .valid_in(1'b1),
        .a(csi_p), .b({tm, 16'd0}), .y(sum), .err(err), .valid_out(vo_unused));
    wire [32:0] seed_d;
    ot_hdc_delay #(.W(33), .D(FPL)) u_sd (.clk(clk), .rst_n(1'b1),
        .d({tf, (tm[14:0] == 15'd0) ? 32'd0 : {tm, 16'd0}}), .q(seed_d));
    wire pf;
    ot_hdc_delay #(.W(1), .D(FPL)) u_pf (.clk(clk), .rst_n(1'b1), .d(cfi_p || tf), .q(pf));
    always @(posedge clk) begin
        cs_out <= first_p ? seed_d[31:0] : sum;
        cf_out <= first_p ? seed_d[32] : (pf || (err != 2'd0));
    end
endmodule
