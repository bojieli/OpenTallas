`timescale 1ns/1ps
// c6: low masters RDK 3 + TAIL_CAPTURE, high masters RDK 4 (export r[1] one edge early), all RST_RELAY.
// Four unique physical masters; soft wrappers retain exact chronological chunk parameter sets.
module ot_hgi_sfu_ctl75lo(
 input wire clk,rst_n,v,tail_v, input wire [2:0] sfu,
 input wire [74:0] d,tail_d, output wire [74:0] q, output wire vo,coll,busy
);
 ot_hgi_sfu_ctl_chunk #(.W(75),.OFFSET(0),.PIN_CAPTURE(1),.STATUS_REG(2),.RDK(3),.TAIL_CAPTURE(1),.RST_RELAY(1)) u (
 .clk(clk),.rst_n(rst_n),.v(v),.sfu(sfu),.d(d),.tail_d(tail_d),.tail_v(tail_v),.q(q),.vo(vo),.coll(coll),.busy(busy));
endmodule

module ot_hgi_sfu_ctl75hi(
 input wire clk,rst_n,v,tail_v, input wire [2:0] sfu,
 input wire [74:0] d,tail_d, output wire [74:0] q, output wire vo,coll,busy
);
 ot_hgi_sfu_ctl_chunk #(.W(75),.OFFSET(138),.PIN_CAPTURE(1),.STATUS_REG(2),.RDK(4),.RST_RELAY(1)) u (
 .clk(clk),.rst_n(rst_n),.v(v),.sfu(sfu),.d(d),.tail_d(tail_d),.tail_v(tail_v),.q(q),.vo(vo),.coll(coll),.busy(busy));
endmodule

module ot_hgi_sfu_ctl60lo(
 input wire clk,rst_n,v,tail_v, input wire [2:0] sfu,
 input wire [59:0] d,tail_d, output wire [59:0] q, output wire vo,coll,busy
);
 ot_hgi_sfu_ctl_chunk #(.W(60),.OFFSET(0),.PIN_CAPTURE(1),.STATUS_REG(2),.RDK(3),.TAIL_CAPTURE(1),.RST_RELAY(1)) u (
 .clk(clk),.rst_n(rst_n),.v(v),.sfu(sfu),.d(d),.tail_d(tail_d),.tail_v(tail_v),.q(q),.vo(vo),.coll(coll),.busy(busy));
endmodule

module ot_hgi_sfu_ctl60hi(
 input wire clk,rst_n,v,tail_v, input wire [2:0] sfu,
 input wire [59:0] d,tail_d, output wire [59:0] q, output wire vo,coll,busy
);
 ot_hgi_sfu_ctl_chunk #(.W(60),.OFFSET(138),.PIN_CAPTURE(1),.STATUS_REG(2),.RDK(4),.RST_RELAY(1)) u (
 .clk(clk),.rst_n(rst_n),.v(v),.sfu(sfu),.d(d),.tail_d(tail_d),.tail_v(tail_v),.q(q),.vo(vo),.coll(coll),.busy(busy));
endmodule

