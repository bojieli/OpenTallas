`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen KV die, KVJ-C3 2026-10-17 (kv_static_join_plan.md item 6 + 7; kvint gap list 768 + 897 ports): the ROOT of the
// four per-stack static PC chains, 1 per die, beside the native writer (qkd_kv_static_writer_native) and the d2d KV end.
//
// One registered neighbour chain per HBM stack runs from this root down the stack's PC strip (root -> PC slot 31 ->
// 30 -> ... -> 0); every PC parent (qkd_static_kv_pc_path_fan) holds one chain station (qkd_kv_pc_chain_station) that
// registers the chain once per hop (one edge per hop, hop <= the 378 um strip pitch) and taps it for its own PC.
// No star: the root is a 4-way tree node, each stack a neighbour stream.  The chain carries, on fixed fields:
//   (a) the writer's lane -> PC words, two lanes per edge: lanes 0/1 on the edge after the writer's high-half slot,
//       lanes 2/3 one edge later (the writer holds es / dest / expected between high slots, which are >= 2 edges
//       apart: two high slots on consecutive edges latch fault).  Actual words are steered by the writer's ACTUAL
//       dest_stack / dest_pc, the independent expected descriptor by the COMPILED expected_stack / expected_pc, so
//       the PC controller's native intake check still compares two independent sources;
//   (b) the token run start (d2d kind-15 RESULT: engine_result_v / token / TAG59 epoch) for the per-PC embedding slot
//       players;
//   (c) the boot stream of the players' calendar constants (one 16-b word per edge, addressed {stack, pc, reg}).
// Static: no credit, ready, wait or arbitration.  Every functional input lands on a pin flop (+1), every chain output
// is a register (+1).  Ages (all compiler-priced, tools/qwen_kv_die/kvjc3_pc_chain.py): writer output edge w ->
// station input of PC slot s at w + 2 + R[stack] + (31 - s) (lanes 2/3: + 1).
// Boot word (shared boot bus with qkd_embedding_static_join4_cal): cfg_data[63:62] = target (0 = PC player constant,
// 1 = join beat calendar, here ignored); target 0: cfg_addr = {pc[4:0], reg[2:0]}, cfg_data[17:16] = stack,
// cfg_data[15:0] = value, cfg_data[61:18] must be 0.  Targets 2/3 or a non-zero reserved field latch fault.
// Fault (sticky): consecutive writer events; malformed boot word.  MUT (bench only): 2 = lanes 2/3 never sent.
// ---------------------------------------------------------------------------------------------------------------------
module qkd_kv_es_fan_root #(parameter integer MUT = 0) (
    input  wire            ck,
    input  wire            rst_n,
    // native writer face (qkd_kv_static_writer_native outputs)
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
    // token run start (d2d kind-15 RESULT)
    input  wire            emb_start,
    input  wire [17:0]     emb_token,
    input  wire [15:0]     emb_epoch,
    // boot calendar stream
    input  wire            cfg_we,
    input  wire [7:0]      cfg_addr,
    input  wire [63:0]     cfg_data,
    // the four stack chains (WS, WN, ES, EN)
    output reg  [778:0]    d0,
    output reg  [778:0]    d1,
    output reg  [778:0]    d2,
    output reg  [778:0]    d3,
    output reg             fault
);
    // ---- chain field map (LSB first; identical in qkd_kv_pc_chain_station) ----
    localparam integer F_V = 0, F_PC0 = 2, F_PC1 = 7, F_D0 = 12, F_D1 = 268, F_AD = 524, F_SV = 553, F_CTX = 554,
                       F_EV = 615, F_EPC0 = 617, F_EPC1 = 622, F_EST = 627, F_EID = 629, F_EAD = 690,
                       F_SS = 719, F_TOK = 720, F_EP = 738, F_CV = 754, F_CPC = 755, F_CRG = 760, F_CVL = 763, W = 779;
    // ---- pin flops ----
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
    // ---- two-lane serialisation: event edge -> lanes 0/1, next edge -> lanes 2/3 (held writer registers) ----
    wire ev_now = (|ev_p) | (|wv_p);
    reg  ph1; reg [1:0] wv23, ev23;
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin ph1 <= 1'b0; wv23 <= 2'd0; ev23 <= 2'd0; end
        else begin ph1 <= ev_now && MUT != 2; wv23 <= wv_p[3:2]; ev23 <= ev_p[3:2]; end
    wire [1:0]   av = ph1 ? wv23 : wv_p[1:0];
    wire [1:0]   xv = ph1 ? ev23 : ev_p[1:0];
    wire [1:0]   lo = ph1 ? 2'd2 : 2'd0;           // the edge's lane pair {lo, hi}
    wire [1:0]   hi = lo | 2'd1;
    wire [255:0] da = es_p[288*lo + 1 +: 256], db = es_p[288*hi + 1 +: 256];
    wire [4:0]   pa = dpc_p[5*lo +: 5], pb = dpc_p[5*hi +: 5];
    wire [4:0]   qa = epc_p[5*lo +: 5], qb = epc_p[5*hi +: 5];
    // ---- boot word ----
    wire c_pc = cw_p && cd_p[63:62] == 2'd0;
    wire c_bad = cw_p && (cd_p[63] || (cd_p[63:62] == 2'd0 && cd_p[61:18] != 44'd0));
    // ---- the four chain heads ----
    function automatic [W-1:0] head(input [1:0] s, input [W-1:0] prev);
        reg [W-1:0] h; reg [1:0] v, e;
        begin
            h = prev;
            v = av & {2{dst_p == s}};
            e = xv & {2{est_p == s}};
            h[F_V +: 2] = v; h[F_EV +: 2] = e;
            if (|v) begin
                h[F_PC0 +: 5] = pa; h[F_PC1 +: 5] = pb; h[F_D0 +: 256] = da; h[F_D1 +: 256] = db;
                h[F_AD +: 29] = es_p[257 +: 29]; h[F_SV] = es_p[286]; h[F_CTX +: 61] = {id_p, gen_p};
            end
            if (|e) begin
                h[F_EPC0 +: 5] = qa; h[F_EPC1 +: 5] = qb; h[F_EST +: 2] = est_p;
                h[F_EID +: 61] = {eid_p, egen_p}; h[F_EAD +: 29] = ea_p;
            end
            h[F_SS] = ss_p;
            if (ss_p) begin h[F_TOK +: 18] = tok_p; h[F_EP +: 16] = ep_p; end
            h[F_CV] = c_pc && cd_p[17:16] == s;
            if (c_pc) begin h[F_CPC +: 5] = ca_p[7:3]; h[F_CRG +: 3] = ca_p[2:0]; h[F_CVL +: 16] = cd_p[15:0]; end
            head = h;
        end
    endfunction
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin d0 <= {W{1'b0}}; d1 <= {W{1'b0}}; d2 <= {W{1'b0}}; d3 <= {W{1'b0}}; fault <= 1'b0; end
        else begin
            d0 <= head(2'd0, d0); d1 <= head(2'd1, d1); d2 <= head(2'd2, d2); d3 <= head(2'd3, d3);
            if ((ev_now && ph1) || c_bad) fault <= 1'b1;
        end
endmodule
