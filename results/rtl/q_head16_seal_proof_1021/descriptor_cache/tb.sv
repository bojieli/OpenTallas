`timescale 1ns/1ps
module tb;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,pw_v=0,pre_v=0;reg[9:0]pw_addr=0,pw_addr_pre=0;reg[63:0]pw_data=0,pre_data=0;
 reg start=0;wire[5:0]stage=7;wire[11:0]start_base=0,start_base_pre=0;
 wire candidate_v=0;wire[11:0]candidate_pc=0;wire[1:0]candidate_unit=0;
 wire available=1,end_ok=1,cp_available=1;
 wire[1:0]iv,ev,cv,act,dn,ready,fault;wire[55:0]cmd[2];wire[11:0]pc[2];wire[1:0]unit_[2];wire[31:0]cy[2];
 always @(posedge clk)begin pw_addr<=pw_addr_pre;pw_v<=pre_v;pw_data<=pre_data;end
 ot_qwen_fixed_issue_seg_pw_ld #(.H16X(2)) old2(.clk,.rst_n,.pw_v,.pw_addr,.pw_data,.pw_addr_pre,.start,.stage,.start_base,.start_base_pre,.candidate_v,.candidate_pc,.candidate_unit,.available,.end_ok,.cp_available,.issue_v(iv[0]),.end_v(ev[0]),.cp_cmd(cmd[0]),.cp_v(cv[0]),.issue_pc(pc[0]),.issue_unit(unit_[0]),.active(act[0]),.done(dn[0]),.cycle(cy[0]),.image_ready(ready[0]),.fault(fault[0]));
 ot_qwen_fixed_issue_seg_pw_ld #(.H16X(3)) new3(.clk,.rst_n,.pw_v,.pw_addr,.pw_data,.pw_addr_pre,.start,.stage,.start_base,.start_base_pre,.candidate_v,.candidate_pc,.candidate_unit,.available,.end_ok,.cp_available,.issue_v(iv[1]),.end_v(ev[1]),.cp_cmd(cmd[1]),.cp_v(cv[1]),.issue_pc(pc[1]),.issue_unit(unit_[1]),.active(act[1]),.done(dn[1]),.cycle(cy[1]),.image_ready(ready[1]),.fault(fault[1]));
 integer edges=0,cases=0;string label_="reset";
 always @(posedge clk)begin #1;edges=edges+1;
  if(rst_n&&({iv[0],ev[0],cv[0],act[0],dn[0],ready[0],fault[0],cmd[0],pc[0],unit_[0],cy[0]}!=={iv[1],ev[1],cv[1],act[1],dn[1],ready[1],fault[1],cmd[1],pc[1],unit_[1],cy[1]}))$fatal(1,"DIFF case=%s edge=%0d ready=%b fault=%b",label_,edges,ready,fault);
 end
 task send(input bit v,input integer a,input reg[63:0]d);
  @(negedge clk);pw_addr_pre=a;pre_data=d;pre_v=v;@(posedge clk);#2;
 endtask
 task reset_();
  @(negedge clk);rst_n=0;pre_v=0;pw_addr_pre=0;pre_data=0;
  repeat(3)@(posedge clk);
  @(negedge clk);rst_n=1;
  send(0,0,0);
 endtask
 function automatic reg[63:0]meta(input integer n);return (64'h43414c53<<32)|(64'd1<<18)|(64'd7<<12)|n;endfunction
 function automatic reg[63:0]gd(input integer n);return(64'h43414c42<<32)|(64'(n)<<24)|128;endfunction
 localparam reg[63:0]SEAL=(64'h58504631<<32)|(7<<6)|(1<<2)|2;
 // mode:0 good;1 badownlast;2 owninactive;3 growunit;4 growlast;5 growinactive;
 //6 duplicate;7 upperpayload;8 missingrow;9 invalidMETA;10 invalidGDESC;11 duplicateMETA.
 task image(input string name_,input bit meta_first,input bit gd_first,input integer n,input integer gn,input integer mode,input bit do_reset);
  reg[63:0]r;integer j;
  label_=name_;if(do_reset)reset_();
  if(mode==8&&old2.rows[7]===0)$fatal(1,"poison row unexpectedly initialized by reset");
  send(1,0,0);
  if(meta_first)send(1,1017,meta(n));
  if(gd_first)send(1,993,gn?gd(gn):0);
  for(j=0;j<8;j=j+1)begin
   r=(j<n)?((j==n-1)?64'h400000000000:0):0;
   if(mode==1&&j==n-1)r=r^(64'd1<<46);
   if(mode==2&&j==7)r=1;
   if(mode==7&&j==0)r=r|(64'd1<<60);
   if((mode==15||mode==18)&&j==7)r=r|(64'd3<<44);
   if((mode==16&&j<3)||(mode==17&&j<4))r=r|(64'd3<<44);
   if(mode==19&&j==7)r=64'd3<<44;
   if(mode==12)r=(64'd1<<46)|j;
   if(!((mode==8||mode==13||mode==15)&&j==7))send(1,976+j,r);
  end
  if(mode==6)send(1,976,64'h400000000000);
  for(j=0;j<8;j=j+1)begin
   r=(j<gn)?((j==gn-1)?64'h400000000000:0):0;
   if(mode==3&&j==0)r=r|(64'd1<<45);
   if(mode==4&&j==gn-1)r=r^(64'd1<<46);
   if(mode==5&&j==7)r=1;
   if(mode==12)r=(64'd1<<46)|(64'd1<<45)|j;
   if(!(mode==14&&j==7))send(1,984+j,r);
  end
  for(j=1019;j<=1021;j=j+1)send(1,j,((mode==15&&j==1019)||mode==16||mode==17)?((64'd1<<49)|1):0);
  send(1,1016,(64'h43414c31<<32)|32);
  if(!(mode>=20&&mode<=22)&&mode!=29)send(1,992,gn?((64'h43414c47<<32)|32):0);
  if(!gd_first||mode==10)begin
   r=mode==10?(gd(gn)|(64'd1<<28)):(gn?gd(gn):0);
   if(mode==27)r=gd(gn)&~64'hfff;
   if(mode==28)r=1;
   send(1,993,r);
  end
  if(!meta_first||mode==9||mode==11)begin
   r=mode==9?meta(9):meta(n);
   if(mode==23)r=r^(64'd1<<63);
   if(mode==24)r=r|(64'd1<<28);
   if(mode==25)r=r&~(64'd1023<<18);
   if(mode==26)r=(r&~(64'd1023<<18))|(64'd61<<18);
   send(1,1017,r);
  end
  if(mode>=20&&mode<=22)send(1,992,((mode==21?64'h43414c46:64'h43414c47)<<32)|(mode==22?0:32));
  if(mode==29)send(1,992,1);
  // No bubble between a final META/GDESC write and the seal: pipeline honors the exact pre-address law.
  if(mode==13)send(1,983,64'h400000000000);
  if(mode==15)send(1,983,64'h400000000000|(64'd3<<44));
  if(mode==14)send(1,991,64'h400000000000);
  send(1,1023,SEAL);send(0,0,0);send(0,0,0);
  if(mode==0||mode==13||mode==14||mode==15||mode==16||mode==20)begin if(ready!==2'b11||fault!==0)$fatal(1,"LEGAL_REJECT %s ready=%b fault=%b",name_,ready,fault);end
  else if(ready!==0||fault!==2'b11)$fatal(1,"INVALID_ACCEPT %s ready=%b fault=%b",name_,ready,fault);
  cases=cases+1;$display("CASE_PASS %s ready=%b fault=%b edge=%0d",name_,ready,fault,edges);
 endtask
 initial begin
  image("legal_gstop_final_immediate_seal",1,1,2,2,20,1);
  image("legal_meta_gdesc_before",1,1,1,2,0,1);
  image("legal_reload_rows_retained_meta_after",0,0,3,3,0,0);
  image("legal_full8_meta_before_gdesc_after",1,0,8,8,0,1);
  image("legal_gabsent_meta_after",0,1,1,0,0,1);
  image("bad_own_last",1,1,2,2,1,1);
  image("bad_own_inactive",1,1,2,2,2,1);
  image("bad_grow_unit",0,0,2,2,3,1);
  image("bad_grow_last",1,0,2,2,4,1);
  image("bad_grow_inactive",0,1,2,2,5,1);
  image("bad_duplicate_row",0,0,1,1,6,1);
  image("bad_upper_payload",1,1,1,1,7,1);
  image("bad_poison_all_rows",0,0,1,1,12,1);
  image("bad_missing_row_after_reset_retains_poison",0,0,1,1,8,1);
  image("bad_meta_count",0,0,1,1,9,1);
  image("bad_gdesc_reserved",0,0,1,1,10,1);
  image("bad_duplicate_meta_after_rows",1,1,1,1,11,1);
  image("legal_own_row_final_before_seal",1,1,8,2,13,1);
  image("legal_grow_final_before_seal",1,1,2,8,14,1);
  image("legal_recovery_reset_reload",0,0,2,2,0,1);
  image("legal_copy_final_row_immediate_seal",1,1,8,2,15,1);
  image("legal_three_copy_rows",0,0,3,2,16,1);
  image("bad_four_copy_rows",1,1,4,2,17,1);
  image("bad_copy_descriptor_missing",1,1,8,2,18,1);
  image("bad_copy_row_outside_count",1,1,2,2,19,1);
  image("bad_gstop_magic_late_seal",1,1,2,2,21,1);
  image("bad_gstop_zero_stop_late_seal",1,1,2,2,22,1);
  image("bad_meta_magic_late_seal",0,1,2,2,23,1);
  image("bad_meta_reserved_late_seal",0,1,2,2,24,1);
  image("bad_meta_zero_shape_late_seal",0,1,2,2,25,1);
  image("bad_meta_shape61_late_seal",0,1,2,2,26,1);
  image("bad_gdesc_zero_base_late_seal",1,0,2,2,27,1);
  image("bad_gdesc_absent_nonzero_late_seal",1,0,2,0,28,1);
  image("bad_gstop_absent_nonzero_late_seal",1,1,2,0,29,1);
  $display("H16_SEAL_PASS cases=%0d edges=%0d old=2 new=3",cases,edges);$finish;
 end
endmodule
