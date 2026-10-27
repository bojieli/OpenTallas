`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// qkd_host_native_engine_preg (QK-CORES-6 2026-10-27, owner rule "register every core pin"; opt-in through
// qkd_host_native_qm_debt ENG_PREG = 1, default 0 = unchanged): the KV hub_Wi hard core qkd_hr_ingest_eng with a
// registered boundary.  qkd_host_native_engine is instantiated UNCHANGED; around it:
//   * every input bit is captured by exactly ONE pin flop (qkd_ie_pff, keep): d_v/d_data, in_v/in_data, w_rdy,
//     r_rdy, rd_v/rd_data (+1 cycle each; rd_data stays registered, no dead-pin drop);
//   * d / in (this core is the SINK): a 2-entry skid with bypass behind the pin flops; d_rdy / in_rdy are
//     registered (port flop + private shadow flop for the in-flight accounting).  rdy(t+1) = 1 iff
//     entries_after(t) + rdy(t) <= 1, so a beat accepted at the pin under rdy never overflows; full rate.
//   * w (this core is the SOURCE): ready-latency (credit) form.  w_rdy from the parent means "a write issued 2
//     cycles later fits"; the engine sees the registered w_rdy, its fire is registered to the pins as w_v (a write
//     is TAKEN whenever w_v = 1: no combinational ready at the pin) with w_addr / w_data.
//   * busy / done_v / done_tag / n_sectors / r_v / r_addr: registered (+1).  busy additionally covers the skids,
//     the pin-flop beats and the engine's write / read / done outputs, so the parent's idle checks stay ordered.
// Cycle delta vs the bare engine: every bus +1 (inputs at the pin flop, outputs at the port flop); the w handshake
// becomes ready-latency 2 (parent: qkd_host_native_qm_debt ENG_PREG credit counter).
// ---------------------------------------------------------------------------------------------------------------
(* keep_hierarchy *)
module qkd_ie_pff #(parameter integer W = 1, parameter integer R = 0) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    generate if (R != 0) begin : g_r
        always @(posedge clk or negedge rst_n) if (!rst_n) q <= {W{1'b0}}; else q <= d;
    end else begin : g_n
        always @(posedge clk) q <= d;
    end endgenerate
endmodule

// 2-entry skid with bypass, registered ready (port + shadow flops), behind single-capture pin flops.
module qkd_ie_skid #(parameter integer W = 1) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         pin_v,
    input  wire [W-1:0] pin_d,
    output wire         pin_rdy,
    output wire         e_v,
    output wire [W-1:0] e_d,
    input  wire         e_rdy,
    output wire         occ
);
    wire         v_q, rdy_s;
    wire [W-1:0] d_q;
    reg  [1:0]   cnt;
    reg  [W-1:0] m0, m1;
    (* keep *) qkd_ie_pff #(.W(1), .R(1)) u_vf (.clk(clk), .rst_n(rst_n), .d(pin_v), .q(v_q));
    (* keep *) qkd_ie_pff #(.W(W), .R(0)) u_df (.clk(clk), .rst_n(rst_n), .d(pin_d), .q(d_q));
    reg  rdy_d;                                     // the ready the upstream saw last cycle
`ifdef QKD_IE_SKID_MUT
    wire beat = v_q && rdy_s;  // bench mutant only (must FAIL): ready of the wrong cycle
