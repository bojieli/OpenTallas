`timescale 1ns/1ps
// el1011-hbm-idx 2026-10-11 (owner textbook audit: the 8-head chunk was 146.7k flops on one clock root, 52k async-reset;
// CTS hold repair stalled at -70 ps with ~48k endpoints in margin): ONE HEAD x ONE KEY of the indexer chunk as a hardened
// slice.  Every slice is identical (one view for all 32 positions of a chunk): the chunk is NKT columns of 8 slices and
// everything travels SYSTOLICALLY down a column on registered seams -- no broadcast across the chunk.
//   * q load: the beat enters at the pin flop, the slice compares its head with its strap hid (a registered pin), writes
//     its own query registers (2 edges, as ot_hdc_v41x_idx_chunk_l) and passes the beat on FPL + 2 edges a hop (as keys).
//   * key: pin flop -> NB block dots + NB-1 sequential block adds -> BF16 -> head-weight product = the head term
//     (LAT_T after the pin flop, exactly the chunk_l arithmetic), and the key passes on FPL + 2 edges a hop, so the next
//     slice's term meets this slice's running sum with no per-position delay.
//   * running sum: pin flop cs_in; first = 1 seeds (term -> FP32, -0 -> +0, delayed FPL like an add), else cs + term
//     (ot_hdc_v41x_faddl); registered out.  Fault ORs along, as chunk_l.
// Pin-to-pin: key_out = key_in + FPL + 2; q_out = q_in + FPL + 2; cs_out = key_in + LAT_T + FPL + 2.
module ot_hdc_v41x_idx_hslice #(
    parameter integer NB  = 4,
    parameter integer FPL = 7,
    parameter integer FML = 5,
    parameter integer QL  = 5
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [7:0]        hid,        // absolute head of this slice (strap, registered)
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
    // ---- q load: own head written one edge after the compare; beat passed on registered
    reg q_we; reg [NB*128-1:0] q2c; reg [NB*8-1:0] q2s; reg [15:0] q2w;
    reg [NB*128-1:0] qc; reg [NB*8-1:0] qs; reg [15:0] qw;
    always @(posedge clk) begin
        q_we <= qv_p && rn_p && (qh_p == hid_p);
        q2c <= qc_p; q2s <= qs_p; q2w <= qw_p;
        if (q_we) begin qc <= q2c; qs <= q2s; qw <= q2w; end
    end
    // the q beat passes on FPL + 2 pin to pin, the same as a key, so q loads and keys keep their input order at every
    // slice (a key sees exactly the query it would have seen in chunk_l)
    localparam integer QW = 8 + NB * 128 + NB * 8 + 16;
    wire [QW-1:0] qb_d; wire qv_d;
    ot_hdc_delay #(.W(QW), .D(FPL)) u_qp (.clk(clk), .rst_n(1'b1), .d({qh_p, qc_p, qs_p, qw_p}), .q(qb_d));
    ot_hdc_delay #(.W(1), .D(FPL), .RESET(1)) u_qv (.clk(clk), .rst_n(rs), .d(qv_p && rn_p), .q(qv_d));
    always @(posedge clk) begin
        qo_v <= qv_d && rn_p; {qo_head, qo_codes, qo_sc, qo_w} <= qb_d;
    end
    // ---- key pass-through: FPL + 2 pin to pin (pin flop + FPL + output flop)
    wire [KW-1:0] key_d;
    ot_hdc_delay #(.W(KW), .D(FPL)) u_kp (.clk(clk), .rst_n(1'b1), .d(key_p), .q(key_d));
    reg [KW-1:0] key_o;
    always @(posedge clk) key_o <= key_d;
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
    wire [15:0] tm; wire tmo, rscf_d;
    ot_hdc_v41x_bmul_l #(.ML(FML)) u_m (.clk(clk), .a(rsc), .w(qw), .y(tm), .ovf(tmo));
    ot_hdc_delay #(.W(1), .D(FML)) u_tf (.clk(clk), .rst_n(1'b1), .d(rscf), .q(rscf_d));
    wire tf = rscf_d || tmo;
    // ---- running sum: the term is formed LAT_T after key_p, when cs_in (pin flopped) arrives
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
