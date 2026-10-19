`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen KV die, RTL-BUILD-KV/BOOT 2026-10-18 (results/arch/qwen_kv_boot_path_1018/note.md): the static PC chain carries
// the EMBEDDING BOOT WORDS (the removed per-stack strips' BOOT_WR delivery) on its existing lane-0 pc / data / address
// fields, with one new valid bit:
//   qkd_kv_es_fan_root2_b = qkd_kv_es_fan_root2 + boot face bw (pin flop) + h[783] BV.  On a boot edge the word's
//                           stack / pc / data / address replace lane A's DST / PA / DA / AD (AV stays 0, so no writer
//                           lane hits); a writer or expected event (or the lanes-2/3 edge) on a boot edge latches fault.
//   qkd_kv_es_fan_stack_b = qkd_kv_es_fan_stack + chain bit F_BT = 779 (W 780): BV && DST == stack.
// Writer / expected / token-start / calendar fields and their edges are UNCHANGED (h[782:0] and d[778:0] equal the
// originals' bit for bit whenever bw is idle: tb_kv_boot_chain lockstep).  Boot word age root input -> station:
// as a writer lane 0 word (kvjc3_pc_chain writer_ages).  Boot is elastic (init phase): no compiled slot is added.
// MUT (bench only): root2_b 1 = a boot word overrides a writer edge with no fault.
// ---------------------------------------------------------------------------------------------------------------------
module qkd_kv_es_fan_root2_b #(parameter integer MUT = 0, parameter integer RCOPIES = 1) (
    input  wire            ck,
    input  wire            rst_n,
    input  wire [4*288-1:0] es,
    input  wire [19:0]     dest_pc,
    input  wire [1:0]      dest_stack,
    input  wire [58:0]     identity,
    input  wire [1:0]      generation,
    input  wire [3:0]      expected_valid,
    input  wire [19:0]     expected_pc,
    input  wire [1:0]      expected_stack,
    input  wire [58:0]     expected_identity,
    input  wire [1:0]      expected_generation,
    input  wire [28:0]     expected_address,
    input  wire            emb_start,
    input  wire [17:0]     emb_token,
    input  wire [15:0]     emb_epoch,
    input  wire            cfg_we,
    input  wire [7:0]      cfg_addr,
    input  wire [63:0]     cfg_data,
    // BOOT (RTL-BUILD-KV/BOOT): the embedding boot word from qkd_embgw_boot_s
    //   bw = {data 256, address 29 = {bank, col, row}, pc 5, stack 2, v}
    input  wire [292:0]    bw,
    output reg  [783:0]    h,
    output reg             fault
);
    // ---- pin flops (identical to qkd_kv_es_fan_root) ----
    (* keep *) reg rs_q;
    always @(posedge ck) rs_q <= rst_n;
    // KV-GRP-CTL/MU5 10-19: RCOPIES > 1 = that many KEPT identical copies of rs_q (family wire g_rc.rsv, ot_rst_split)
    // for the synthesis reset-relay split (physical/common_flow/ot_rst_copies.py); default 1 = unchanged.
    generate if (RCOPIES > 1) begin : g_rc
        (* keep *) reg [RCOPIES-2:0] rc_q;
        always @(posedge ck) rc_q <= {(RCOPIES-1){rst_n}};
        (* keep, ot_rst_split *) wire [RCOPIES-1:0] rsv = {rc_q, rs_q};
    end endgenerate
    reg [4*288-1:0] es_p; reg [19:0] dpc_p, epc_p; reg [1:0] dst_p, gen_p, est_p, egen_p;
    reg [58:0] id_p, eid_p; reg [28:0] ea_p; reg [17:0] tok_p; reg [15:0] ep_p; reg [7:0] ca_p; reg [63:0] cd_p;
    reg [3:0] ev_p; reg ss_p, cw_p;
    always @(posedge ck) begin
        es_p <= es; dpc_p <= dest_pc; dst_p <= dest_stack; id_p <= identity; gen_p <= generation;
        epc_p <= expected_pc; est_p <= expected_stack; eid_p <= expected_identity; egen_p <= expected_generation;
        ea_p <= expected_address; tok_p <= emb_token; ep_p <= emb_epoch; ca_p <= cfg_addr; cd_p <= cfg_data;
        bw_p[292:1] <= bw[292:1];
    end
    reg [292:0] bw_p;
    always @(posedge ck or negedge rs_q) if (!rs_q) bw_p[0] <= 1'b0; else bw_p[0] <= bw[0];
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin ev_p <= 4'd0; ss_p <= 1'b0; cw_p <= 1'b0; end
        else begin ev_p <= expected_valid; ss_p <= emb_start; cw_p <= cfg_we; end
    wire [3:0] wv_p = {es_p[864], es_p[576], es_p[288], es_p[0]};
    wire ev_now = (|ev_p) | (|wv_p);
    reg  ph1; reg [1:0] wv23, ev23;
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin ph1 <= 1'b0; wv23 <= 2'd0; ev23 <= 2'd0; end
        else begin ph1 <= ev_now && MUT != 2; wv23 <= wv_p[3:2]; ev23 <= ev_p[3:2]; end
    wire [1:0]   av = ph1 ? wv23 : wv_p[1:0];
    wire [1:0]   xv = ph1 ? ev23 : ev_p[1:0];
    wire [1:0]   lo = ph1 ? 2'd2 : 2'd0;
    wire [1:0]   hi = lo | 2'd1;
    wire c_pc = cw_p && cd_p[63:62] == 2'd0;
    wire c_bad = cw_p && (cd_p[63] || (cd_p[63:62] == 2'd0 && cd_p[61:18] != 44'd0));
    // ---- boot word: rides lane A's pc / data / address fields with its own valid BV (bit 783).  Boot is the
    //      exceptional init phase: the writer is idle by construction; a writer / expected event or the lanes-2/3
    //      edge on a boot edge latches fault and the WRITER keeps its fields (the boot word is dropped).
    wire bt   = bw_p[0] && !ev_now && !ph1;
    wire bt_x = bw_p[0] && (ev_now || ph1);
    wire use_b = (MUT == 1) ? bw_p[0] : bt;
    // ---- the edge word (field map: qkd_kv_es_fan_half) ----
    wire [782:0] hn = {cd_p[15:0], ca_p[2:0], ca_p[7:3], cd_p[17:16], c_pc,                 // CVL CRG CPC CST CV
                       ep_p, tok_p, ss_p,                                                    // EP TOK SS
                       ea_p, {eid_p, egen_p}, {id_p, gen_p}, es_p[286],                      // EAD EID CTX SV
                       use_b ? bw_p[36:8] : es_p[257 +: 29],                                 // AD
                       es_p[288*hi + 1 +: 256], use_b ? bw_p[292:37] : es_p[288*lo + 1 +: 256], // DB DA
                       epc_p[5*hi +: 5], epc_p[5*lo +: 5], dpc_p[5*hi +: 5],                 // QB QA PB
                       use_b ? bw_p[7:3] : dpc_p[5*lo +: 5],                                 // PA
                       est_p, use_b ? bw_p[2:1] : dst_p, xv, av};                            // EST DST XV AV
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin h <= 784'd0; fault <= 1'b0; end
        else begin
            h <= {use_b, hn};
            if ((ev_now && ph1) || c_bad || (bt_x && MUT != 1)) fault <= 1'b1;
        end
endmodule

module qkd_kv_es_fan_stack_b #(parameter integer MUT = 0) (
    input  wire            ck,
    input  wire            rst_n,
    input  wire [1:0]      stack,         // identity strap: WS 0, WN 1, ES 2, EN 3
    input  wire [783:0]    h,
    output reg  [779:0]    d
);
    localparam integer H_AV = 0, H_XV = 2, H_DST = 4, H_EST = 6, H_PA = 8, H_PB = 13, H_QA = 18, H_QB = 23, H_DA = 28,
                       H_DB = 284, H_AD = 540, H_SV = 569, H_CTX = 570, H_EID = 631, H_EAD = 692, H_SS = 721,
                       H_TOK = 722, H_EP = 740, H_CV = 756, H_CST = 757, H_CPC = 759, H_CRG = 764, H_CVL = 767,
                       H_BV = 783;
    // chain field map: qkd_kv_es_fan_root / qkd_kv_pc_chain_station
    localparam integer F_V = 0, F_PC0 = 2, F_PC1 = 7, F_D0 = 12, F_D1 = 268, F_AD = 524, F_SV = 553, F_CTX = 554,
                       F_EV = 615, F_EPC0 = 617, F_EPC1 = 622, F_EST = 627, F_EID = 629, F_EAD = 690,
                       F_SS = 719, F_TOK = 720, F_EP = 738, F_CV = 754, F_CPC = 755, F_CRG = 760, F_CVL = 763, F_BT = 779,
                       W = 780;
    (* keep *) reg rs_q;
    always @(posedge ck) rs_q <= rst_n;
    wire [1:0] s = (MUT == 1) ? (stack ^ 2'd1) : stack;
    function automatic [W-1:0] head(input [W-1:0] prev, input [783:0] x);
        reg [W-1:0] o; reg [1:0] v, e;
        begin
            o = prev;
            v = x[H_AV +: 2] & {2{x[H_DST +: 2] == s}};
            e = x[H_XV +: 2] & {2{x[H_EST +: 2] == s}};
            o[F_V +: 2] = v; o[F_EV +: 2] = e;
            if (|v) begin
                o[F_PC0 +: 5] = x[H_PA +: 5]; o[F_PC1 +: 5] = x[H_PB +: 5];
                o[F_D0 +: 256] = x[H_DA +: 256]; o[F_D1 +: 256] = x[H_DB +: 256];
                o[F_AD +: 29] = x[H_AD +: 29]; o[F_SV] = x[H_SV]; o[F_CTX +: 61] = x[H_CTX +: 61];
            end
            if (|e) begin
                o[F_EPC0 +: 5] = x[H_QA +: 5]; o[F_EPC1 +: 5] = x[H_QB +: 5]; o[F_EST +: 2] = x[H_EST +: 2];
                o[F_EID +: 61] = x[H_EID +: 61]; o[F_EAD +: 29] = x[H_EAD +: 29];
            end
            o[F_SS] = x[H_SS];
            if (x[H_SS]) begin o[F_TOK +: 18] = x[H_TOK +: 18]; o[F_EP +: 16] = x[H_EP +: 16]; end
            o[F_CV] = x[H_CV] && x[H_CST +: 2] == s;
            if (x[H_CV]) begin o[F_CPC +: 5] = x[H_CPC +: 5]; o[F_CRG +: 3] = x[H_CRG +: 3]; o[F_CVL +: 16] = x[H_CVL +: 16]; end
            // BOOT: the boot word for this stack takes lane 0's pc / data / address fields (lane valids stay 0)
            o[F_BT] = x[H_BV] && x[H_DST +: 2] == s;
            if (o[F_BT]) begin o[F_PC0 +: 5] = x[H_PA +: 5]; o[F_D0 +: 256] = x[H_DA +: 256]; o[F_AD +: 29] = x[H_AD +: 29]; end
            head = o;
        end
    endfunction
    always @(posedge ck or negedge rs_q)
        if (!rs_q) d <= {W{1'b0}};
        else d <= head(d, h);
endmodule

