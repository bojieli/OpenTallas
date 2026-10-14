`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen3-8B TP8 two-die split (owner 2026-10-14 06:45 PT), KV/system die: the LINK BRIDGE (die master qkd_lnk), abutting
// the KV end of the link (qkd_d2d = ot_qkvd_kv_end, SPL thin cluster over its closed hard tiles).  Contract:
// results/arch/qwen_split_1014/LINK.md.
//
// It turns the KV end's class faces into the merged sequencer's ROM-side faces (ot_qkvd_kv_seq_merged / cluster qkd_seq,
// UNCHANGED: the split keeps the closed sequencer leaves) and the embedding gateway's SU face:
//   r[0] CTL   -> op 1 SD:  sd (56 b levels) = data[55:0];  op 2 KVD: kvd pulse {1, data[42:0]} one cycle
//   r[1] Q, r[2] KVN -> x3 {v, tag 11, d 512}: the sequencer's ONE x3 credit pool XS (= 40 = one native layer 36 words
//              + 4) is held here; KVN first (a layer starts on its 4 KVN words), then Q, each in arrival order
//   r[3] EMBQ  -> ea {v, kind, addr 24} to qkd_embgw (credit ea_cr per request; the gateway's RQD buffer)
//   ar (sequencer RES, 519 b) -> t[0] RES: a direct wire pair (t_v / t_d, credit t_cr = the sequencer's ar_cr);
//              the sequencer's OCR_AR must equal the KV end's RES die-face buffer (UCX)
//   eq (gateway EMBD 512 b, posted) -> t[1] EMBD (posted: the gateway answers only requests that hold a KV-end EMBD
//              slot; the bridge counts them and faults on an overrun)
//   ds 187 b + pw 75 b (sequencer -> ROM sequencer / ROM control tile) -> t[2] SCTL event words (ot_qwen_split_lvl_tx,
//              pulses h_start ds[42], pws_v ds[118], dwo_v ds[186], pw_v pw[74])
// Word formats (tag 16 | data 512, as ot_qkvd_rom_end):
//   CTL  tag[15:12] = 1 SD {data[55:0] = sd}; 2 KVD {data[42:0] = kvd[42:0]}
//   Q    {10'd0, beat 6 | 16 FP32}            KVN {13'd0, tag 3 | 64 E4M3 bytes}
//   RES  {9'd0, g, beat 6, 16 FP32} = ar_d[518:0] zero-extended
//   SCTL tag[15:12] = 3; data[261:0] = {pw 75, ds 187}
// Every face input is captured at a pin flop, every output launched from a flop.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_split_kvlink #(
    parameter integer W    = 528,
    parameter integer QB   = 8,             // Q bridge FIFO (= the KV end's Q die-face credits, kv_end QD)
    parameter integer KB   = 8,             // KVN bridge FIFO (= the KV end's KVN die-face credits, fixed 8)
    parameter integer XS   = 40,            // the sequencer's x3 credits
    parameter integer EB   = 32,            // EMBD slots of the KV end (UCX >= EB)
    parameter integer ECR  = 32,            // gateway request credits
    parameter integer SC0  = 4,             // SCTL die-face credits of the KV end (its UCX for class 6 is 4: IBD[2])
    parameter integer MUT  = 0              // bench: 1 = KVN tag bit 2 dropped (v rows posted as k)
) (
    input  wire            clk,
    input  wire            rst_n,
    // KV end die faces (ot_qkvd_kv_end: r = CTL Q KVN EMBQ, t = RES EMBD HCTL/SCTL)
    input  wire [3:0]      r_v,
    input  wire [4*W-1:0]  r_d,
    output reg  [3:0]      r_cr,
    output wire [2:0]      t_v,
    output wire [3*W-1:0]  t_d,
    input  wire [2:0]      t_cr,
    // sequencer ROM-side faces
    output reg             x3_v,
    output reg  [10:0]     x3_tag,
    output reg  [511:0]    x3_d,
    input  wire            x3_cr,
    output reg  [55:0]     sd,
    output reg  [43:0]     kvd,
    input  wire            ar_v,
    input  wire [518:0]    ar_d,
    output wire            ar_cr,
    input  wire [186:0]    ds,
    input  wire [74:0]     pw,
    // embedding gateway SU face
    output reg             ea_v,
    output reg             ea_kind,
    output reg  [23:0]     ea_addr,
    input  wire            ea_cr,
    input  wire            eq_v,
    input  wire [511:0]    eq_d,
    // the KV end's sticky fault + cause (link sequence / credit / overrun): folded into fault (-> host status)
    input  wire            d2d_fault,
    input  wire [4:0]      d2d_cause,
    output reg             fault
);
    // ---- pin capture ----
    reg [3:0]     rv;
    reg [4*W-1:0] rd;
    reg           xcq, ecq, eqv;
    reg [511:0]   eqd;
    always @(posedge clk) begin rd <= r_d; eqd <= eq_d; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rv <= 4'd0; xcq <= 1'b0; ecq <= 1'b0; eqv <= 1'b0; end
        else begin rv <= r_v; xcq <= x3_cr; ecq <= ea_cr; eqv <= eq_v; end
    wire [W-1:0] w_ctl = rd[0*W +: W], w_q = rd[1*W +: W], w_kv = rd[2*W +: W], w_eq = rd[3*W +: W];
    // ---- Q / KVN -> x3 ----
    wire          qe, qf, ke, kf, ee, ef;
    wire [517:0]  qh;                        // {beat 6, data 512}
    wire [514:0]  kh;                        // {tag 3, data 512}
    wire [24:0]   eh;
    reg  [7:0]    xc, ec;
    wire          kpop = !ke && xc != 8'd0;
    wire          qpop = !qe && xc != 8'd0 && ke;
    wire          epop = !ee && ec != 8'd0;
    ot_qkvd_fifo #(.RH(1), .W(518), .D(QB)) u_q (.clk(clk), .rst_n(rst_n), .push(rv[1]), .din({w_q[517:512], w_q[511:0]}),
        .pop(qpop), .dout(qh), .empty(qe), .full(qf), .count());
    ot_qkvd_fifo #(.RH(1), .W(515), .D(KB)) u_k (.clk(clk), .rst_n(rst_n), .push(rv[2]), .din({w_kv[514:512], w_kv[511:0]}),
        .pop(kpop), .dout(kh), .empty(ke), .full(kf), .count());
    ot_qkvd_fifo #(.RH(1), .W(25), .D(32)) u_e (.clk(clk), .rst_n(rst_n), .push(rv[3]), .din({w_eq[512], w_eq[23:0]}),
        .pop(epop), .dout(eh), .empty(ee), .full(ef), .count());
    wire [2:0] ktag = (MUT == 1) ? {1'b0, kh[513:512]} : kh[514:512];
    // ---- CTL ----
    wire [3:0] cop = w_ctl[527:524];
    // ---- RES / EMBD / SCTL toward the KV end ----
    wire        sv;
    wire [261:0] sdat;
    wire        sfault;
    reg  [7:0]  eb;                          // EMBD slots of the KV end in hand
    reg         crq0, crq1, crq2;
    ot_qwen_split_lvl_tx #(.W(262), .PM(262'(1) << 261 | 262'(1) << 186 | 262'(1) << 118 | 262'(1) << 42), .C0(SC0)) u_sc (
        .clk(clk), .rst_n(rst_n), .face({pw, ds}), .v(sv), .d(sdat), .cr(crq2), .fault(sfault));
    reg          tv0, tv1;
    reg  [518:0] td0;
    reg  [511:0] td1;
    always @(posedge clk) begin td0 <= ar_d; td1 <= eqd; end
    assign t_v = {sv, tv1, tv0};
    assign t_d = {{4'd3, 12'd0, 250'd0, sdat}, {16'd0, td1}, {9'd0, td0}};
    assign ar_cr = crq0;
    reg f_ctl, f_ovr, f_emb, dfq;
    always @(posedge clk or negedge rst_n) if (!rst_n) dfq <= 1'b0; else dfq <= d2d_fault;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            x3_v <= 1'b0; x3_tag <= 11'd0; sd <= 56'd0; kvd <= 44'd0; ea_v <= 1'b0; ea_kind <= 1'b0; ea_addr <= 24'd0;
            r_cr <= 4'd0; xc <= 8'(XS); ec <= 8'(ECR); eb <= 8'(EB); tv0 <= 1'b0; tv1 <= 1'b0;
            crq0 <= 1'b0; crq1 <= 1'b0; crq2 <= 1'b0; f_ctl <= 1'b0; f_ovr <= 1'b0; f_emb <= 1'b0; fault <= 1'b0;
        end else begin
            crq0 <= t_cr[0]; crq1 <= t_cr[1]; crq2 <= t_cr[2];
            tv0 <= ar_v; tv1 <= eqv;
            // CTL: consumed on arrival
            kvd[43] <= 1'b0;
            if (rv[0]) begin
                if (cop == 4'd1) sd <= w_ctl[55:0];
                else if (cop == 4'd2) kvd <= {1'b1, w_ctl[42:0]};
                else f_ctl <= 1'b1;
            end
            // x3: KVN before Q (one credit pool)
            x3_v <= kpop || qpop;
            if (kpop) begin x3_tag <= {3'b010, 5'd0, ktag}; x3_d <= kh[511:0]; end
            else if (qpop) begin x3_tag <= {3'b001, 2'd0, qh[517:512]}; x3_d <= qh[511:0]; end
            xc <= xc - ((kpop || qpop) ? 8'd1 : 8'd0) + (xcq ? 8'd1 : 8'd0);
            // EMBQ -> gateway
            ea_v <= epop;
            if (epop) begin ea_kind <= eh[24]; ea_addr <= eh[23:0]; end
            ec <= ec - (epop ? 8'd1 : 8'd0) + (ecq ? 8'd1 : 8'd0);
            // EMBD slots: one taken per posted gateway word, one back per KV-end credit
            eb <= eb - (eqv ? 8'd1 : 8'd0) + (crq1 ? 8'd1 : 8'd0);
            if (eqv && eb == 8'd0) f_emb <= 1'b1;
            // credits back to the KV end's die faces: CTL at once, the rest when the word leaves the bridge
            r_cr <= {epop, kpop, qpop, rv[0]};
            if ((rv[1] && qf && !qpop) || (rv[2] && kf && !kpop) || (rv[3] && ef && !epop)) f_ovr <= 1'b1;
            fault <= f_ctl | f_ovr | f_emb | sfault | dfq;
        end
endmodule
