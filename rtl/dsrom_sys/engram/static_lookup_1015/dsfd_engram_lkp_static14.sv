`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// dsfd_engram_lkp_static14 (S-ENGRAM+NORM 2210): the hardened S81 Engram lookup element, STATIC form.
// ot_s81_engram_lookup_static (14 phase-related 1:1 clock roots: ck core, ck_seed hash primary, ck_hash[5:0] hash
// columns, ck_rows[5:0] row buffers) behind pin registers (owner rule 10-15 19:50):
//   * every input pin is captured by one flop with no logic in front of it (+1 cycle on every input);
//   * every output pin is driven by one flop (+1 cycle on every output);
//   * NO ready, credit or release signal crosses the boundary (owner 10-14 static schedule): the window issues in
//     its compiler slot (win_slot), every HBM request leaves in its fixed slot, responses carry their slot (hr_slot)
//     and must arrive within RETURN_AGE cycles of their request at the ENGINE ports; a missing, late, duplicate or
//     stale atom poisons the fixed return (st_bad / fault), it is never retried or waited for.
// Compiler contract: the external service bound measured at THIS element's pins is RETURN_AGE + 2 (hq pin flop +
// hr pin flop); the row-beat schedule leaves the engine at its fixed offset and reaches the pins one cycle later.
// Replaces the credit wrapper dsfd_engram_lkp_14roots (win_cred / rel / hq_cred / o_cred removed; win_slot / hr_slot
// added).  The HBM side is an off-die boundary: only its declared service bound is used, no on-chip flow control.
// ---------------------------------------------------------------------------------------------------------------------
import ot_hdc_engram_tables_shipped_pkg::*;

module dsfd_engram_lkp_static14 #(
    parameter integer ROWSTRIPE  = 0,
    parameter integer NSLOT      = 8,
    parameter integer SLW        = 3,
    parameter integer RETURN_AGE = 128
) (
    input  wire                  ck,
    input  wire                  ck_seed,
    input  wire [5:0]            ck_hash,
    input  wire [5:0]            ck_rows,
    input  wire                  rst_n,
    input  wire                  cfg_layer,
    input  wire [1:0]            cfg_rank,
    // window (compiler slot)
    input  wire                  win_v,
    input  wire [SLW-1:0]        win_slot,
    input  wire [4*ENG_ID_W-1:0] win_ids,
    // HBM request (fixed slot, no ready)
    output reg                   hq_v,
    output reg  [30:0]           hq_atom,
    output reg  [2:0]            hq_tag,
    // HBM response (push, slot-tagged)
    input  wire                  hr_v,
    input  wire [SLW-1:0]        hr_slot,
    input  wire [2:0]            hr_tag,
    input  wire [3:0]            hr_idx,
    input  wire [255:0]          hr_d,
    // row beats (fixed slots)
    output reg                   o_v,
    output reg  [4:0]            o_col,
    output reg  [2:0]            o_beat,
    output reg  [SLW-1:0]        o_slot,
    output reg  [263:0]          o_d,
    // row status
    output reg                   st_v,
    output reg  [SLW-1:0]        st_slot,
    output reg                   st_bad,
    output reg                   fault
);
    // ---- input pin flops ------------------------------------------------------------
    reg                  wv_q, hrv_q, cl_q;
    reg [1:0]            cr_q;
    reg [SLW-1:0]        ws_q, hrs_q;
    reg [4*ENG_ID_W-1:0] wid_q;
    reg [2:0]            hrt_q;
    reg [3:0]            hri_q;
    reg [255:0]          hrd_q;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin wv_q <= 1'b0; hrv_q <= 1'b0; end
        else begin wv_q <= win_v; hrv_q <= hr_v; end
    always @(posedge ck) begin
        ws_q <= win_slot; wid_q <= win_ids; hrs_q <= hr_slot; hrt_q <= hr_tag; hri_q <= hr_idx; hrd_q <= hr_d;
        cl_q <= cfg_layer; cr_q <= cfg_rank;
    end
    // ---- engine ---------------------------------------------------------------------
    wire        e_hqv, e_ov, e_stv, e_stb, e_fault;
    wire [30:0] e_hqa;
    wire [2:0]  e_hqt;
    wire [4:0]  e_oc;
    wire [2:0]  e_ob;
    wire [SLW-1:0] e_os, e_sts;
    wire [263:0] e_od;
    ot_s81_engram_lookup_static #(.RETURN_AGE(RETURN_AGE), .ROWSTRIPE(ROWSTRIPE), .NR(4), .CPR(6), .NSLOT(NSLOT), .ABW(36),
                                  .PIPE(1)) u_e (
        .clk(ck), .clk_seed(ck_seed), .clk_hash(ck_hash), .clk_rows(ck_rows), .rst_n(rst_n), .cfg_layer(cl_q), .cfg_rank(cr_q),
        .win_valid(wv_q), .win_slot(ws_q), .win_ids(wid_q),
        .hq_valid(e_hqv), .hq_atom(e_hqa), .hq_len(), .hq_tag(e_hqt),
        .hr_valid(hrv_q), .hr_slot(hrs_q), .hr_tag(hrt_q), .hr_idx(hri_q), .hr_data(hrd_q),
        .o_valid(e_ov), .o_col(e_oc), .o_beat(e_ob), .o_slot(e_os), .o_data(e_od),
        .st_valid(e_stv), .st_slot(e_sts), .st_bad(e_stb), .fault(e_fault));
    // ---- output pin flops -----------------------------------------------------------
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin hq_v <= 1'b0; o_v <= 1'b0; st_v <= 1'b0; fault <= 1'b0; end
        else begin hq_v <= e_hqv; o_v <= e_ov; st_v <= e_stv; fault <= e_fault; end
    always @(posedge ck) begin
        hq_atom <= e_hqa; hq_tag <= e_hqt;
        o_col <= e_oc; o_beat <= e_ob; o_slot <= e_os; o_d <= e_od;
        st_slot <= e_sts; st_bad <= e_stb;
    end
endmodule
