`timescale 1ns/1ps
`default_nettype none
// Real register storage, finite compiler-scheduled windows. Gray pointer
// observations only diagnose ownership errors; they NEVER select transfer time.
// No payload marker, data-dependent drop/insert, ready or backpressure exists.
// Exact physical clocks/epoch ages and the finite-window capacity proof must be
// supplied by the enclosing compiler. This component is not a physical view.
module ot_hbm_static_word_cdc #(
 parameter integer W=487, AW=4, WORDS=2048, MUT=0
)(
 input wire wclk,rclk,rst_n,
 input wire w_start,w_take,w_last,w_observed_v,
 input wire [W-1:0] w_data,
 input wire r_start,r_take,r_last,
 output reg r_v,output reg [W-1:0] r_data,
 output reg w_fault,output reg r_fault
);
 localparam integer DEPTH=1<<AW;
 localparam integer CW=$clog2(WORDS+1);
 reg [W-1:0] storage[0:DEPTH-1];
 reg [AW:0] wp,rp,wgray,rgray;
 (* async_reg="true" *) reg [AW:0] rg1,rg2,wg1,wg2;
 reg wa,ra;
 reg [CW-1:0] wc,rc;
 function automatic [AW:0] binary(input [AW:0] g);
  integer k;begin binary[AW]=g[AW];for(k=AW-1;k>=0;k=k-1)binary[k]=binary[k+1]^g[k];end
 endfunction
 wire [AW:0] w_fill=wp-binary(rg2);
 wire [AW:0] r_fill=binary(wg2)-rp;
 wire [AW:0] wn=wp+1'b1,rn=rp+1'b1;
 initial if(AW<2 || WORDS<1)$fatal(1,"invalid static CDC size");
 always @(posedge wclk or negedge rst_n)
 if(!rst_n)begin rg1<=0;rg2<=0;end else begin rg1<=rgray;rg2<=rg1;end
 always @(posedge rclk or negedge rst_n)
 if(!rst_n)begin wg1<=0;wg2<=0;end else begin wg1<=wgray;wg2<=wg1;end
 always @(posedge wclk or negedge rst_n)
 if(!rst_n)begin wp<=0;wgray<=0;wa<=0;wc<=0;w_fault<=0;end
 else if(w_start)begin
  wa<=1;wc<=0;
  w_fault<=w_fault|wa|w_take|w_observed_v;
 end else begin
  if(w_observed_v!==w_take)w_fault<=1;
  if(w_take)begin
   if(!wa || w_fill>=DEPTH || (w_last!==(wc==WORDS-1)))w_fault<=1;
   // Execution stays at its reserved edge even on a faulty program.
   if(!(MUT==1 && wc==13))storage[wp[AW-1:0]]<=w_data;
   wp<=wn;wgray<=wn^(wn>>1);wc<=wc+1'b1;
   if(w_last)wa<=0;
  end else if(w_last)w_fault<=1;
 end
 always @(posedge rclk or negedge rst_n)
 if(!rst_n)begin rp<=0;rgray<=0;ra<=0;rc<=0;r_fault<=0;r_v<=0;r_data<=0;end
 else if(r_start)begin
  ra<=1;rc<=0;r_v<=0;r_fault<=r_fault|ra|r_take;
 end else begin
  r_v<=r_take && ra;
  if(r_take)begin
   if(!ra || r_fill==0 || r_fill>DEPTH || (r_last!==(rc==WORDS-1)))r_fault<=1;
   r_data<=storage[rp[AW-1:0]] ^ ((MUT==2)?{{(W-1){1'b0}},1'b1}:{W{1'b0}});
   rp<=rn;rgray<=rn^(rn>>1);rc<=rc+1'b1;
   if(r_last)ra<=0;
  end else if(r_last)r_fault<=1;
 end
endmodule
`default_nettype wire
