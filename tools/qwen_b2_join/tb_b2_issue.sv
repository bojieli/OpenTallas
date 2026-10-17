`timescale 1ns/1ps
module tb_b2_issue;
parameter integer MUT=0;
reg clk=0,rs=0;always #1 clk=~clk;
reg go=0,tv=0,tl=0,oen=0;reg[17:0]tiles=0;reg[23:0]ts=0;reg[3:0]split=0;
wire start,pay,fault;wire[3:0]cnt,nh;wire[31:0]stride;
qfd_res_train_issue_b2 #(.TRAIN_EDGES(4),.MUT(MUT))dut(.ck(clk),.rst_n(rs),.me_go(go),.me_tiles(tiles),.me_ts(ts),.me_split(split),.me_oen(oen),.tag_v(tv),.tag_last(tl),.train_start(start),.train_count(cnt),.capture_stride(stride),.payload_write(pay),.slot_count(nh),.fault(fault));
integer cycle=0,first_tag=0,expected_nh=0,expected_tiles=0,expected_stride=0,expected_pay=0,starts=0;
always @(negedge clk)begin
 cycle=cycle+1;
 if(start)begin
  if(cycle!=first_tag+4)$fatal(1,"issuer calendar got%0d expected%0d",cycle,first_tag+4);
  if(cnt!=expected_tiles||stride!=expected_stride||pay!=expected_pay||nh!=expected_nh)$fatal(1,"issuer descriptor count%0d stride%0d pay%0d nh%0d",cnt,stride,pay,nh);
  starts=starts+1;
 end
end
task automatic op(input integer sp,n,spacing,wr);
 begin
 expected_nh=(sp==7)?4:(sp==8)?2:(sp==9)?1:(sp==10)?3:1;
 expected_tiles=n;expected_stride=(spacing<8)?8:spacing;expected_pay=wr;
 split=4'(sp);tiles=18'(n);ts=24'(spacing);oen=1'(wr);go=1;
 @(negedge clk);#0.01;go=0;repeat(3)@(negedge clk);#0.01;
 for(integer k=0;k<8*n;k=k+1)begin
  tv=1;tl=1;if(k==0)first_tag=cycle;
  @(negedge clk);#0.01;tv=0;tl=0;
  if(k%8==7)begin repeat(3)@(negedge clk);#0.01;end
 end
 repeat(12)@(negedge clk);#0.01;
 if(fault)$fatal(1,"issuer fault on legal static program");
 end
endtask
initial begin
 repeat(4)@(negedge clk);#0.01;rs=1;repeat(4)@(negedge clk);#0.01;
 op(7,1,256,1);op(8,3,16,1);op(9,1,64,1);op(10,1,8,1);op(11,1,8,1);op(7,8,8,0);
 if(starts!=6)$fatal(1,"missing issuer starts %0d",starts);
 $display("PASS b2 issuer six descriptors split7..11 and64tags");$finish;
end
endmodule
