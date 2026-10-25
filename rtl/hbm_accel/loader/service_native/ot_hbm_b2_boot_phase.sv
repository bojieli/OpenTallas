`timescale 1ns/1ps
`default_nettype none
// A BOOT-only phase broadcast. BOOT_WAIT is generated from the exact plan's
// max_complete_release minus the root delivered-reset release. Configuration
// starts after RX warmup; token/MTP launches never restart the link phases.
// tx_start uses the declared root->hub CTL lanes. Root-local RX delay matches
// the respective lane age, so each TX/RX pair observes START on the same edge.
module ot_hbm_b2_boot_phase #(
 parameter integer BOOT_WAIT=1,NW_AGE=2,NE_AGE=2,MUT=0
)(input wire clk,rst_n,output reg tx_start,
 output wire rx_start_nw,rx_start_ne);
 localparam integer CW=(BOOT_WAIT<2)?1:$clog2(BOOT_WAIT+1);
 reg[CW-1:0]age;reg issued;
 always @(posedge clk)begin
  if(!rst_n)begin age<=0;issued<=0;tx_start<=0;end
  else begin
   tx_start<=0;
   if(!issued)begin
    if(age==CW'(BOOT_WAIT-1-(MUT==1&&BOOT_WAIT>1?1:0)))begin
     tx_start<=1;issued<=(MUT==2?1'b0:1'b1);age<=0;
    end else age<=age+CW'(1);
   end
  end
 end
 wire[NW_AGE:0]nw;wire[NE_AGE:0]ne;
 assign nw[0]=tx_start;assign ne[0]=tx_start;
 genvar j;
 generate for(j=1;j<=NW_AGE;j=j+1)begin:g_nw
  reg q;always @(posedge clk)if(!rst_n)q<=0;else q<=nw[j-1];assign nw[j]=q;
 end
 for(j=1;j<=NE_AGE;j=j+1)begin:g_ne
  reg q;always @(posedge clk)if(!rst_n)q<=0;else q<=ne[j-1];assign ne[j]=q;
 end endgenerate
 assign rx_start_nw=nw[NW_AGE];assign rx_start_ne=ne[NE_AGE];
 initial if(BOOT_WAIT<1||NW_AGE<0||NE_AGE<0)$fatal(1,"boot phase parameters");
endmodule
`default_nettype wire
