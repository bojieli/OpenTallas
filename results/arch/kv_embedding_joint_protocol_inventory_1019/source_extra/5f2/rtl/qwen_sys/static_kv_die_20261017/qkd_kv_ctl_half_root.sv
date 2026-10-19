`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen KV die, KV-PLAN 2026-10-17 (HANDOFF 0cx+4 decision 1): DISTRIBUTED static control.  One control root per die
// half (N: WN + EN, S: WS + ES), each serving its own two stacks, instead of every per-stack word leaving the single
// top-centre control tile (the S stacks' words crossed the full N half: no relay spots left in the N corridors).
// The PV pair column splits every half into its W and E stack and the only W <-> E crossings are the top band and the
// hub gap at the stack seam (a single S root tile fails the relay pass exactly there: its E-stack return train found no
// spot at the hub gap), so each half root is TWO replica-identical tiles, one per stack, on its own side channel:
// the S roots at the stack seam (the S stacks' PC 31 chain ends), the N roots at the top of the N stacks.
//
//   qkd_kv_es_fan_root2  (in the control tile, beside the native writer): the front half of qkd_kv_es_fan_root (same
//                        pin flops, same two-lane serialisation, same boot word decode / fault) that emits ONE
//                        783-b edge word h instead of the four steered 779-b stack chain heads.  h is not steered:
//                        it carries the actual dest_stack / compiled expected_stack, so both half roots read the
//                        same word (one die bus, its short N branch forked at the driver pin).
//   qkd_kv_es_fan_stack  (in each stack root tile): one chain-head register of qkd_kv_es_fan_root:
//                        d <= head(stack, d, h) (stack strap: WS 0, WN 1, ES 2, EN 3).  One register stage (the
//                        root's input lands in the chain-head register).
//
// Exactness: d of the stack root equals qkd_kv_es_fan_root d<stack> delayed by exactly ONE edge (+ the die relay
// stages of h): the head function is copied bit for bit.  tb_qkd_kv_ctl_half_root checks it in lockstep against the
// unchanged qkd_kv_es_fan_root for all four stacks (MUT 1 = bit 0 of the stack compare inverted: caught).  The compiler prices the extra edge: kvjc3_pc_chain.py chain_in(stack) relay[stack] += 1 + relay(h).
// Static: no credit, ready, wait or arbitration.
// ---------------------------------------------------------------------------------------------------------------------
module qkd_kv_es_fan_root2 #(parameter integer MUT = 0) (
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
    output reg  [782:0]    h,
    output reg             fault
);
    // ---- pin flops (identical to qkd_kv_es_fan_root) ----
    (* keep *) reg rs_q;
    always @(posedge ck) rs_q <= rst_n;
    reg [4*288-1:0] es_p; reg [19:0] dpc_p, epc_p; reg [1:0] dst_p, gen_p, est_p, egen_p;
    reg [58:0] id_p, eid_p; reg [28:0] ea_p; reg [17:0] tok_p; reg [15:0] ep_p; reg [7:0] ca_p; reg [63:0] cd_p;
    reg [3:0] ev_p; reg ss_p, cw_p;
    always @(posedge ck) begin
        es_p <= es; dpc_p <= dest_pc; dst_p <= dest_stack; id_p <= identity; gen_p <= generation;
        epc_p <= expected_pc; est_p <= expected_stack; eid_p <= expected_identity; egen_p <= expected_generation;
        ea_p <= expected_address; tok_p <= emb_token; ep_p <= emb_epoch; ca_p <= cfg_addr; cd_p <= cfg_data;
    end
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
    // ---- the edge word (field map: qkd_kv_es_fan_half) ----
    wire [782:0] hn = {cd_p[15:0], ca_p[2:0], ca_p[7:3], cd_p[17:16], c_pc,                 // CVL CRG CPC CST CV
                       ep_p, tok_p, ss_p,                                                    // EP TOK SS
                       ea_p, {eid_p, egen_p}, {id_p, gen_p}, es_p[286], es_p[257 +: 29],     // EAD EID CTX SV AD
                       es_p[288*hi + 1 +: 256], es_p[288*lo + 1 +: 256],                     // DB DA
                       epc_p[5*hi +: 5], epc_p[5*lo +: 5], dpc_p[5*hi +: 5], dpc_p[5*lo +: 5],  // QB QA PB PA
                       est_p, dst_p, xv, av};                                                // EST DST XV AV
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin h <= 783'd0; fault <= 1'b0; end
        else begin
            h <= hn;
            if ((ev_now && ph1) || c_bad) fault <= 1'b1;
        end
endmodule

module qkd_kv_es_fan_stack #(parameter integer MUT = 0) (
    input  wire            ck,
    input  wire            rst_n,
    input  wire [1:0]      stack,         // identity strap: WS 0, WN 1, ES 2, EN 3
    input  wire [782:0]    h,
    output reg  [778:0]    d
);
    localparam integer H_AV = 0, H_XV = 2, H_DST = 4, H_EST = 6, H_PA = 8, H_PB = 13, H_QA = 18, H_QB = 23, H_DA = 28,
                       H_DB = 284, H_AD = 540, H_SV = 569, H_CTX = 570, H_EID = 631, H_EAD = 692, H_SS = 721,
                       H_TOK = 722, H_EP = 740, H_CV = 756, H_CST = 757, H_CPC = 759, H_CRG = 764, H_CVL = 767;
    // chain field map: qkd_kv_es_fan_root / qkd_kv_pc_chain_station
    localparam integer F_V = 0, F_PC0 = 2, F_PC1 = 7, F_D0 = 12, F_D1 = 268, F_AD = 524, F_SV = 553, F_CTX = 554,
                       F_EV = 615, F_EPC0 = 617, F_EPC1 = 622, F_EST = 627, F_EID = 629, F_EAD = 690,
                       F_SS = 719, F_TOK = 720, F_EP = 738, F_CV = 754, F_CPC = 755, F_CRG = 760, F_CVL = 763, W = 779;
    (* keep *) reg rs_q;
    always @(posedge ck) rs_q <= rst_n;
    wire [1:0] s = (MUT == 1) ? (stack ^ 2'd1) : stack;
    function automatic [W-1:0] head(input [W-1:0] prev, input [782:0] x);
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
            head = o;
        end
    endfunction
    always @(posedge ck or negedge rs_q)
        if (!rs_q) d <= {W{1'b0}};
        else d <= head(d, h);
endmodule

// The stack root's pass-through words: one register stage each (resetless data relays, as ot_qkd_rlys): the stack
// fan word from the down word {fan, h}, the fan's group gathers (up to the control tile) and the PC 31 embedding
// return train (up to the embedding tile).  MUT 1 (bench only): the fan word is taken one bit low.
module qkd_kv_stack_relays #(parameter integer HW = 783, FW = 1, GW = 1, RW = 1, MUT = 0) (
    input  wire            ck,
    input  wire [HW+FW-1:0] dn,
    input  wire [GW-1:0]   g_i,
    input  wire [RW-1:0]   r_i,
    output reg  [FW-1:0]   fan,
    output reg  [GW-1:0]   g,
    output reg  [RW-1:0]   r
);
    always @(posedge ck) begin
        fan <= dn[HW - ((MUT == 1) ? 1 : 0) +: FW];
        g <= g_i;
        r <= r_i;
    end
endmodule
