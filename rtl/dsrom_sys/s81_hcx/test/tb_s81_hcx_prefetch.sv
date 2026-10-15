`timescale 1ns/1ps
module tb_s81_hcx_prefetch;
 localparam integer RL=4;
 reg clk=0;always #5 clk=~clk;
 reg rn=0,start=0;wire[7:0]rv;wire[111:0]ra;wire sb,sv,cv,f;wire[6:0]sw;wire[4095:0]sd;
 reg[RL-1:0]due=0;reg[6:0]word[0:RL-1];reg[4095:0]data[0:RL-1];integer cycle=0,readgroups=0,stages=0,commands=0;
`ifdef MUT_RETURN
 wire[7:0]rs={8{due[RL-1]}} & ((word[RL-1]==42)?8'hfe:8'hff);
`else
 wire[7:0]rs={8{due[RL-1]}};
`endif
 assign sd=data[RL-1]; // actual payload bypasses metadata controller on die
 ot_s81_hcx_prefetch #(.RL(RL))u(.clk(clk),.rst_n(rn),.start(start),.h_base_row(14'd8192),.rq_v(rv),.rq_row(ra),.rs_v(rs),.stage_begin(sb),.stage_v(sv),.stage_word(sw),.cmd_v(cv),.fault(f));
 always @(posedge clk)begin
  cycle<=cycle+1;due[0]<=rv[0];word[0]<=7'(readgroups);
  for(integer p=0;p<8;p=p+1)data[0][512*p+:512]<={16{32'(8192+readgroups*8+p)}};
  for(integer i=1;i<RL;i=i+1)begin due[i]<=due[i-1];word[i]<=word[i-1];data[i]<=data[i-1];end
  if(rv!=0)begin
   if(rv!=8'hff)$fatal(1,"partial native fetch");
   for(integer p=0;p<8;p=p+1)if(ra[14*p+:14]!==14'(8192+8*readgroups+p))$fatal(1,"bad native row schedule");
   readgroups<=readgroups+1;
  end
  if(sv)begin
   if(sw!==7'(stages))$fatal(1,"wrong SRAM stage address");
   for(integer p=0;p<8;p=p+1)if(sd[512*p+:512]!=={16{32'(8192+stages*8+p)}})$fatal(1,"wrong native row data");
   stages<=stages+1;
  end
  if(cv)commands<=commands+1;
 end
 initial begin
  repeat(3)@(negedge clk);rn=1;start=1;
  @(negedge clk);start=0;
  repeat(95)@(negedge clk);
  if(readgroups!=80||stages!=80||commands!=1||f)$fatal(1,"HCX_PREFETCH FAIL reads%0d stages%0d commands%0d fault%0d",readgroups,stages,commands,f);
  $display("HCX_PREFETCH PASS 640 actual native rows,80 fixed stage beats,one compiled command");$finish;
 end
endmodule
