`timescale 1ns/1ps
`default_nettype none
// Opt-in structural composition. Two private roots, delivered at phi-R; the
// caller must supply coherent same-rate clock edges and reset. No macro view of
// the old monolithic WR can be substituted for either new leaf.
module ot_hgi_qdq_wr_split #(parameter integer LQ=10,OD=64,RQ=16)(
 input wire clk_pay,clk_fin,rst_n,
 input wire m_v,input wire [18:0] m,input wire i_bad,vo,qfault,dfault,
 input wire [511:0] y,output wire [2239:0] wwq,
 input wire [7:0] wwq_cr,wwq_done,
 output wire wg_req,input wire wg_gnt,i_act,
 output wire o_wf,o_fin,o_bad,o_idle,
 output wire pay_bad,fin_bad
);
 wire snapshot_v;wire [63:0] snapshot;wire fin_idle;
 ot_hgi_qdq_wr_pay #(.LQ(LQ),.OD(OD),.RQ(RQ)) u_pay(
 .clk(clk_pay),.rst_n(rst_n),.m_v(m_v),.m(m),.i_bad(i_bad),.vo(vo),.qfault(qfault),.dfault(dfault),.y(y),
 .wwq(wwq),.wwq_cr(wwq_cr),.wg_req(wg_req),.wg_gnt(wg_gnt),.i_act(i_act),
 .o_wf(o_wf),.snapshot_v(snapshot_v),.snapshot(snapshot),.o_bad(pay_bad),.o_idle(o_idle));
 ot_hgi_qdq_wr_fin #(.RQ(RQ)) u_fin(.clk(clk_fin),.rst_n(rst_n),.snapshot_v(snapshot_v),.snapshot(snapshot),
 .wwq_done(wwq_done),.o_fin(o_fin),.o_bad(fin_bad),.o_idle(fin_idle));
 assign o_bad=pay_bad|fin_bad; // wrapper is wires only; physical consumers capture leaf pins separately
endmodule
`default_nettype wire
