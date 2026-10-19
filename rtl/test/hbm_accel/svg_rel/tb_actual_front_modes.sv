`timescale 1ns/1ps
// Decoder validity and legal mixed mode-only stream, on the selected actual
// frontend. This bench does not instantiate or qualify a GO/transport path.
module tb_actual_front_modes;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[191:0]command=0;reg[63:0]kv_desc=0;reg[1098:0]packet=0;
 reg xw_en=0;reg[6:0]xw_addr=0,xw_grp=0;reg[2047:0]xw_data=0;
 reg[183:0]ql=0,qr=0;wire[42:0]request;wire[3271:0]rl,rr;wire[4137:0]bl,br;
 wire rv;wire[11:0]rrow;wire[255:0]rdata;wire fault,schedule_fault;
 reg descriptor_class_at_command=0,context_valid_at_command=0;wire class_fault;
 integer mode_i,h_i,invalids=0,valids=0,sticky_checks=0,step_i,phase=0;
 ot_hbm_sm_attn_front_static actual_front(.*);
 ot_hbm_svc_command_class_guard #(.ENABLE(1))class_guard(.clk(clk),.app_reset_n(rst_n),
  .assembled_command(command),.descriptor_class_at_command(descriptor_class_at_command),
  .context_valid_at_command(context_valid_at_command),.fault(class_fault));
 function[191:0]word;input[2:0]m;input h,cfg;reg[191:0]w;begin
  w=0;w[191:184]=8'ha2;w[183:181]=m;w[180]=h;w[179]=cfg;
  if(cfg)begin w[178:166]=h?13'd32:13'd8;w[165:153]=m==5||m==7?13'd0:(h?13'd32:13'd8);end
  word=w;
 end endfunction
 function invalid;input integer m,h;begin
  case(8*h+m)3,11,13,15:invalid=1;default:invalid=0;endcase
 end endfunction
 task clear;begin
  @(negedge clk);rst_n=0;command=0;context_valid_at_command=0;
  repeat(8)@(negedge clk);rst_n=1;repeat(16)@(negedge clk);
  if(schedule_fault||fault||class_fault)$fatal(1,"FRONT_MODE_FAIL reset");
 end endtask
 task offer;input[2:0]m;input h,cfg,cls;begin
  @(negedge clk);command=word(m,h,cfg);descriptor_class_at_command=cls;context_valid_at_command=1;
  @(posedge clk);#1;
 end endtask
 task blank;input integer n;input expected_front,expected_guard;begin
  @(negedge clk);command=0;context_valid_at_command=0;
  repeat(n)begin @(posedge clk);#1;
   if(schedule_fault!==expected_front||class_fault!==expected_guard||fault)$fatal(1,"FRONT_MODE_FAIL sticky/idle phase%0d front%0d guard%0d",phase,schedule_fault,class_fault);
   if(expected_front)sticky_checks=sticky_checks+1;
  end
 end endtask
 task mixed;input integer gap;begin
  clear;phase=gap;
  offer(0,0,0,0);if(schedule_fault||class_fault||fault)$fatal(1,"FRONT_MODE_FAIL mixed dense");
  $display("FRONT_LITERAL phase=%0d index=0 command=%048h",phase,command);
  if(gap>0)blank(gap,0,0);
  offer(4,0,0,gap>0);if(schedule_fault||fault||class_fault!==(gap==0))$fatal(1,"FRONT_MODE_FAIL mixed attention");
  $display("FRONT_LITERAL phase=%0d index=1 command=%048h",phase,command);
  if(gap>0)blank(gap,0,0);
  offer(0,0,0,0);if(schedule_fault||fault||class_fault!==(gap==0))$fatal(1,"FRONT_MODE_FAIL mixed finaldense");
  $display("FRONT_LITERAL phase=%0d index=2 command=%048h",phase,command);
  blank(4,0,gap==0);
  $display("FRONT_MIXED_PASS gap=%0d programmes=%0d added_idle=%0d frontend_fault=0 class_fault=%0d",gap,gap>0?3:1,2*gap,class_fault);
 end endtask
 initial begin
  for(h_i=0;h_i<2;h_i=h_i+1)for(mode_i=0;mode_i<8;mode_i=mode_i+1)begin
   clear;phase=100+8*h_i+mode_i;
   offer(3'(mode_i),1'(h_i),mode_i>=4,mode_i>=4);
   if(schedule_fault!==invalid(mode_i,h_i)||fault||class_fault!==(mode_i==3))$fatal(1,"FRONT_MODE_FAIL table mode%0d h128%0d got%0d guard%0d",mode_i,h_i,schedule_fault,class_fault);
   if(mode_i>=4&&!invalid(mode_i,h_i))begin
    if(actual_front.u_converter.qk!==(mode_i<6))$fatal(1,"FRONT_MODE_FAIL QK/PV identity mode%0d",mode_i);
    if(mode_i==7&&actual_front.u_converter.kv4!==1)$fatal(1,"FRONT_MODE_FAIL mode7 PV4 identity");
   end
   blank(12,invalid(mode_i,h_i),mode_i==3);
   if(invalid(mode_i,h_i))invalids=invalids+1;else valids=valids+1;
   $display("FRONT_MODE_PASS mode=%0d h128=%0d configure=%0d sticky_fault=%0d",mode_i,h_i,mode_i>=4,invalid(mode_i,h_i));
  end
  mixed(0);mixed(8);mixed(10);
  $display("ACTUAL_FRONT_MODES_PASS valid=%0d invalid=%0d sticky_checks=%0d",valids,invalids,sticky_checks);
  $finish;
 end
endmodule
