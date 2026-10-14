`timescale 1ns/1ps
// Candidate only: no die-slot approval or physical qualification.
// No reset by design: matches delay1 and xrelay. Upstream reset/flush changes data and me_e.
module ot_qfd_vm_face_sn_e0 #(parameter integer MUT=0) (input wire clk, input wire [511:0] d, output reg [511:0] q);
always @(posedge clk) q <= (MUT==1) ? (d ^ 512'h1) : d;
endmodule
module ot_qfd_vm_face_sn_e1 #(parameter integer MUT=0) (input wire clk, input wire me_e, input wire [511:0] d, output reg [511:0] q);
genvar g; generate for(g=0;g<4;g=g+1) begin: g_me
(* keep="true", dont_touch="true" *) reg me_r;
always @(posedge clk) me_r <= me_e;
always @(posedge clk) if ((MUT==2) || ((MUT==3) ? me_e : me_r)) q[g*128 +:128] <= (MUT==1) ? (d[g*128 +:128] ^ 128'h1) : d[g*128 +:128];
end endgenerate
endmodule
module ot_qfd_vm_face_ns_e0 #(parameter integer MUT=0) (input wire clk, input wire [511:0] d, output reg [511:0] q);
always @(posedge clk) q <= (MUT==1) ? (d ^ 512'h1) : d;
endmodule
module ot_qfd_vm_face_ns_e1 #(parameter integer MUT=0) (input wire clk, input wire me_e, input wire [511:0] d, output reg [511:0] q);
genvar g; generate for(g=0;g<4;g=g+1) begin: g_me
(* keep="true", dont_touch="true" *) reg me_r;
always @(posedge clk) me_r <= me_e;
always @(posedge clk) if ((MUT==2) || ((MUT==3) ? me_e : me_r)) q[g*128 +:128] <= (MUT==1) ? (d[g*128 +:128] ^ 128'h1) : d[g*128 +:128];
end endgenerate
endmodule
