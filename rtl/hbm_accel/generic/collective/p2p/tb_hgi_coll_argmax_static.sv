`timescale 1ns/1ps
`default_nettype none
module tb_hgi_coll_argmax_static;
 parameter integer MUT_TIE=0,MUT_SLOT_CHECK=0;
 reg clk=0,rst_n=0,start=0,flush=0,publish=0;
 always #0.41665 clk=~clk;
 reg [3:0] iv=0,slot=0;
 reg [2179:0] data=0;
 wire ov,fault;
 wire [544:0] oflit;
 reg bad=0,bad_src=0;integer round=0,checked=0;
 ot_hgi_coll_argmax_static #(.MUT_TIE(MUT_TIE),.MUT_SLOT_CHECK(MUT_SLOT_CHECK)) u(
  .clk(clk),.rst_n(rst_n),.start(start),.cfg_g(8'd96),.cfg_gbase(8'd0),.cfg_rank(8'd3),
  .in_slot(slot),.in_v(iv),.in_flit(data),.flush_slot(flush),.publish_slot(publish),
  .out_v(ov),.out_flit(oflit),.fault(fault));
 function automatic [31:0] value(input integer r,input integer src);
  case(r)
   0:value=(src==7 || src==88)?32'h42280000:32'hbf800000;
   1:value=32'h7fc00000+32'(src);
   2:value=src==0?32'h80000000:src==95?32'h00000000:32'hbf800000;
   3:value=src==0?32'h7fc00001:(src==7 || src==95)?32'h7f800000:32'h3f800000;
   default:value=src==17?32'hbf000000:32'hc0000000;
  endcase
 endfunction
 function automatic [31:0] ident(input integer r,input integer src);
  case(r)
   0:ident=src==7?32'd17:src==88?32'd5:32'(100+src);
   1:ident=32'(1000-src);
   2:ident=src==95?32'd7:32'(100+src);
   3:ident=src==7?32'd9:src==95?32'd22:32'(src);
   default:ident=32'(200+src);
  endcase
 endfunction
 function automatic [31:0] expected(input integer r);
  case(r)0:expected=5;1:expected=905;2:expected=7;3:expected=9;default:expected=217;endcase
 endfunction
 always @(posedge clk)if(rst_n)begin
  #0.01;
  if(ov!==publish)$fatal(1,"ARGMAX fixed output phase mismatch");
  if(ov)begin
   if(oflit!=={1'b1,8'hff,8'd3,16'd0,480'd0,expected(round)})
    $fatal(1,"ARGMAX exact winner mismatch round%0d got%0d expected%0d",round,oflit[31:0],expected(round));
   checked=checked+1;
  end
 end
 initial begin
  bad=$test$plusargs("BAD_SLOT"); bad_src=$test$plusargs("BAD_SRC");
  repeat(4)@(negedge clk);rst_n=1;
  for(round=0;round<5;round=round+1)begin
   @(negedge clk);start=1;
   @(negedge clk);start=0;
   for(integer base=0;base<96;base=base+4)begin
    @(negedge clk);iv=4'hf;slot=4'hf;
    for(integer l=0;l<4;l=l+1)data[l*545+:545]={1'b1,8'hff,8'(base+l),16'd0,448'd0,ident(round,base+l),value(round,base+l)};
    if(bad && base==4)slot[0]=0;
    if(bad_src && base==4)data[528+:8]=0;
   end
   @(negedge clk);iv=0;slot=0;flush=1;
   @(negedge clk);flush=0;
   repeat(5)@(negedge clk);publish=1;
   @(negedge clk);publish=0;
   repeat(3)@(negedge clk);
   if(!bad && !bad_src && fault)$fatal(1,"ARGMAX unexpected protocol fault");
   if((bad || bad_src) && !fault)$fatal(1,"ARGMAX reservation mismatch escaped checker");
  end
  if(checked!=5)$fatal(1,"ARGMAX missing publication %0d",checked);
  $display("ARGMAX_STATIC PASS G96 rounds5 exact5 flush6 BAD_SLOT=%0d BAD_SRC=%0d",bad,bad_src);$finish;
 end
endmodule
`default_nettype wire
