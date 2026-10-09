`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_wfc_lnk: the WFC's link shim (stream mtp-rom, 2026-10-08; WFC integration binding 4 of 4, "in_* out_*").
//
// The closed WFC (LINK_REG 1) speaks the registered grant protocol of ot_dsrom_mtp_lrx / _ltx on in_* /
// out_* (ready = a grant from a flop; a granted flit arrives two cycles later from the sender's flop).  The die's
// link endpoint (ot_dsrom_link_rt and its hub FIFO) speaks valid / ready.  This shim is the bridge, built from
// the WFC's own pair (the sender half towards the WFC's receiver, the receiver half for the WFC's sender), with
// registered skids on the link side, plus the two MTP / transport duties of stage 0:
//   * a DRAFT flit (type 4, one flit; ot_dsrom_mtp_seq) is diverted to the token store (dw_*) and never reaches
//     the WFC; the next flit is held GUARD cycles so the store entry is written before the WFC can read it;
//   * VM write credits: every non-header flit the WFC receives becomes exactly one vector-memory write, which
//     ot_dsrom_wfc_vmx carries across the 1.2 / 0.9 GHz boundary; a payload flit is forwarded only with a credit
//     (VCRED = the vmx transport capacity), returned by vmx (vc_ret) when the write has left for the VM.
//     Headers (the first flit of a message) need none.
// Cycles: inbound +3 (skid out flop, ltx grant + launch), outbound +3 (lrx pin flop, skid, output flop).
// Mutants: OT_WFCLNK_MUT_DRAFT2WFC (DRAFT flits go to the WFC), OT_WFCLNK_MUT_NOCRED (no VM credit check).
// ---------------------------------------------------------------------------
module ot_dsrom_wfc_lnk #(
    parameter integer FLIT  = 512,
    parameter integer VCRED = 8,
    parameter integer GUARD = 3
) (
    input  wire            clk,
    input  wire            rst_n,
    // die link, inbound (valid / ready)
    input  wire            li_valid,
    output wire            li_ready,
    input  wire [FLIT-1:0] li_data,
    input  wire            li_last,
    // to the WFC in_* (grant protocol; the WFC's in_ready is the grant)
    output wire            wi_valid,
    input  wire            wi_grant,
    output wire [FLIT-1:0] wi_data,
    output wire            wi_last,
    // from the WFC out_* (grant protocol; wo_grant drives the WFC's out_ready)
    input  wire            wo_valid,
    output wire            wo_grant,
    input  wire [FLIT-1:0] wo_data,
    input  wire            wo_last,
    // die link, outbound (valid / ready)
    output wire            lo_valid,
    input  wire            lo_ready,
    output wire [FLIT-1:0] lo_data,
    output wire            lo_last,
    // DRAFT flits to ot_dsrom_wfc_tok
    output reg             dw_v,
    output reg  [FLIT-1:0] dw_d,
    // VM write credit return from ot_dsrom_wfc_vmx
    input  wire            vc_ret,
    output reg             fault
);
    localparam integer HDR_TYPE = 16;
    localparam [3:0] MT_DRAFT = 4'd4;
    localparam integer CB = $clog2(VCRED + 1) + 1;
    reg live;
    always @(posedge clk) live <= rst_n;

    // ---- inbound: 2-entry skid (ready / valid from its count flops)
    wire sk_v; wire [FLIT:0] sk_h;
    reg  hdr;                                      // the head flit is a message header
    wire is_draft = hdr && sk_h[HDR_TYPE +: 4] == MT_DRAFT;
    reg [CB-1:0] cred;
    reg [2:0] gd;
    wire c_ready;                                  // ltx: the WFC's grant, registered
    wire need_c = !hdr;
`ifdef OT_WFCLNK_MUT_NOCRED
    wire c_ok = 1'b1;
`else
    wire c_ok = !need_c || cred != 0;
`endif
`ifdef OT_WFCLNK_MUT_DRAFT2WFC
    wire take_d = 1'b0;
`else
    wire take_d = sk_v && is_draft && gd == 0;
`endif
    wire c_valid = sk_v && !take_d && gd == 0 && c_ok
`ifndef OT_WFCLNK_MUT_DRAFT2WFC
                   && !is_draft
`endif
                   ;
    wire fwd = c_valid && c_ready;
    wire pop = fwd || take_d;
    ot_dsrom_mtp_skid #(.W(FLIT + 1)) u_isk (.clk(clk), .rst_n(live), .in_valid(li_valid), .in_ready(li_ready),
        .in_data({li_last, li_data}), .out_valid(sk_v), .out_ready(pop), .out_data(sk_h));
    always @(posedge clk) begin
        if (!live) begin
            hdr <= 1'b1; cred <= CB'(VCRED); gd <= 0; dw_v <= 1'b0; fault <= 1'b0;
        end else begin
            if (pop) hdr <= sk_h[FLIT];
            dw_v <= take_d; if (take_d) dw_d <= sk_h[FLIT-1:0];
            if (take_d && !sk_h[FLIT]) fault <= 1'b1;            // a DRAFT is one flit
            gd <= take_d ? GUARD[2:0] : (gd != 0) ? gd - 1'b1 : 3'd0;
            cred <= cred - ((fwd && need_c) ? 1'b1 : 1'b0) + (vc_ret ? 1'b1 : 1'b0);
            if (vc_ret && cred == CB'(VCRED)) fault <= 1'b1;
        end
    end
    ot_dsrom_mtp_ltx #(.W(FLIT + 1)) u_tx (.clk(clk), .rst_n(live),
        .c_valid(c_valid), .c_ready(c_ready), .c_data(sk_h),
        .l_valid(wi_valid), .l_ready(wi_grant), .l_data({wi_last, wi_data}));

    // ---- outbound: the WFC's sender into a receive skid with grants, then a 2-entry output skid
    wire o_v, o_rdy; wire [FLIT:0] o_d, od;
    ot_dsrom_mtp_lrx #(.W(FLIT + 1), .D(4)) u_rx (.clk(clk), .rst_n(live),
        .l_valid(wo_valid), .l_ready(wo_grant), .l_data({wo_last, wo_data}),
        .c_valid(o_v), .c_ready(o_rdy), .c_data(o_d));
    ot_dsrom_mtp_skid #(.W(FLIT + 1)) u_osk (.clk(clk), .rst_n(live), .in_valid(o_v), .in_ready(o_rdy),
        .in_data(o_d), .out_valid(lo_valid), .out_ready(lo_ready), .out_data(od));
    assign lo_data = od[FLIT-1:0]; assign lo_last = od[FLIT];
endmodule
