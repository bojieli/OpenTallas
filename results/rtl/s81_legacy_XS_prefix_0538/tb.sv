`timescale 1ps/1ps
module tb;
reg clk=0;always begin #416 clk=1;#417 clk=0;end
reg rst_n=0,is_v=0;reg[159:0]is_d=0;reg[1103:0]rw=0,re=0;reg[4:0]xv=0,xs=0;reg[1379:0]xd=0;
integer cyc=0,ep=0,ne=0,ct[0:127],rc,fd,tt,fill=-1,wait_n=0,gathers=0,gopulses=0,xwords=0,checks=0;
reg[159:0]cmd[0:127],vv;reg[71:0]gold[0:28671];
initial begin $readmemh("oracle.hex",gold);fd=$fopen("control.txt","r");
 while(!$feof(fd))begin rc=$fscanf(fd,"%d %h\n",tt,vv);if(rc==2)begin ct[ne]=tt;cmd[ne]=vv;ne++;end end $fclose(fd);end
function automatic[1103:0]beat(input integer index,input bit bf);reg[1103:0]v;begin
 v=0;v[0]=1;v[3:1]=bf?3'd2:3'd1;v[8:4]=1;v[12:9]=7;v[19:13]=7'(index);
 if(bf)begin for(integer k=0;k<64;k++)v[21+16*k+:16]=16'h3f00+16'((index+k)&255);end
 else begin for(integer k=0;k<32;k++)begin v[21+8*k+:8]=8'h20+8'(index%32);v[287+8*k+:8]=8'ha0+8'(index%32);end v[277+:10]=127;v[543+:10]=127;end
 beat=v;end endfunction
wire[6418:0]old_o;
wire[6418:0]def_o;
wire[6418:0]equ_o;
wire[6418:0]south_o;
ot_s81sl_xg_gate_ref  refx(.clk(clk),.rst_n(rst_n),.ri_w(rw),.ri_e(re),.vi(276'd0),.xf_v(xv),.xf_s(xs),.xf(xd),.nx_eo(173'd0),.nx_wo(173'd0),.ci_dir(3'd0),.ci_b(1076'd0),.is_v(is_v),.is_d(is_d),.sid(4'd7),.ro_e(old_o[0+:1104]),.ro_w(old_o[1104+:1104]),.vo(old_o[2208+:276]),.nx_wi(old_o[2484+:173]),.nx_ei(old_o[2657+:173]),.dl_ev(old_o[2830+:1]),.dl_e(old_o[2831+:1104]),.dl_wv(old_o[3935+:1]),.dl_w(old_o[3936+:1104]),.dl_vv(old_o[5040+:1]),.dl_vb(old_o[5041+:276]),.xw_d(old_o[5317+:1101]),.fault(old_o[6418+:1]));
ot_s81sl_xg  defx(.clk(clk),.rst_n(rst_n),.ri_w(rw),.ri_e(re),.vi(276'd0),.xf_v(xv),.xf_s(xs),.xf(xd),.nx_eo(173'd0),.nx_wo(173'd0),.ci_dir(3'd0),.ci_b(1076'd0),.is_v(is_v),.is_d(is_d),.sid(4'd7),.ro_e(def_o[0+:1104]),.ro_w(def_o[1104+:1104]),.vo(def_o[2208+:276]),.nx_wi(def_o[2484+:173]),.nx_ei(def_o[2657+:173]),.dl_ev(def_o[2830+:1]),.dl_e(def_o[2831+:1104]),.dl_wv(def_o[3935+:1]),.dl_w(def_o[3936+:1104]),.dl_vv(def_o[5040+:1]),.dl_vb(def_o[5041+:276]),.xw_d(def_o[5317+:1101]),.fault(def_o[6418+:1]));
ot_s81sl_xg #(.INSTANCE("u_s_3N.u_slice.u_xg")) eqx(.clk(clk),.rst_n(rst_n),.ri_w(rw),.ri_e(re),.vi(276'd0),.xf_v(xv),.xf_s(xs),.xf(xd),.nx_eo(173'd0),.nx_wo(173'd0),.ci_dir(3'd0),.ci_b(1076'd0),.is_v(is_v),.is_d(is_d),.sid(4'd7),.ro_e(equ_o[0+:1104]),.ro_w(equ_o[1104+:1104]),.vo(equ_o[2208+:276]),.nx_wi(equ_o[2484+:173]),.nx_ei(equ_o[2657+:173]),.dl_ev(equ_o[2830+:1]),.dl_e(equ_o[2831+:1104]),.dl_wv(equ_o[3935+:1]),.dl_w(equ_o[3936+:1104]),.dl_vv(equ_o[5040+:1]),.dl_vb(equ_o[5041+:276]),.xw_d(equ_o[5317+:1101]),.fault(equ_o[6418+:1]));
ot_s81sl_xg #(.INSTANCE("u_s_3S.u_sl.u_xg")) southx(.clk(clk),.rst_n(rst_n),.ri_w(rw),.ri_e(re),.vi(276'd0),.xf_v(xv),.xf_s(xs),.xf(xd),.nx_eo(173'd0),.nx_wo(173'd0),.ci_dir(3'd0),.ci_b(1076'd0),.is_v(is_v),.is_d(is_d),.sid(4'd6),.ro_e(south_o[0+:1104]),.ro_w(south_o[1104+:1104]),.vo(south_o[2208+:276]),.nx_wi(south_o[2484+:173]),.nx_ei(south_o[2657+:173]),.dl_ev(south_o[2830+:1]),.dl_e(south_o[2831+:1104]),.dl_wv(south_o[3935+:1]),.dl_w(south_o[3936+:1104]),.dl_vv(south_o[5040+:1]),.dl_vb(south_o[5041+:276]),.xw_d(south_o[5317+:1101]),.fault(south_o[6418+:1]));
always@(negedge clk)begin
 is_v=0;is_d=0;rw=0;re=0;xv=0;xs=0;xd=0;
 if(cyc==8)rst_n=1;
 if(ep<ne&&ct[ep]==cyc)begin is_v=1;is_d=cmd[ep];ep++;end
 if(refx.u_s.o_gw&&!refx.u_s.o_gw_fam)begin fill=0;wait_n=8;end
 else if(fill>=0&&fill<40)begin
  if(wait_n>0)wait_n--;else begin rw=beat(fill,0);re=beat(fill+40,0);fill++;end
 end
 if(cyc==900)begin is_v=1;is_d=160'd1<<120|160'd1<<121;end
 if(cyc>=920&&cyc<952)begin
  xv[2]=1;xs[2]=((cyc-920)%4==0);xd[552+:276]=beat((cyc-920)/4,1)>>((cyc-920)%4*276);
 end
end
always@(posedge clk)begin cyc++;#2;
 if(cyc>20)begin
  if(old_o!==def_o||old_o!==equ_o)$fatal(1,"NATIVE_LEGACY_PORT_MISMATCH cycle=%0d",cyc);
  if({refx.u_s.gv_q,refx.u_s.gf_q,refx.u_s.gi_q,refx.u_s.gd_q,refx.u_s.isv_q,refx.u_s.isd_q,refx.u_s.o_go,refx.u_s.o_gw} !== {defx.u_s.gv_q,defx.u_s.gf_q,defx.u_s.gi_q,defx.u_s.gd_q,defx.u_s.isv_q,defx.u_s.isd_q,defx.u_s.o_go,defx.u_s.o_gw})$fatal(1,"LEGACY_CAPTURE_DEFAULT_MISMATCH");
  if({refx.u_s.gv_q,refx.u_s.gf_q,refx.u_s.gi_q,refx.u_s.gd_q,refx.u_s.isv_q,refx.u_s.isd_q,refx.u_s.o_go,refx.u_s.o_gw} !== {eqx.u_s.gv_q,eqx.u_s.gf_q,eqx.u_s.gi_q,eqx.u_s.gd_q,eqx.u_s.isv_q,eqx.u_s.isd_q,eqx.u_s.o_go,eqx.u_s.o_gw})$fatal(1,"LEGACY_CAPTURE_PREFIX_MISMATCH");
  checks++;
 end
 gathers+=refx.g_v[0]+refx.g_v[1]+refx.g_v[2];
 if(refx.u_s.o_go)begin gopulses++;$display("LEGACY_NATIVE_DECODED_GO %0d",cyc);end
 if(old_o[5317])xwords++;
end
integer addr;reg[71:0]nword,sword;
always@(negedge clk)begin #2;
 if(cyc>20)begin addr=(cyc*131)%4096;
if(refx.u_s.u_cal_action.word_read(addr)!==gold[0*4096+addr]||defx.u_s.u_cal_action.word_read(addr)!==gold[0*4096+addr]||eqx.u_s.u_cal_action.word_read(addr)!==gold[0*4096+addr])$fatal(1,"LEGACY_NATIVE_IMAGE_MISMATCH ROM=u_cal_action addr=%0d",addr);
if(southx.u_s.u_cal_action.word_read(addr)!==72'ha8a7a6a5a4a3a2a1a0)$fatal(1,"LEGACY_NATIVE_NAMESPACE_LEAK ROM=u_cal_action");
if(refx.u_s.u_cal_time.word_read(addr)!==gold[1*4096+addr]||defx.u_s.u_cal_time.word_read(addr)!==gold[1*4096+addr]||eqx.u_s.u_cal_time.word_read(addr)!==gold[1*4096+addr])$fatal(1,"LEGACY_NATIVE_IMAGE_MISMATCH ROM=u_cal_time addr=%0d",addr);
if(southx.u_s.u_cal_time.word_read(addr)!==72'ha9a8a7a6a5a4a3a2a1)$fatal(1,"LEGACY_NATIVE_NAMESPACE_LEAK ROM=u_cal_time");
if(refx.u_s.u_phase0.word_read(addr)!==gold[2*4096+addr]||defx.u_s.u_phase0.word_read(addr)!==gold[2*4096+addr]||eqx.u_s.u_phase0.word_read(addr)!==gold[2*4096+addr])$fatal(1,"LEGACY_NATIVE_IMAGE_MISMATCH ROM=u_phase0 addr=%0d",addr);
if(southx.u_s.u_phase0.word_read(addr)!==72'haaa9a8a7a6a5a4a3a2)$fatal(1,"LEGACY_NATIVE_NAMESPACE_LEAK ROM=u_phase0");
if(refx.u_s.u_stream0.word_read(addr)!==gold[3*4096+addr]||defx.u_s.u_stream0.word_read(addr)!==gold[3*4096+addr]||eqx.u_s.u_stream0.word_read(addr)!==gold[3*4096+addr])$fatal(1,"LEGACY_NATIVE_IMAGE_MISMATCH ROM=u_stream0 addr=%0d",addr);
if(southx.u_s.u_stream0.word_read(addr)!==72'habaaa9a8a7a6a5a4a3)$fatal(1,"LEGACY_NATIVE_NAMESPACE_LEAK ROM=u_stream0");
if(refx.u_s.u_stream1.word_read(addr)!==gold[4*4096+addr]||defx.u_s.u_stream1.word_read(addr)!==gold[4*4096+addr]||eqx.u_s.u_stream1.word_read(addr)!==gold[4*4096+addr])$fatal(1,"LEGACY_NATIVE_IMAGE_MISMATCH ROM=u_stream1 addr=%0d",addr);
if(southx.u_s.u_stream1.word_read(addr)!==72'hacabaaa9a8a7a6a5a4)$fatal(1,"LEGACY_NATIVE_NAMESPACE_LEAK ROM=u_stream1");
if(refx.u_s.u_stream2.word_read(addr)!==gold[5*4096+addr]||defx.u_s.u_stream2.word_read(addr)!==gold[5*4096+addr]||eqx.u_s.u_stream2.word_read(addr)!==gold[5*4096+addr])$fatal(1,"LEGACY_NATIVE_IMAGE_MISMATCH ROM=u_stream2 addr=%0d",addr);
if(southx.u_s.u_stream2.word_read(addr)!==72'hadacabaaa9a8a7a6a5)$fatal(1,"LEGACY_NATIVE_NAMESPACE_LEAK ROM=u_stream2");
if(refx.u_s.u_stream3.word_read(addr)!==gold[6*4096+addr]||defx.u_s.u_stream3.word_read(addr)!==gold[6*4096+addr]||eqx.u_s.u_stream3.word_read(addr)!==gold[6*4096+addr])$fatal(1,"LEGACY_NATIVE_IMAGE_MISMATCH ROM=u_stream3 addr=%0d",addr);
if(southx.u_s.u_stream3.word_read(addr)!==72'haeadacabaaa9a8a7a6)$fatal(1,"LEGACY_NATIVE_NAMESPACE_LEAK ROM=u_stream3");
end
 if(cyc==1200)begin
  if(gopulses<1||gathers<88||checks<1000)$fatal(1,"NATIVE_GATE_INSUFFICIENT_ACTIVITY go=%0d gathers=%0d checks=%0d",gopulses,gathers,checks);
  $display("PASS_NATIVE_LEGACY_XG_XS_PREFIX cycles=%0d checks=%0d gathers=%0d go=%0d xwords=%0d fault=%b defaultempty_and_identicalprefix_exact distinct_namespaces2 native_ROMs7 added_capture0",cyc,checks,gathers,gopulses,xwords,old_o[6418]);$finish;
 end
end
endmodule
