`timescale 1ns/1ps
// Valid-qualified SMJ payload. No reset/hold mux; same producer edge as sm_rv.
// Values while sm_rv=0 are intentionally unconstrained by the stream contract.
module dsdv_svc_smj_payload_n32(input wire clk,input wire[511:0] d,output reg[511:0] q);
always @(posedge clk) q<=d;
endmodule
