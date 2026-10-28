`timescale 1ns/1ps
module tb;
reg clk=0;always #0.4165 clk=~clk;
reg rst_n=0;reg[15:0]w_sys_face_host_epoch=0;reg w_sys_face_host_epoch_valid=0,w_sys_face_host_fused_capability=0;reg[1:0]w_sys_face_host_generation=0;reg[58:0]w_sys_face_host_tag=0;
wire p_hev,p_hfc;wire[15:0]p_he;wire[58:0]p_ht;wire[1:0]p_hg;
host_path u(.*);
reg prep=0;reg[17:0]ptoken=0,ppos=0;wire head_descriptor_v;wire[58:0]head_descriptor_tag;wire[1:0]head_descriptor_generation;
dut native_consumer(.ck(clk),.rst_top(rst_n),.head_prepare_v(prep),.head_prepare_user(2'd0),.head_prepare_token(ptoken),.head_prepare_position(ppos),.p_hev(p_hev),.p_hfc(p_hfc),.p_he(p_he),.p_ht(p_ht),.p_hg(p_hg),.head_descriptor_v(head_descriptor_v),.head_descriptor_tag(head_descriptor_tag),.head_descriptor_generation(head_descriptor_generation));
reg[78:0]history[0:63];reg[78:0]actual;integer c,k,checks=0;
initial begin
 repeat(4)@(negedge clk);rst_n=1;
 for(c=0;c<40;c=c+1)begin
  @(posedge clk);#0.001;
  actual={p_hev,p_hfc,p_he,p_ht,p_hg};
  if(c>=3)begin
   checks=checks+1;
   if(actual!==history[c-3])$fatal(1,"HOST_PATH_FAIL source_cycle=%0d consumer_cycle=%0d got=%h want=%h",c-3,c,actual,history[c-3]);
  end
  if(head_descriptor_v!==(c==9||c==19))$fatal(1,"HOST_PATH_FAIL native consumer publication edge=%0d",c);
  if(head_descriptor_v&&{head_descriptor_tag,head_descriptor_generation}!==history[c-4][60:0])$fatal(1,"HOST_PATH_FAIL native tuple lifecycle edge=%0d",c);
  #0.001;
  prep=(c==1||c==11);ptoken=c<10?18'd304:18'd607;ppos=c<10?18'd203:18'd405;
  // This is a source publication AFTER the edge; all five fields change together.
  k=(c>=5&&c<=7)?101:(c>=15&&c<=19)?202:c;
  w_sys_face_host_epoch=16'(k*4+16);w_sys_face_host_epoch_valid=(c>=5&&c<=7)||(c>=15&&c<=19);
  w_sys_face_host_fused_capability=w_sys_face_host_epoch_valid;w_sys_face_host_generation=2'(k);
  w_sys_face_host_tag={w_sys_face_host_epoch,6'd0,18'(k*3+1),13'(k*2+1),6'd0};
  history[c]={w_sys_face_host_epoch_valid,w_sys_face_host_fused_capability,w_sys_face_host_epoch,w_sys_face_host_tag,w_sys_face_host_generation};
 end
 $display("HOST_PATH_PASS checks=%0d transport2_plus_capture1=3 coherent_fields=5 valid_intervals=8..10,18..22 native_descriptor_edges=9,19",checks);$finish;
end
endmodule
