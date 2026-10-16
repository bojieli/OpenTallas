`timescale 1ns/1ps
`default_nettype none
// Native composition harness: the exact physical die's literal624-bit relay
// masters, including their actual reset relay. External unused pad bits are0
// exactly as the v16 source straps. No computed data or memory is modeled.
module ot_hgi_sfu_lg_hbfd_relay #(parameter integer R=23)(
 input wire clk,rst_n,input wire [33:0] c_rq,input wire [561:0] c_wq,
 output wire [513:0] c_rr,output wire [1:0] c_w_done,
 output wire [33:0] l_rq,output wire [561:0] l_wq,
 input wire [513:0] l_rr,input wire [1:0] l_w_done);
 wire [623:0] f[0:R],b[0:R];
 assign f[0]={28'd0,c_wq,c_rq};assign b[0]={108'd0,l_w_done,l_rr};
 for(genvar n=0;n<R;n=n+1)begin:g
  hbfd_rly_624_EW forward(.ck(clk),.rs(rst_n),.i(f[n]),.o(f[n+1]));
  hbfd_rly_624_EW backward(.ck(clk),.rs(rst_n),.i(b[n]),.o(b[n+1]));
 end
 assign l_rq=f[R][33:0];assign l_wq=f[R][595:34];
 assign c_rr=b[R][513:0];assign c_w_done=b[R][515:514];
endmodule
`default_nettype wire
