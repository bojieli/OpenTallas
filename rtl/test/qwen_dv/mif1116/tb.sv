`timescale 1ns/1fs
module tb;
reg ck=0;always #0.4165 ck=~ck;
reg rst=0;reg[115:0]cmd=0;reg wv=0,tv=0;reg[23:0]wa=0,ta=0;reg[511:0]wd=0;reg[1023:0]td=0,pw[0:1];
parameter integer BAD=0;
native_su_component #(.PROBE_MIF(0)) a(.ck(ck),.rst_n(rst),.cmd_i(cmd),.hr_i('0),.rs_s('0),.rs_n('0),.l9_i('0),.st_up_i('0),.st_dn_i('0),.sc_up_i('0),.sc_dn_i('0),.ch_up_i('0),.ch_dn_i('0),.ag_up_i('0),.treq_i('0));
native_su_component #(.PROBE_MIF(1),.PROBE_BAD_REPLY(BAD)) b(.ck(ck),.rst_n(rst),.cmd_i(cmd),.hr_i('0),.rs_s('0),.rs_n('0),.l9_i('0),.st_up_i('0),.st_dn_i('0),.sc_up_i('0),.sc_dn_i('0),.ch_up_i('0),.ch_dn_i('0),.ag_up_i('0),.treq_i('0));
native_su_component #(.PROBE_MIF(1),.PROBE_BAD_REPLY(1)) c(.ck(ck),.rst_n(rst),.cmd_i(cmd),.hr_i('0),.rs_s('0),.rs_n('0),.l9_i('0),.st_up_i('0),.st_dn_i('0),.sc_up_i('0),.sc_dn_i('0),.ch_up_i('0),.ch_dn_i('0),.ag_up_i('0),.treq_i('0));
reg[31:0]gold[0:3][0:255]; integer nc=0,fc=-1,lc=-1,mutants=0,done0=-1,done1=-1;
integer cy=0,op=-1,start=0,k,j,n0=0,n1=0,first0=-1,first1=-1,last0=-1,last1=-1,checks=0;reg[31:0]ex;
always @(negedge ck)begin
 cy=cy+1;
 if(rst&&op>=0)begin
  for(k=0;k<8;k=k+1)begin
   if(a.L_vm_we[k])begin
    gold[op][n0]=a.L_vm_wdata[k*32+:32];
    if(first0<0)first0=cy;last0=cy;n0=n0+1;
    if(op==0 && a.L_vm_wdata[k*32+:32]!==32'h40000000)$fatal(1,"BASE_COPY");
   end
   if(b.L_vm_we[k])begin
    if(n1>=n0||b.L_vm_wdata[k*32+:32]!==gold[op][n1])$fatal(1,"MIF_PAYLOAD");
    if(first1<0)first1=cy;last1=cy;n1=n1+1;
    if(op==0 && b.L_vm_wdata[k*32+:32]!==32'h40000000)$fatal(1,"MIF_COPY");
   end
   if(c.L_vm_we[k])begin if(fc<0)fc=cy;lc=cy;nc=nc+1;end
   if(op==2 && a.L_l_ov[k])begin gold[op][n0]=a.L_l_out[k*32+:32]; if(first0<0)first0=cy;last0=cy;n0=n0+1;end
   if(op==2 && b.L_l_ov[k])begin if(n1>=n0||b.L_l_out[k*32+:32]!==gold[op][n1])$fatal(1,"MIF_SCALAR_PAYLOAD"); if(first1<0)first1=cy;last1=cy;n1=n1+1;end
   if(op==2 && c.L_l_ov[k])begin if(fc<0)fc=cy;lc=cy;nc=nc+1;end
  end
  if(done0<0&&a.su_idle&&n0>0)done0=cy;
  if(done1<0&&b.su_idle&&n1>0)done1=cy;
 end
end
initial begin
 force a.w16_we=wv;force a.w16_addr=wa;force a.w16_data=wd;
 force b.w16_we=wv;force b.w16_addr=wa;force b.w16_data=wd;
 force c.w16_we=wv;force c.w16_addr=wa;force c.w16_data=wd;
 force a.tw_we=tv;force a.tw_kind=2'd3;force a.tw_addr=ta;force a.tw_data=td;
 force b.tw_we=tv;force b.tw_kind=2'd3;force b.tw_addr=ta;force b.tw_data=td;
 force c.tw_we=tv;force c.tw_kind=2'd3;force c.tw_addr=ta;force c.tw_data=td;
 $readmemh("programme.hex",pw);
 repeat(32)@(negedge ck);rst=1;repeat(32)@(negedge ck);
 for(j=0;j<384;j=j+16)begin wv=1;wa=j;for(k=0;k<16;k=k+1)wd[k*32+:32]=(j<128)?32'h40000000:((j<256)?32'h40400000:32'h40800000);@(negedge ck);end
 wv=0;repeat(32)@(negedge ck);
 for(j=0;j<2;j=j+1)begin tv=1;ta=j;td=pw[j];@(negedge ck);end
 tv=0;repeat(32)@(negedge ck);
 for(j=0;j<4;j=j+1)begin
  op=j;nc=0;fc=-1;lc=-1;done0=-1;done1=-1;n0=0;n1=0;first0=-1;first1=-1;last0=-1;last1=-1;start=cy;
  cmd=(116'(j)<<4)|116'd3;@(negedge ck);cmd=0;repeat(500)@(negedge ck);
  $display("AGE op=%0d base_first=%0d mif_first=%0d base_last=%0d mif_last=%0d count0=%0d count1=%0d faults=%b/%b",op,first0-start,first1-start,last0-start,last1-start,n0,n1,a.su_fault,b.su_fault);
  if(first0<0||first1<0||n0!=n1||first1-first0!=2||last1-last0!=2)$fatal(1,"MIF_AGE_PROFILE");
  if(a.su_fault||b.su_fault||a.vm_fault||b.vm_fault)$fatal(1,"NATIVE_FAULT");
  $display("DONE op=%0d base=%0d mif=%0d mutant_first=%0d mutant_last=%0d mutant_count=%0d",op,done0-start,done1-start,fc-start,lc-start,nc);
  if(fc-first0!=2||lc-last0!=2||nc!=n0)mutants=mutants+1;
  checks=checks+n0;op=-1;repeat(32)@(negedge ck);
 end
 if(mutants==0)$fatal(1,"MUTANT_NOT_CAUGHT");
 $display("MIF_MUTANT_CAUGHT operations=%0d",mutants);
 $display("MIF_NATIVE_PROFILE_PASS checks=%0d period833ps alignment3",checks);$finish;
end
endmodule
