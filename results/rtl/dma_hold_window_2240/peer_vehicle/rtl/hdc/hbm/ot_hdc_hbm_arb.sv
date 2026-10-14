`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Two HBM clients on one controller port: the KV streaming engine (A,
// rtl/hdc/kv/ot_hdc_kv_stream.sv) and the weight streaming engine (B,
// rtl/hdc/hbm/ot_hdc_wstream.sv) share the stack(s) of the HBM configuration.
//
// Requests (valid/ready): A has priority -- its fetches gate KV ops whose
// windows are small, and its writes carry the token's new K/V rows; B's stream
// runs ahead of the engine and absorbs the wait.  The combined tag's top bit
// names the client; the controller's ready does not depend on valid, so the
// grant is combinational without a loop.
// Responses: per pseudo-channel, routed to the client its tag names; a
// response port's ready is its client's.  Each pseudo-channel returns in
// order, so a response held by one client blocks the ones behind it (as a
// shared controller queue would).
// ---------------------------------------------------------------------------
module ot_hdc_hbm_arb #(
    parameter integer NPC   = 4,
    parameter integer AW    = 24,        // sector address bits
    parameter integer DW    = 256,       // sector bits
    parameter integer LENW  = 5,
    parameter integer BEATW = 4,
    parameter integer TAGA  = 14,
    parameter integer TAGB  = 12,
    parameter integer TAGW  = 1 + ((TAGA > TAGB) ? TAGA : TAGB)
) (
    // client A (KV): reads and one-sector writes
    input  wire              a_v,
    output wire              a_rdy,
    input  wire              a_we,
    input  wire [AW-1:0]     a_addr,
    input  wire [LENW-1:0]   a_len,
    input  wire [TAGA-1:0]   a_tag,
    input  wire [DW-1:0]     a_wdata,
    output wire [NPC-1:0]    a_hr_v,
    input  wire [NPC-1:0]    a_hr_rdy,
    // client B (weights): reads
    input  wire              b_v,
    output wire              b_rdy,
    input  wire [AW-1:0]     b_addr,
    input  wire [LENW-1:0]   b_len,
    input  wire [TAGB-1:0]   b_tag,
    output wire [NPC-1:0]    b_hr_v,
    input  wire [NPC-1:0]    b_hr_rdy,
    // client tags and beats as the controller returns them
    output wire [NPC*TAGA-1:0] a_hr_tag,
    output wire [NPC*TAGB-1:0] b_hr_tag,
    // controller
    output wire              req_v,
    input  wire              req_rdy,
    output wire              req_we,
    output wire [AW-1:0]     req_addr,
    output wire [LENW-1:0]   req_len,
    output wire [TAGW-1:0]   req_tag,
    output wire [DW-1:0]     req_wdata,
    input  wire [NPC-1:0]    rsp_v,
    output wire [NPC-1:0]    rsp_rdy,
    input  wire [NPC*TAGW-1:0] rsp_tag
);
    wire grant_a = a_v;
    assign req_v = a_v || b_v;
    assign req_we = grant_a ? a_we : 1'b0;
    assign req_addr = grant_a ? a_addr : b_addr;
    assign req_len = grant_a ? a_len : b_len;
    assign req_tag = grant_a ? {1'b0, {(TAGW-1-TAGA){1'b0}}, a_tag} : {1'b1, {(TAGW-1-TAGB){1'b0}}, b_tag};
    assign req_wdata = a_wdata;
    assign a_rdy = req_rdy && grant_a;
    assign b_rdy = req_rdy && !grant_a;
    genvar p;
    generate
        for (p = 0; p < NPC; p = p + 1) begin : g_pc
            wire src_b = rsp_tag[p*TAGW + TAGW - 1];
            assign a_hr_v[p] = rsp_v[p] && !src_b;
            assign b_hr_v[p] = rsp_v[p] && src_b;
            assign rsp_rdy[p] = src_b ? b_hr_rdy[p] : a_hr_rdy[p];
            assign a_hr_tag[p*TAGA +: TAGA] = rsp_tag[p*TAGW +: TAGA];
            assign b_hr_tag[p*TAGB +: TAGB] = rsp_tag[p*TAGW +: TAGB];
        end
    endgenerate
endmodule
