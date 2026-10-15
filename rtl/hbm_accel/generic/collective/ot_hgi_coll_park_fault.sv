// Keep sticky feedback inside the state cell; a distinct publication cell
// owns the external pin at the same edge. Explicit process keep prevents
// merging the two physical registers back into a feedback-loaded pin net.
module ot_hgi_coll_park_fault #(parameter integer N=16)(input wire clk,rst_n,input wire[N-1:0]bank_ovf,output reg ovf);
wire[0:0]rn;
ot_rst_relay #(.REGIONS(1)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rn));
reg sticky;
// Native pin boundary (A4 2026-10-14, native audit of faultpub2paths-7a34d98ba: capture bank_ovf 196-201 ps > 190 with the
// 16-input OR in front of the sticky flop): every bank_ovf pin lands in its own pin flop; the OR reads the pin flops,
// so the station reports one edge later (sticky fault: latency only).
reg [N-1:0] bank_q;
always @(posedge clk or negedge rn[0]) if(!rn[0]) bank_q<='0; else bank_q<=bank_ovf;
wire event_in =
`ifdef MUT_FAULT
1'b0;
`else
|bank_q;
`endif
(* keep = 1 *) always @(posedge clk or negedge rn[0])
 if(!rn[0]) sticky<=1'b0;else sticky<=sticky|event_in;
(* keep = 1 *) always @(posedge clk or negedge rn[0])
 if(!rn[0]) ovf<=1'b0;else ovf<=sticky|event_in;
endmodule
