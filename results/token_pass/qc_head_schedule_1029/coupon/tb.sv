`timescale 1ns/1ps
module tb;
 reg ck=0;always #0.4165 ck=~ck;
 reg rst_top=0,head_prepare_v=0,p_hev=0,p_hfc=1;
 reg[1:0]head_prepare_user=0,p_hg=2;
 reg[17:0]head_prepare_token=123,head_prepare_position=79;
 reg[15:0]p_he=16;reg[58:0]p_ht=0;
 wire head_descriptor_v;wire[58:0]head_descriptor_tag;wire[1:0]head_descriptor_generation;
 dut native(.*);
 reg[61:0]transport[0:4];integer i;
 always @(posedge ck)begin
  transport[0]<={head_descriptor_v,head_descriptor_tag,head_descriptor_generation};
  for(integer k=1;k<5;k=k+1)transport[k]<=transport[k-1];
 end
 reg send_slot=0;wire tx_v,fault;wire[547:0]tx_record;
 wire[22:0]tx_v_pub;
 qfd_mu_head_context_tx_lctx32 actual_head(
  .ck(ck),.rst_leaf({40{rst_top}}),.source_copies({6{send_slot}}),.tx_v_pub(tx_v_pub),
  .descriptor_v(transport[4][61]),.descriptor_tag(transport[4][60:2]),
  .descriptor_generation(transport[4][1:0]),.send_slot(send_slot),.send_user(2'd0),
  .program_ready(1'b1),.installed_fusedcap(1'b1),.program_epoch(16'h42a1),
  .program_digest(64'hbd510612),.tx_v(tx_v),.tx_record(tx_record),.fault(fault));
 reg outv;reg[547:0]outrec;
 always @(posedge ck)begin outv<=tx_v;outrec<=tx_record;end
 integer cycle,mut=0,mode=0,slot,descriptor;
 initial begin
  if(!$value$plusargs("MUT=%d",mut))mut=0;
  if(!$value$plusargs("MODE=%d",mode))mode=0;
  // Dates are post-edge publication, in the compiler's common origin.
  slot=(mode==1)?23:39;descriptor=(mode==1)?15:31;
  if(mode==2)begin slot=40;descriptor=32;end
  if(mut==1)slot=slot-1;
  repeat(8)@(negedge ck);
  rst_top=1;
  for(cycle=0;cycle<60;cycle=cycle+1)begin
   head_prepare_v=cycle==12||(mode==2&&cycle==29);
   head_prepare_user=(mode==2&&cycle==29)?1:0;
   head_prepare_token=(mode==2&&cycle==29)?124:123;
   p_hev=(mode==1)?1:(cycle>=31&&cycle<=39);
   p_ht={16'd16,6'd0,(mut==2?18'd124:18'd123),13'd79,6'd0};
   send_slot=cycle==slot-1;
   @(posedge ck);#0.001;
   if(head_descriptor_v&&head_descriptor_tag[44:43]==0)begin
    if(cycle!=descriptor)$fatal(1,"descriptor edge got%0d want%0d",cycle,descriptor);
    $display("DESCRIPTOR edge=%0d tag=%h",cycle,head_descriptor_tag);
   end
   if(cycle==slot)begin
    if(outv!==1||fault!==0||outrec[58:0]!=={16'd16,6'd0,18'd123,13'd79,6'd0})
      $fatal(1,"HEAD_RESERVATION_FAIL cycle%0d valid%0b fault%0b",cycle,outv,fault);
    $display("HEAD_RESERVATION_PASS mode=%0d wire_slot=%0d actual_native+5transport+actual_lctx32+output_capture",mode,slot);
   end
   @(negedge ck);
  end
  $finish;
 end
endmodule
