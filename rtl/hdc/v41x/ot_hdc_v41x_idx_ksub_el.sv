`timescale 1ns/1ps
// el1011-ds-misc/idx 2026-10-11: the HARDENED SUB-TILE of the indexer chunk element = ONE key lane of an 8-head chunk
// (8 heads x NB block dots + the 8-term head chain for one key a cycle).  ot_hdc_v41x_idx_chunk_el is 4 of these (one per
// key lane, NKT 4) placed as macros, with the q-load broadcast to all four.
//
// Why (flat chunk hgi-idx-chunk-{a,b}-9473077de): one 760 x 760 block with 146,738 clock sinks at 28 % utilisation;
// CTS arrival 518..833 ps, average sink wire 1,145 um, SS setup -272 / -437 on ~46k endpoints, FF hold stuck at -70 on
// the input captures (rql_codes / rkey / rql_head) after 12.5k-15k hold buffers.  Structural causes fixed here:
//   * 52,337 of the flops were DFFASRHQN: every FP32-add DATA flop (124 adders) carried rst_n's asynchronous clear, so
//     the rst_n port drove 52k loads.  The adders here are DRST 0 (only their valid bits reset; valid_out is unused, so
//     those fold away): the chain is feed-forward and every stage is overwritten before a valid beat reaches it, so the
//     reset value never reaches a valid output (bit-exact vs chunk_l, lockstep bench).  rst_n now reaches ~170 flops.
//   * one clock tree over the whole chunk: the sub-tile is ~1/4 of it (one key lane, ~40k flops) at 50-57 %.
//   * fan-out: the q-load write enable drove a head's 553 query flops from one flop; here it is replicated per head per
//     query block (NB + 1 copies per head, <= 136 loads each).  The key capture is replicated per head quad (KR 2, kept
//     copies) so a key flop and its skew line feed 4 block dots, not 8.  The query registers are per key lane (each
//     lane holds its own copy: NKT x the query flops of the flat chunk, ~4.4k flops a lane).
//   * every input is a pin flop (hb too: the head-base subtract moved behind the pin flops, same cycle as before), every
//     output is a flop (c_v / c_kv / c_sum / c_fault).
// Latency and function are those of ot_hdc_v41x_idx_chunk_l #(NKT 1, HB hb): 0 added cycles.
module ot_hdc_v41x_idx_ksub_el #(
    parameter integer NB  = 4,
    parameter integer FPL = 7,
    parameter integer FML = 5,
    parameter integer QL  = 5,
    parameter integer KR  = 2         // key-capture replicas (each serves HC / KR heads)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [7:0]        hb,
    input  wire              ql_v,
    input  wire [7:0]        ql_head,
    input  wire [NB*128-1:0] ql_codes,
    input  wire [NB*8-1:0]   ql_sc,
    input  wire [15:0]       ql_w,
    input  wire              k_v,
    input  wire              k_kv,
    input  wire [NB*136-1:0] k_key,
    output reg               c_v,
    output reg               c_kv,
    output reg  [31:0]       c_sum,
    output reg               c_fault
);
    localparam integer HC = 8;
    localparam integer HPR = HC / KR;
    localparam integer KW = NB * 136;
    localparam integer LAT_SC = QL + FPL * (NB - 1);
    localparam integer LAT_T  = LAT_SC + 1 + FML;
    localparam integer LAT    = LAT_T + FPL * (HC - 1);

    // -- q load: pin flops, then a replicated per-head per-block write enable ---------------------------------------
    reg              rql_v;
    reg [7:0]        rql_head, rhb;
    reg [NB*128-1:0] rql_codes, rq2_codes;
    reg [NB*8-1:0]   rql_sc, rq2_sc;
    reg [15:0]       rql_w, rq2_w;
    wire [7:0]       lhead = rql_head - rhb;          // = (ql_head - hb) registered: chunk_l's rql_head
    always @(posedge clk) begin
        rql_v <= ql_v && rst_n;
        rql_head <= ql_head;
        rhb <= hb;
        rql_codes <= ql_codes;
        rql_sc <= ql_sc;
        rql_w <= ql_w;
        rq2_codes <= rql_codes;
        rq2_sc <= rql_sc;
        rq2_w <= rql_w;
    end

    reg [HC*NB*128-1:0] qc;
    reg [HC*NB*8-1:0]   qs;
    reg [HC*16-1:0]     qw;
    genvar g, h, bb;
    generate
        for (h = 0; h < HC; h = h + 1) begin : g_qw
            // NB + 1 enable copies per head: copy b writes query block b (128 codes + 8 scale), copy NB the head weight
            (* keep = "true" *) reg [NB:0] we;
            always @(posedge clk) we <= {(NB + 1){rst_n && rql_v && (lhead == h)}};
            for (bb = 0; bb < NB; bb = bb + 1) begin : g_b
                always @(posedge clk) if (we[bb]) begin
                    qc[(h*NB+bb)*128 +: 128] <= rq2_codes[128*bb +: 128];
                    qs[(h*NB+bb)*8 +: 8] <= rq2_sc[8*bb +: 8];
                end
            end
            always @(posedge clk) if (we[NB]) qw[h*16 +: 16] <= rq2_w;
        end
    endgenerate

    // -- key: pin flops, KR kept replicas ---------------------------------------------------------------------------
    reg rv, rkv;
    always @(posedge clk) begin
        rv <= k_v && rst_n;
        rkv <= k_kv;
    end
    wire [1:0] vl;
    ot_hdc_delay #(.W(2), .D(LAT), .RESET(1)) u_vl (.clk(clk), .rst_n(rst_n), .d({rkv, rv}), .q(vl));

    wire [HC*16-1:0] term;
    wire [HC-1:0]    tfault;
    generate
        for (g = 0; g < KR; g = g + 1) begin : g_kr
            (* keep = "true" *) reg [KW-1:0] rkey;
            always @(posedge clk) rkey <= k_key;
            wire [NB*128-1:0] kc;
            wire [NB*8-1:0]   ks;
            for (bb = 0; bb < NB; bb = bb + 1) begin : g_skew
                localparam integer DS = (bb == 0) ? 0 : FPL * (bb - 1);
                wire [135:0] kb_d;
                ot_hdc_delay #(.W(136), .D(DS)) u_sk (.clk(clk), .rst_n(rst_n),
                    .d({rkey[NB*128 + 8*bb +: 8], rkey[128*bb +: 128]}), .q(kb_d));
                assign kc[128*bb +: 128] = kb_d[127:0];
                assign ks[8*bb +: 8] = kb_d[135:128];
            end

            for (h = g * HPR; h < (g + 1) * HPR; h = h + 1) begin : g_head
                wire [NB*32-1:0] acc;
                wire [NB-1:0] afault;
                for (bb = 0; bb < NB; bb = bb + 1) begin : g_blk
                    wire [31:0] bv;
                    wire        bo;
                    ot_hdc_v41x_q4dot_l #(.QL(QL)) u_d (.clk(clk), .a(qc[(h*NB+bb)*128 +: 128]), .b(kc[128*bb +: 128]),
                                           .ua(qs[(h*NB+bb)*8 +: 8]), .ub(ks[8*bb +: 8]), .y(bv), .ovf(bo));
                    if (bb == 0) begin : g_first
                        assign acc[31:0] = bv;
                        assign afault[0] = bo;
                    end else begin : g_add
                        wire [1:0] err;
                        wire       vo_unused;
                        wire       pf;
                        ot_hdc_delay #(.W(1), .D(FPL)) u_pf (.clk(clk), .rst_n(rst_n), .d(afault[bb-1]), .q(pf));
                        ot_hdc_fp32_add_lat #(.LAT(FPL), .DRST(0)) u_a (.clk(clk), .rst_n(rst_n), .valid_in(1'b1),
                            .a(acc[32*(bb-1) +: 32]), .b(bv), .y(acc[32*bb +: 32]), .err(err), .valid_out(vo_unused));
                        wire bo_d;
                        ot_hdc_delay #(.W(1), .D(FPL)) u_bf (.clk(clk), .rst_n(rst_n), .d(bo), .q(bo_d));
                        assign afault[bb] = pf || bo_d || (err != 2'd0);
                    end
                end
                wire [15:0] sc16;
                wire        sco;
                ot_hdc_v41x_bf16 u_sb (.x(acc[32*(NB-1) +: 32]), .y(sc16), .ovf(sco));
                reg  [15:0] rsc;
                reg         rscf;
                always @(posedge clk) begin
                    rsc <= sc16;
                    rscf <= afault[NB-1] || sco;
                end
                wire [15:0] tm;
                wire        tmo;
                ot_hdc_v41x_bmul_l #(.ML(FML)) u_m (.clk(clk), .a(rsc), .w(qw[16*h +: 16]), .y(tm), .ovf(tmo));
                wire        rscf_d;
                ot_hdc_delay #(.W(1), .D(FML)) u_tf (.clk(clk), .rst_n(rst_n), .d(rscf), .q(rscf_d));
                assign term[16*h +: 16] = tm;
                assign tfault[h] = rscf_d || tmo;
            end
        end
    endgenerate

    // -- the head chain: seed with term 0 (-0 -> +0), then 7 adds; term j joins at add j, FPL(j-1) cycles later ------
    wire [HC*32-1:0] cs;
    wire [HC-1:0] cf;
    assign cs[31:0] = (term[14:0] == 15'd0) ? 32'd0 : {term[15:0], 16'd0};
    assign cf[0] = tfault[0];
    generate
        for (h = 1; h < HC; h = h + 1) begin : g_chain
            wire [16:0] tj;
            ot_hdc_delay #(.W(17), .D(FPL * (h - 1))) u_tj (.clk(clk), .rst_n(rst_n),
                .d({tfault[h], term[16*h +: 16]}), .q(tj));
            wire [1:0] err;
            wire       vo_unused;
            ot_hdc_fp32_add_lat #(.LAT(FPL), .DRST(0)) u_a (.clk(clk), .rst_n(rst_n), .valid_in(1'b1),
                .a(cs[32*(h-1) +: 32]), .b({tj[15:0], 16'd0}), .y(cs[32*h +: 32]), .err(err), .valid_out(vo_unused));
            wire pf;
            ot_hdc_delay #(.W(1), .D(FPL)) u_pf (.clk(clk), .rst_n(rst_n), .d(cf[h-1] || tj[16]), .q(pf));
            assign cf[h] = pf || (err != 2'd0);
        end
    endgenerate
    always @(posedge clk) begin
        c_sum <= cs[32*(HC-1) +: 32];
        c_fault <= cf[HC-1];
        c_v <= vl[0] && rst_n;
        c_kv <= vl[1];
    end
endmodule
