`timescale 1ns/1ps
`default_nettype none
// argmax_m_tp192 (START_REG=1) on the actual compiled ARGMAX stimulus of tb_hgi_coll_argmax_static (5 rounds, G lanes,
// start then lanes from start+2, flush, publish=flush+6): exact winners on the fixed output phase, no fault.  The
// registered start (+1) must leave every output edge and value unchanged; OT_ARGMAX_MUT_START_LATE (+2) must FAIL.
module tb_hgi_coll_argmax_m;
 parameter integer G=192;
 reg clk=0,rst_n=0,start=0,flush=0,publish=0;
 always #0.41665 clk=~clk;
 reg [3:0] iv=0,slot=0;reg [2179:0] data=0;
 wire ov,fault;wire [544:0] oflit;
 integer round=0,checked=0;
 wire [255:0] key;wire [131:0] meta;
 for(genvar l=0;l<4;l=l+1)begin:g
  assign key[l*64+:64]=data[l*545+:64];assign meta[l*33+:33]=data[l*545+512+:33];
 end
 ot_hgi_coll_argmax_m_tp192 u(.clk(clk),.rst_n(rst_n),.start(start),.mode(1'b1),.cfg_g(8'(G)),.cfg_gbase(8'd0),.cfg_rank(8'd3),
  .in_slot(slot),.in_v(iv),.in_key(key),.in_meta(meta),.flush_slot(flush),.publish_slot(publish),
  .out_v(ov),.out_flit(oflit),.fault(fault));
 function automatic [31:0] value(input integer r,input integer src);
  case(r)
   0:value=(src==7 || src==88)?32'h42280000:32'hbf800000;
   1:value=32'h7fc00000+32'(src);
   2:value=src==0?32'h80000000:src==G-1?32'h00000000:32'hbf800000;
   3:value=src==0?32'h7fc00001:(src==7 || src==G-1)?32'h7f800000:32'h3f800000;
   default:value=src==17?32'hbf000000:32'hc0000000;
  endcase
 endfunction
 function automatic [31:0] ident(input integer r,input integer src);
  case(r)
   0:ident=src==7?32'd17:src==88?32'd5:32'(100+src);
   1:ident=32'(1000-src);
   2:ident=src==G-1?32'd7:32'(100+src);
   3:ident=src==7?32'd9:src==G-1?32'd22:32'(src);
   default:ident=32'(200+src);
  endcase
 endfunction
 function automatic [31:0] expected(input integer r);
  case(r)0:expected=5;1:expected=32'(1001-G);2:expected=7;3:expected=9;default:expected=217;endcase
 endfunction
 always @(posedge clk)if(rst_n)begin
  #0.01;
  if(ov!==publish)$fatal(1,"ARGMAX_M fixed output phase mismatch");
  if(ov)begin
   if(oflit!=={1'b1,8'hff,8'd3,16'd0,480'd0,expected(round)})
    $fatal(1,"ARGMAX_M exact winner mismatch round%0d got%0d expected%0d",round,oflit[31:0],expected(round));
   checked=checked+1;
  end
 end
 initial begin
  repeat(4)@(negedge clk);rst_n=1;repeat(2)@(negedge clk);
  for(round=0;round<5;round=round+1)begin
   @(negedge clk);start=1;
   @(negedge clk);start=0;
   for(integer base=0;base<G;base=base+4)begin
    @(negedge clk);iv=4'hf;slot=4'hf;
    for(integer l=0;l<4;l=l+1)data[l*545+:545]={1'b1,8'hff,8'(base+l),16'd0,448'd0,ident(round,base+l),value(round,base+l)};
   end
   @(negedge clk);iv=0;slot=0;flush=1;
   @(negedge clk);flush=0;
   repeat(5)@(negedge clk);publish=1;
   @(negedge clk);publish=0;
   repeat(3)@(negedge clk);
   if(fault)$fatal(1,"ARGMAX_M unexpected protocol fault round%0d",round);
  end
  if(checked!=5)$fatal(1,"ARGMAX_M missing publication %0d",checked);
  $display("ARGMAX_M_TP192 PASS G%0d rounds5 exact5 start_reg1",G);$finish;
 end
endmodule
`default_nettype wire
