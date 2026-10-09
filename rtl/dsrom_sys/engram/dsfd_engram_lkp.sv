`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// dsfd_engram_lkp: the hardened Engram lookup element of the S81 layer1e die
// (eng_SE, in the svc_SE slot next to ctrl_SE).  ot_dsrom_engram_lookup behind
// a safe-by-construction boundary (REDESIGN_RULES templates D / credits):
//   * every input pin is captured by a flop with no logic in front of it;
//   * every output pin is driven by a flop;
//   * no same-cycle ready crosses the boundary: the window input, the HBM
//     request port and the row-beat output are CREDIT interfaces.
//       win:  the sender holds WIN_CRED credits; win_cred pulses when an entry
//             of the 2-entry input FIFO is taken by the engine.
//       hq:   this element holds HQ_CRED credits (the controller's request
//             queue depth); hq_cred pulses when the controller frees an entry.
//       o:    this element holds O_CRED credits (the collective's ingress
//             depth); o_cred pulses when the collective frees an entry.
//   * hr (HBM responses) is a pure push port: the engine's row buffers are
//     reserved before a request is issued, so it never back-pressures.
// Cost: +1 cycle on the window, +1 on the responses, +1 on requests and beats
// (the pin flops), credit round trips sized so that they never limit the
// engine's one-row-in-flight rate.
// ---------------------------------------------------------------------------
import ot_hdc_engram_tables_shipped_pkg::*;

module dsfd_engram_lkp #(
    parameter integer PIPE    = 0,
    parameter integer NSLOT   = 8,
    parameter integer HQ_CRED = 8,
    parameter integer O_CRED  = 16,
    parameter integer SLW     = 3
) (
    input  wire                  ck,
    input  wire                  rst_n,
    input  wire                  cfg_layer,
    input  wire [1:0]            cfg_rank,
    // window (credit)
    input  wire                  win_v,
    input  wire [4*ENG_ID_W-1:0] win_ids,
    output reg                   win_cred,
    input  wire [3:0]            rel,
    // HBM request (credit)
    output reg                   hq_v,
    output reg  [30:0]           hq_atom,
    output reg  [2:0]            hq_tag,
    input  wire                  hq_cred,
    // HBM response (push)
    input  wire                  hr_v,
    input  wire [2:0]            hr_tag,
    input  wire [3:0]            hr_idx,
    input  wire [255:0]          hr_d,
    // row beats (credit)
    output reg                   o_v,
    output reg  [4:0]            o_col,
    output reg  [2:0]            o_beat,
    output reg  [SLW-1:0]        o_slot,
    output reg  [263:0]          o_d,
    input  wire                  o_cred,
    // row status
    output reg                   st_v,
    output reg  [SLW-1:0]        st_slot,
    output reg                   st_bad,
    output reg                   fault
);
    // ---- input pin flops ------------------------------------------------------------
    reg                  wv_q, hqc_q, hrv_q, oc_q, cl_q;
    reg [1:0]            cr_q;
    reg [4*ENG_ID_W-1:0] wid_q;
    reg [3:0]            rel_q;
    reg [2:0]            hrt_q;
    reg [3:0]            hri_q;
    reg [255:0]          hrd_q;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            wv_q <= 1'b0; hqc_q <= 1'b0; hrv_q <= 1'b0; oc_q <= 1'b0; rel_q <= 4'd0;
        end else begin
            wv_q <= win_v; hqc_q <= hq_cred; hrv_q <= hr_v; oc_q <= o_cred; rel_q <= rel;
        end
    end
    always @(posedge ck) begin
        wid_q <= win_ids; hrt_q <= hr_tag; hri_q <= hr_idx; hrd_q <= hr_d; cl_q <= cfg_layer; cr_q <= cfg_rank;
    end

    // ---- window FIFO (2 entries) ----------------------------------------------------
    reg [4*ENG_ID_W-1:0] wf [0:1];
    reg       wh, wt;
    reg [1:0] wn;
    wire      e_wrdy;
    wire      w_take = (wn != 2'd0) && e_wrdy;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin wh <= 1'b0; wt <= 1'b0; wn <= 2'd0; win_cred <= 1'b0; end
        else begin
            if (wv_q) wt <= ~wt;
            if (w_take) wh <= ~wh;
            wn <= wn + wv_q - w_take;
            win_cred <= w_take;
        end
    end
    always @(posedge ck) if (wv_q) wf[wt] <= wid_q;

    // ---- engine ---------------------------------------------------------------------
    reg  [7:0] hq_n, o_n;                    // credits held
    wire       e_hqv, e_ov, e_stv, e_stb, e_fault;
    wire [30:0] e_hqa;
    wire [2:0] e_hqt;
    wire [4:0] e_oc;
    wire [2:0] e_ob;
    wire [SLW-1:0] e_os, e_sts;
    wire [263:0] e_od;
    // the engine's request / beat registers hold until "ready": ready = a credit is held and the
    // previous transfer has left (one transfer a cycle at most, every credit counted before it is spent)
    wire e_hqr = (hq_n != 8'd0);
    wire e_or  = (o_n != 8'd0);
    ot_dsrom_engram_lookup #(.NR(4), .CPR(6), .NSLOT(NSLOT), .ABW(36), .PIPE(PIPE)) u_e (
        .clk(ck), .rst_n(rst_n), .cfg_layer(cl_q), .cfg_rank(cr_q),
        .win_valid(wn != 2'd0), .win_ready(e_wrdy), .win_ids(wf[wh]), .rel_valid(rel_q),
        .hq_valid(e_hqv), .hq_ready(e_hqr), .hq_atom(e_hqa), .hq_len(), .hq_tag(e_hqt),
        .hr_valid(hrv_q), .hr_ready(), .hr_tag(hrt_q), .hr_idx(hri_q), .hr_data(hrd_q),
        .o_valid(e_ov), .o_ready(e_or), .o_col(e_oc), .o_beat(e_ob), .o_slot(e_os), .o_data(e_od),
        .st_valid(e_stv), .st_slot(e_sts), .st_bad(e_stb), .fault(e_fault));
    wire hq_fire = e_hqv && e_hqr;
    wire o_fire  = e_ov && e_or;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            hq_n <= HQ_CRED[7:0]; o_n <= O_CRED[7:0]; hq_v <= 1'b0; o_v <= 1'b0; st_v <= 1'b0; fault <= 1'b0;
        end else begin
            hq_n <= hq_n - hq_fire + hqc_q;
            o_n  <= o_n - o_fire + oc_q;
            hq_v <= hq_fire;
            o_v  <= o_fire;
            st_v <= e_stv;
            fault <= e_fault;
        end
    end
    always @(posedge ck) begin
        if (hq_fire) begin hq_atom <= e_hqa; hq_tag <= e_hqt; end
        if (o_fire) begin o_col <= e_oc; o_beat <= e_ob; o_slot <= e_os; o_d <= e_od; end
        if (e_stv) begin st_slot <= e_sts; st_bad <= e_stb; end
    end
endmodule
