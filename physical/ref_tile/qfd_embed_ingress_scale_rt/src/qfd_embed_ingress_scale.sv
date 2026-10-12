`timescale 1ns/1ps
// rr1012 ref_tile re-route: name shell so the exported view's cell is the master the embedding scale parents
// instantiate (qfd_embed_ingress_scale, physical/qwen_embedding_parent/scale/ingress_bb.v).  Body = the closed route's
// RTL, rtl/physical/ot_qwen_embedding_ingress_island.sv at 0e025d03c (unchanged on main), AW=18 as its cfg.
module qfd_embed_ingress_scale(
    input wire clk, rst_n,
    input wire [17:0] address,
    input wire valid, credit,
    output wire [17:0] address_q, address_n,
    output wire valid_q, valid_n, credit_q, credit_n
);
    ot_qwen_embedding_ingress_island #(.AW(18)) u_island(
        .clk(clk), .rst_n(rst_n), .address(address), .valid(valid), .credit(credit),
        .address_q(address_q), .address_n(address_n), .valid_q(valid_q), .valid_n(valid_n),
        .credit_q(credit_q), .credit_n(credit_n));
endmodule
