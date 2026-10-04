`timescale 1ps/1fs
// One real compiled SRAM/PC. ECC protects mutable response payload and tag.
// Cold reset invalidates pointers, never manufactures a memory receipt.
module ot_hbm_accel_return_fifo(
 input wire clk,por_n,input wire iv,output wire ir,input wire [272:0] id,
 output wire ov,input wire ore,output wire [272:0] od,output wire fault,output wire empty);
 import ot_gpu_w6_secded_pkg::*;
 typedef struct packed {logic[4:0] wp,rp;logic[5:0] count;logic[1:0] phase;logic held;} control_t;
 control_t c,n;reg[71:0] sealed;reg[359:0] captured;wire[511:0] ram_out;
 wire bad=(sealed!=encode64(64'(c)));
 wire fetch=!c.held && c.phase==0 && c.count!=0 && !bad;
 wire put=iv&&ir;
 assign ir=c.count<32&&!bad;
 wire[319:0] unpacked;wire[4:0] ue;
 for(genvar g=0;g<5;g=g+1)begin
  wire[65:0] d=decode64(captured[g*72+:72]);
  assign unpacked[g*64+:64]=d[63:0];assign ue[g]=d[65];
 end
 assign fault=bad||(c.held&&((|ue)||(|unpacked[319:273])));
 assign ov=c.held&&!fault;assign od=unpacked[272:0];
 assign empty=c.count==0&&!c.held&&c.phase==0;
 reg[511:0] write_word;
 always @*begin
  write_word=0;
  for(integer w=0;w<5;w=w+1)write_word[w*72+:72]=encode64(64'(320'(id)>>(w*64)));
  n=c;
  if(put)begin n.wp=c.wp+1'b1;n.count=n.count+1'b1;end
  if(fetch)begin n.rp=c.rp+1'b1;n.count=n.count-1'b1;n.phase=1;end
  else if(c.phase==1)begin n.phase=0;n.held=1;end
  if(ov&&ore)n.held=0;
 end
 ot_sram_1r1w_64x512_m1_r2c2 storage(.clk(clk),.r_ce_in(fetch),.r_addr_in({1'b0,c.rp}),.rd_out(ram_out),
  .w_ce_in(put),.w_addr_in({1'b0,c.wp}),.wd_in(write_word),.w_mask_in({512{1'b1}}),
  .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(18'b0));
 always @(posedge clk or negedge por_n)
  if(!por_n)begin c<='0;sealed<=0;captured<=0;end
  else if(!fault)begin
   c<=n;sealed<=encode64(64'(n));
   if(c.phase==1)captured<=ram_out[359:0];
  end
endmodule
