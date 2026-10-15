`timescale 1ns/1ps
// Native landing-group successor: the seventeenth request bit carries layer parity, CHECKED against the compiled
// layer context (static schedule: no hold queue); merge queues with registered heads.
module qkd_land_grp_epoch #(parameter integer MUT = 0) (
    input wire ck, rst_n, input wire [2:0] g, input wire [1:0] s,
    input wire [272:0] gw0, gw1, gw2, gw3, output wire gc0, gc1, gc2, gc3,
    input wire [16:0] rq, output wire [1024:0] rs,
    input wire [20:0] lt, input wire [1046:0] kn, input wire fi, output wire fo
);
    qkd_land_grp #(.EPOCH(1), .DQ(128), .RH(1), .MUT(MUT)) u (.*);
endmodule