`else
    wire beat = v_q && rdy_d;                       // a beat the upstream sent under rdy last cycle
`endif
    assign e_v = (cnt != 2'd0) || beat;
    assign e_d = (cnt != 2'd0) ? m0 : d_q;
    wire pop  = e_v && e_rdy;
    wire push = beat && !((cnt == 2'd0) && e_rdy);  // bypass straight into the engine when empty
    wire [1:0] cnt_n = cnt + (push ? 2'd1 : 2'd0) - ((pop && cnt != 2'd0) ? 2'd1 : 2'd0);
    wire rdy_n = ({1'b0, cnt_n} + {2'b0, rdy_s}) <= 3'd1;
    (* keep *) qkd_ie_pff #(.W(1), .R(1)) u_rp (.clk(clk), .rst_n(rst_n), .d(rdy_n), .q(pin_rdy));   // port flop
    (* keep *) qkd_ie_pff #(.W(1), .R(1)) u_rs (.clk(clk), .rst_n(rst_n), .d(rdy_n), .q(rdy_s));     // private shadow
    assign occ = (cnt != 2'd0) || beat;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin cnt <= 2'd0; rdy_d <= 1'b0; end else begin cnt <= cnt_n; rdy_d <= rdy_s; end
    always @(posedge clk) begin
        if (pop && cnt != 2'd0) begin
            m0 <= (cnt == 2'd2) ? m1 : d_q;
            if (cnt == 2'd2 && push) m1 <= d_q;
        end else if (push) begin
            if (cnt == 2'd0) m0 <= d_q; else m1 <= d_q;
        end
    end
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n && push && cnt == 2'd2 && !(pop)) $fatal(1, "qkd_ie_skid overflow");
`endif
endmodule

module qkd_host_native_engine_preg #(
    parameter integer AW = 32, parameter integer HDMAX = 128, parameter integer KVHMAX = 8, parameter integer DQ = 4,
    parameter integer QKV = 1, parameter integer APIPE = 0, parameter integer NATIVE_ROWS = 1,
    parameter integer QPIPE = 2, parameter integer QMUT = 0
) (
    input  wire              clk,
    input  wire [1:0]        clk_bank,
    input  wire              clk_out,
    input  wire              rst_n,
    input  wire              d_v,
    output wire              d_rdy,
    input  wire [255:0]      d_data,
    input  wire              in_v,
    output wire              in_rdy,
    input  wire [511:0]      in_data,
    output wire              w_v,
    input  wire              w_rdy,
    output wire [AW-1:0]     w_addr,
    output wire [255:0]      w_data,
    output wire              r_v,
    input  wire              r_rdy,
    output wire [AW-1:0]     r_addr,
    input  wire              rd_v,
    input  wire [255:0]      rd_data,
    output wire              done_v,
    output wire [7:0]        done_tag,
    output wire              busy,
    output wire [31:0]       n_sectors,
    output wire [31:0]       n_beats
);
    wire          ed_v, ed_rdy, ei_v, ei_rdy, d_occ, i_occ;
    wire [255:0]  ed_d;
    wire [511:0]  ei_d;
    qkd_ie_skid #(.W(256)) u_dsk (.clk(clk), .rst_n(rst_n), .pin_v(d_v), .pin_d(d_data), .pin_rdy(d_rdy),
                                  .e_v(ed_v), .e_d(ed_d), .e_rdy(ed_rdy), .occ(d_occ));
    qkd_ie_skid #(.W(512)) u_isk (.clk(clk), .rst_n(rst_n), .pin_v(in_v), .pin_d(in_data), .pin_rdy(in_rdy),
                                  .e_v(ei_v), .e_d(ei_d), .e_rdy(ei_rdy), .occ(i_occ));
    wire          wr_q, rr_q, rdv_q;
    wire [255:0]  rdd_q;
    (* keep *) qkd_ie_pff #(.W(1), .R(1))   u_wrf (.clk(clk), .rst_n(rst_n), .d(w_rdy), .q(wr_q));
    (* keep *) qkd_ie_pff #(.W(1), .R(1))   u_rrf (.clk(clk), .rst_n(rst_n), .d(r_rdy), .q(rr_q));
    (* keep *) qkd_ie_pff #(.W(1), .R(1))   u_rvf (.clk(clk), .rst_n(rst_n), .d(rd_v), .q(rdv_q));
    (* keep *) qkd_ie_pff #(.W(256), .R(0)) u_rdf (.clk(clk), .rst_n(rst_n), .d(rd_data), .q(rdd_q));
    wire          e_wv, e_rv, e_done, e_busy;
    wire [AW-1:0] e_waddr, e_raddr;
    wire [255:0]  e_wdata;
    wire [7:0]    e_tag;
    wire [31:0]   e_nsec;
    qkd_host_native_engine #(.AW(AW), .HDMAX(HDMAX), .KVHMAX(KVHMAX), .DQ(DQ), .QKV(QKV), .APIPE(APIPE),
                             .NATIVE_ROWS(NATIVE_ROWS), .QPIPE(QPIPE), .QMUT(QMUT)) u_eng (
        .clk(clk), .clk_bank(clk_bank), .clk_out(clk_out), .rst_n(rst_n),
        .d_v(ed_v), .d_rdy(ed_rdy), .d_data(ed_d),
        .in_v(ei_v), .in_rdy(ei_rdy), .in_data(ei_d),
        .w_v(e_wv), .w_rdy(wr_q), .w_addr(e_waddr), .w_data(e_wdata),
        .r_v(e_rv), .r_rdy(rr_q), .r_addr(e_raddr), .rd_v(rdv_q), .rd_data(rdd_q),
        .done_v(e_done), .done_tag(e_tag), .busy(e_busy), .n_sectors(e_nsec), .n_beats(n_beats));
    (* keep *) qkd_ie_pff #(.W(1), .R(1))    u_wvo (.clk(clk), .rst_n(rst_n), .d(e_wv && wr_q), .q(w_v));
    (* keep *) qkd_ie_pff #(.W(AW), .R(0))   u_wao (.clk(clk), .rst_n(rst_n), .d(e_waddr), .q(w_addr));
    (* keep *) qkd_ie_pff #(.W(256), .R(0))  u_wdo (.clk(clk), .rst_n(rst_n), .d(e_wdata), .q(w_data));
    (* keep *) qkd_ie_pff #(.W(1), .R(1))    u_rvo (.clk(clk), .rst_n(rst_n), .d(e_rv), .q(r_v));
    (* keep *) qkd_ie_pff #(.W(AW), .R(0))   u_rao (.clk(clk), .rst_n(rst_n), .d(e_raddr), .q(r_addr));
    (* keep *) qkd_ie_pff #(.W(1), .R(1))    u_dvo (.clk(clk), .rst_n(rst_n), .d(e_done), .q(done_v));
    (* keep *) qkd_ie_pff #(.W(8), .R(1))    u_dto (.clk(clk), .rst_n(rst_n), .d(e_tag), .q(done_tag));
    (* keep *) qkd_ie_pff #(.W(32), .R(1))   u_nso (.clk(clk), .rst_n(rst_n), .d(e_nsec), .q(n_sectors));
    (* keep *) qkd_ie_pff #(.W(1), .R(1))    u_bso (.clk(clk), .rst_n(rst_n),
                                                    .d(e_busy || e_wv || e_rv || e_done || d_occ || i_occ), .q(busy));
endmodule
