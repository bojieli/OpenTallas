`timescale 1ns/1ps
module tb_program_n37_eq;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,begin_image=0,word_v=0,word_desc=0,seal=0,auth_v=0,execution_active=0;
 reg[15:0]image_epoch=0,auth_epoch=0;
 reg[3:0]image_target=0,auth_target=0,dw_count=0;
 reg[10:0]pw_count=0;reg[9:0]word_addr=0;reg[63:0]word_data=0,auth_digest=0;
 wire[3:0]t0,t1;wire[142:0]pr0,pr1;wire ready0,ready1,fault0,fault1,footer_v0,footer_v1;
 wire[63:0]digest0,digest1,footer0,footer1;wire[15:0]epoch0,epoch1;
 qkd_host_program_loader_target #(.MUT(MUT)) u_dut(.ck,.rst_n,.begin_image,.image_epoch,.image_target,.auth_target,.replay_target(t0),.pw_count,.dw_count,.word_v,.word_desc,.word_addr,.word_data,.seal,.auth_v,.auth_epoch,.auth_digest,.execution_active,.pr(pr0),.program_ready(ready0),.fault(fault0),.digest(digest0),.program_epoch(epoch0),.authorized_footer_valid(footer_v0),.authorized_footer(footer0));
 qkd_host_program_loader_target_n36_ref u_ref(.ck,.rst_n,.begin_image,.image_epoch,.image_target,.auth_target,.replay_target(t1),.pw_count,.dw_count,.word_v,.word_desc,.word_addr,.word_data,.seal,.auth_v,.auth_epoch,.auth_digest,.execution_active,.pr(pr1),.program_ready(ready1),.fault(fault1),.digest(digest1),.program_epoch(epoch1),.authorized_footer_valid(footer_v1),.authorized_footer(footer1));
 wire[293:0]actual={t0,pr0,ready0,fault0,digest0,epoch0,footer_v0,footer0};
 wire[293:0]expected={t1,pr1,ready1,fault1,digest1,epoch1,footer_v1,footer1};
 integer cycles=0,images=0,program_seen=0,desc_seen=0,total_program=0,total_desc=0;
 reg scoring=0;
 function automatic[63:0]pattern(input integer a,input integer desc);
  pattern=64'hd731_6a42_98c5_0be1 ^ (64'(a)*64'h7e51_02cd_634b_a905) ^ (64'(image_epoch)<<32) ^ (desc?64'h8452_ab91_2233_6699:64'd0);
 endfunction
 task automatic tick;
  @(posedge ck);#1;cycles=cycles+1;
  if(actual!==expected)begin
   $display("N37_PROGRAM_EQ FAIL cycle=%0d mut=%0d dut_pr=%h ref_pr=%h",cycles,MUT,pr0,pr1);$fatal(1,"cycle-exact outputs differ");
  end
  if(scoring)begin
   if(pr0[74]&&pr0[142])$fatal(1,"N37_PROGRAM_EQ FAIL overlapping output writes");
   if(pr0[74])begin
    if(pr0[73:64]!==10'(program_seen)||pr0[63:0]!==pattern(program_seen,0))$fatal(1,"N37_PROGRAM_EQ FAIL independent program payload");
    program_seen=program_seen+1;total_program=total_program+1;
   end
   if(pr0[142])begin
    if(pr0[141:139]!==3'(desc_seen)||pr0[138:75]!==pattern(desc_seen,1))$fatal(1,"N37_PROGRAM_EQ FAIL independent descriptor payload");
    desc_seen=desc_seen+1;total_desc=total_desc+1;
   end
  end
  @(negedge ck);
 endtask
 task automatic reset_all;
  scoring=0;rst_n=0;begin_image=0;word_v=0;word_desc=0;seal=0;auth_v=0;execution_active=0;
  repeat(3)tick();rst_n=1;repeat(3)tick();
 endtask
 task automatic run_image(input integer target,input integer np,input integer nd);
  reg[63:0]dg;integer limit;
  image_epoch=image_epoch+1;image_target=4'(target);auth_target=4'(target);pw_count=11'(np);dw_count=4'(nd);
  begin_image=1;tick();begin_image=0;
  dg=64'h51484f5354505247 ^ 64'(target);
  for(integer k=0;k<np;k=k+1)begin
   word_v=1;word_desc=0;word_addr=10'(k);word_data=pattern(k,0);
   dg={dg[56:0],dg[63:57]} ^ word_data ^ {53'b0,word_desc,word_addr};tick();
  end
  for(integer k=0;k<nd;k=k+1)begin
   word_v=1;word_desc=1;word_addr=10'(k);word_data=pattern(k,1);
   dg={dg[56:0],dg[63:57]} ^ word_data ^ {53'b0,word_desc,word_addr};tick();
  end
  word_v=0;word_desc=0;seal=1;tick();seal=0;tick();
  if(digest0!==dg)$fatal(1,"N37_PROGRAM_EQ FAIL independent digest");
  auth_v=1;auth_epoch=image_epoch;auth_digest=dg;tick();auth_v=0;
  program_seen=0;desc_seen=0;scoring=1;limit=0;
  while(!ready0&&limit<np+nd+20)begin tick();limit=limit+1;end
  if(!ready0||fault0||program_seen!=np||desc_seen!=nd)$fatal(1,"N37_PROGRAM_EQ FAIL replay coverage");
  if(footer_v0!==((target==0)&&(np==1024)))$fatal(1,"N37_PROGRAM_EQ FAIL footer validity");
  if(footer_v0&&footer0!==pattern(1023,0))$fatal(1,"N37_PROGRAM_EQ FAIL footer data");
  scoring=0;images=images+1;repeat(3)tick();
 endtask
 initial begin
  reset_all();run_image(3,4,0);reset_all();run_image(12,1024,0);
  reset_all();run_image(0,33,3);reset_all();run_image(0,1024,8);
  reset_all();image_target=3;pw_count=4;dw_count=0;begin_image=1;tick();begin_image=0;
  word_v=1;word_addr=0;word_data=pattern(0,0);tick();reset_all();run_image(3,4,0);
  reset_all();image_target=3;pw_count=4;dw_count=0;begin_image=1;tick();begin_image=0;
  word_v=1;word_addr=1;word_data=pattern(1,0);tick();word_v=0;
  if(!fault0)$fatal(1,"N37_PROGRAM_EQ FAIL malformed word not rejected");
  repeat(3)tick();
  $display("N37_PROGRAM_EQ PASS cycles=%0d images=%0d program_writes=%0d descriptor_writes=%0d reset_pending=1 bad_order=1",cycles,images,total_program,total_desc);$finish;
 end
endmodule
