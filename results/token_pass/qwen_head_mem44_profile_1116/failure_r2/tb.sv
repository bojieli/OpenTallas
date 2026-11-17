`timescale 1ns/1fs
module tb;
localparam integer NCASE=16;
reg ck=0;always #0.4165 ck=~ck;
reg rst_n=0;reg[115:0]cmd=0;reg w16=0,w1=0,tw=0;reg[23:0]w16a=0,w1a=0,twa=0;
reg[511:0]w16d=0;reg[31:0]w1d=0;reg[1023:0]twd=0;reg[1:0]twk=0;reg[2:0]logical_head=0;reg bad_reply=0;
integer csid[0:NCASE-1],cuser[0:NCASE-1],chead[0:NCASE-1],cn[0:NCASE-1],cdso[0:NCASE-1],cxbase[0:NCASE-1],crstd[0:NCASE-1],cpidx[0:NCASE-1],cdbase[0:NCASE-1];
reg[1023:0]progs[0:NCASE-1],gainrows[0:NCASE*24-1],sfu_program[0:1];reg[31:0]gold[0:NCASE*384-1],sfu_gold[0:511];
integer cid=0,user_id=0,sid=0,n=0,dso=0,active=0,mode=0,op=0,cy=0,issue=-1,origin=0;
integer count=0,beats=0,retires=0,first_req=-1,first_bound=-1,first_gain_read=-1,first_operand=-1,first_pin_write=-1,last_pin_write=-1,first_write=-1,last_write=-1,first_retire=-1,last_retire=-1,first_BF16=-1,last_BF16=-1,first_ready=-1,first_gain_store=-1,last_gain_store=-1,programme_store=-1,first_emit=-1;
integer rowidx,colidx,outidx,j,k,t,err=0,total=0,totalbeats=0,expected_count=0;reg[383:0]seen;reg[63:0]beatseen;
integer sfu_outidx;
native_su_component #(.PROBE_MIF(1)) dut(.ck(ck),.rst_n(rst_n),.cmd_i(cmd),.hr_i('0),.rs_s('0),.rs_n('0),.l9_i('0),.st_up_i('0),.st_dn_i('0),.sc_up_i('0),.sc_dn_i('0),.ch_up_i('0),.ch_dn_i('0),.ag_up_i('0),.treq_i('0),
 .preload16_we(w16),.preload16_addr(w16a),.preload16_data(w16d),.preload1_we(w1),.preload1_addr(w1a),.preload1_data(w1d),.install_we(tw),.install_kind(twk),.install_addr(twa),.install_data(twd),.logical_head(logical_head),.bad_reply(bad_reply));
// Complete production pack cohort: one actual private HEAD result and seven
// explicitly software-golden companion producers. No companion HEAD arithmetic.
reg[191:0]pack_addr;reg[255:0]pack_data;wire[7:0]pack_we=(active&&mode==0&&dut.L_vm_we[0])?8'hff:8'd0;
integer pp,pa,rr,cc,gi;
always @*begin
 pack_addr=0;pack_data=0;
 pa=(dut.L_vm_waddr[23:0]&24'h3fffff)-logical_head;
 rr=dso>0?pa/dso:0;cc=dso>0?pa%dso:0;
 for(integer p=0;p<8;p=p+1)begin
  pack_addr[24*p+:24]=24'(pa+p);
  gi=rr*128+cc+p;
  if(gi>=0&&gi<384)pack_data[32*p+:32]=gold[cid*384+gi];
  if(p==logical_head)pack_data[32*p+:32]=dut.L_vm_wdata[31:0];
 end
end
wire srst; qfd_dv_s5_rst2 u_sr(.ck(ck),.rst_n(rst_n),.rst(srst));
reg cfg=0;wire[1087:0]oe,ow;wire xv,xbad,sfault;wire[23:0]xa;wire[1023:0]xd;
qfd_dv_stream_tile stream(.ck(ck),.rst_n(srst),.sid(4'(sid)),.cfg_v(cfg),.cfg_dir(2'b11),.cfg_tag(28'h4845414),
 .sw_lo('0),.sw_v(1'b0),.sw_hi('0),.se_lo('0),.se_v(1'b0),.se_hi('0),.so_e(oe),.so_w(ow),
 .xw_we(pack_we),.xw_addr(pack_addr),.xw_data(pack_data),.tw_we(),.tw_kind(),.tw_addr(),.tw_data_lo(),.tw_data_hi(),.xt_v(xv),.xt_a(xa),.xt_d_lo(xd[511:0]),.xt_d_hi(xd[1023:512]),.xt_bad(xbad),.fault(sfault));
function automatic[15:0]bf16(input[31:0]v);reg[32:0]r;begin r={1'b0,v}+33'h7fff+{32'd0,v[16]};bf16=r[31:16];end endfunction
function automatic[31:0]xvalue(input integer i,input integer u);integer e;begin e=127+(i*3+u)%5-2;xvalue=32'(e<<23);end endfunction
always @(posedge ck)begin
 cy=cy+1;
 if(active)begin
  if(cmd[0]&&issue<0)issue=cy;
  if(dut.c0_emit0&&first_emit<0)first_emit=cy;
  if(dut.L_va_re[0]&&first_req<0)first_req=cy;
  if(dut.M_va_re[0]&&first_bound<0)first_bound=cy;
  if(dut.u_suvm.u_vm8q.u_cl.g_crb[0].m_rce&&first_gain_read<0)first_gain_read=cy;
  if(dut.u_head0.u_h.u_lane.s1_v&&first_operand<0)first_operand=cy;
  if(dut.h0_vm_we)begin if(first_pin_write<0)first_pin_write=cy;last_pin_write=cy;end
  if(dut.h0_retire)begin if(first_retire<0)first_retire=cy;last_retire=cy;retires=retires+1;end
  if(dut.u_suvm.u_su8.ready&&dut.u_suvm.u_su8.inflight==0&&count>0&&first_ready<0)first_ready=cy;
  if(dut.L_vm_we[0])begin
   if(first_write<0)first_write=cy;last_write=cy;
   if(mode==0)begin
    outidx=(dut.L_vm_waddr[23:0]&24'h3fffff);rowidx=outidx/dso;colidx=outidx%dso;outidx=rowidx*128+colidx;
    if(outidx<0||outidx>=n||seen[outidx]||dut.L_vm_wdata[31:0]!==gold[cid*384+outidx])$fatal(1,"HEAD_PAYLOAD case%0d logical%0d idx%0d got%08x expected%08x",cid,logical_head,outidx,dut.L_vm_wdata[31:0],gold[cid*384+outidx]);
    seen[outidx]=1;
   end else begin
    sfu_outidx=dut.L_vm_waddr[23:0]-((op==0)?1024:(op==1)?1280:1536);
    if(sfu_outidx<0||sfu_outidx>=128||dut.L_vm_wdata[31:0]!==sfu_gold[op*128+sfu_outidx])$fatal(1,"SFU_PAYLOAD op%0d idx%0d got%08x expected%08x",op,sfu_outidx,dut.L_vm_wdata[31:0],sfu_gold[op*128+sfu_outidx]);
   end
   count=count+1;
  end
  if(mode==0&&oe[1087])begin
   outidx=oe[1075:1052];rowidx=outidx/dso;colidx=outidx%dso;outidx=rowidx*128+colidx;
   if(outidx<0||outidx+63>=n||beatseen[outidx/64])$fatal(1,"PACK_ADDRESS");
   for(integer bi=0;bi<64;bi=bi+1)if(oe[16*bi+:16]!==bf16(gold[cid*384+outidx+bi]))$fatal(1,"PACK_PAYLOAD case%0d idx%0d",cid,outidx+bi);
   beatseen[outidx/64]=1;beats=beats+1;if(first_BF16<0)first_BF16=cy;last_BF16=cy;
  end
 end
 if(rst_n&&dut.u_suvm.u_vm8q.u_cl.g_crb[0].m_we&&mode==0)begin
  if(dut.u_suvm.u_vm8q.u_cl.g_crb[0].m_wa==10'(68+128*user_id)&&first_gain_store<0)first_gain_store=cy;
  if(dut.u_suvm.u_vm8q.u_cl.g_crb[0].m_wa==10'(68+128*user_id+n/16-1))last_gain_store=cy;
 end
 if(rst_n&&dut.u_suvm.u_vm8q.u_pg.g_prog[0].lo_we)programme_store=cy;
end

task automatic clear_dates;
 begin count=0;beats=0;retires=0;issue=-1;first_emit=-1;first_req=-1;first_bound=-1;first_gain_read=-1;first_operand=-1;first_pin_write=-1;last_pin_write=-1;first_write=-1;last_write=-1;first_retire=-1;last_retire=-1;first_BF16=-1;last_BF16=-1;first_ready=-1;seen=0;beatseen=0;end
endtask
task automatic report_dates;
 begin
 $display("PROFILE_DATES mode=%0d case=%0d op=%0d logical=%0d cmd=%0d emit=%0d req=%0d vm_bound=%0d gain_read=%0d operand_visible=%0d head_write=%0d head_lastwrite=%0d LRLYwrite=%0d LRLYlastwrite=%0d head_retire=%0d head_lastretire=%0d SU8ready=%0d BF16=%0d lastBF16=%0d programme_store=%0d first_gain_store=%0d last_gain_store=%0d count=%0d retires=%0d beats=%0d",mode,cid,op,logical_head,issue,first_emit,first_req,first_bound,first_gain_read,first_operand,first_pin_write,last_pin_write,first_write,last_write,first_retire,last_retire,first_ready,first_BF16,last_BF16,programme_store,first_gain_store,last_gain_store,count,retires,beats);
 end
endtask
initial begin
 csid[0]=0;
cuser[0]=0;
chead[0]=0;
cn[0]=384;
cdso[0]=1536;
cxbase[0]=0;
crstd[0]=400;
cpidx[0]=16;
cdbase[0]=4194304;
csid[1]=0;
cuser[1]=0;
chead[1]=7;
cn[1]=384;
cdso[1]=1536;
cxbase[1]=0;
crstd[1]=400;
cpidx[1]=16;
cdbase[1]=4194304;
csid[2]=0;
cuser[2]=1;
chead[2]=0;
cn[2]=384;
cdso[2]=1536;
cxbase[2]=4096;
crstd[2]=4496;
cpidx[2]=144;
cdbase[2]=4194304;
csid[3]=0;
cuser[3]=1;
chead[3]=7;
cn[3]=384;
cdso[3]=1536;
cxbase[3]=4096;
crstd[3]=4496;
cpidx[3]=144;
cdbase[3]=4194304;
csid[4]=0;
cuser[4]=2;
chead[4]=0;
cn[4]=384;
cdso[4]=1536;
cxbase[4]=8192;
crstd[4]=8592;
cpidx[4]=272;
cdbase[4]=4194304;
csid[5]=0;
cuser[5]=2;
chead[5]=7;
cn[5]=384;
cdso[5]=1536;
cxbase[5]=8192;
crstd[5]=8592;
cpidx[5]=272;
cdbase[5]=4194304;
csid[6]=0;
cuser[6]=3;
chead[6]=0;
cn[6]=384;
cdso[6]=1536;
cxbase[6]=12288;
crstd[6]=12688;
cpidx[6]=400;
cdbase[6]=4194304;
csid[7]=0;
cuser[7]=3;
chead[7]=7;
cn[7]=384;
cdso[7]=1536;
cxbase[7]=12288;
crstd[7]=12688;
cpidx[7]=400;
cdbase[7]=4194304;
csid[8]=8;
cuser[8]=0;
chead[8]=0;
cn[8]=256;
cdso[8]=1536;
cxbase[8]=0;
crstd[8]=400;
cpidx[8]=16;
cdbase[8]=4195328;
csid[9]=8;
cuser[9]=0;
chead[9]=7;
cn[9]=256;
cdso[9]=1536;
cxbase[9]=0;
crstd[9]=400;
cpidx[9]=16;
cdbase[9]=4195328;
csid[10]=8;
cuser[10]=1;
chead[10]=0;
cn[10]=256;
cdso[10]=1536;
cxbase[10]=4096;
crstd[10]=4496;
cpidx[10]=144;
cdbase[10]=4195328;
csid[11]=8;
cuser[11]=1;
chead[11]=7;
cn[11]=256;
cdso[11]=1536;
cxbase[11]=4096;
crstd[11]=4496;
cpidx[11]=144;
cdbase[11]=4195328;
csid[12]=8;
cuser[12]=2;
chead[12]=0;
cn[12]=256;
cdso[12]=1536;
cxbase[12]=8192;
crstd[12]=8592;
cpidx[12]=272;
cdbase[12]=4195328;
csid[13]=8;
cuser[13]=2;
chead[13]=7;
cn[13]=256;
cdso[13]=1536;
cxbase[13]=8192;
crstd[13]=8592;
cpidx[13]=272;
cdbase[13]=4195328;
csid[14]=8;
cuser[14]=3;
chead[14]=0;
cn[14]=256;
cdso[14]=1536;
cxbase[14]=12288;
crstd[14]=12688;
cpidx[14]=400;
cdbase[14]=4195328;
csid[15]=8;
cuser[15]=3;
chead[15]=7;
cn[15]=256;
cdso[15]=1536;
cxbase[15]=12288;
crstd[15]=12688;
cpidx[15]=400;
cdbase[15]=4195328;
 bad_reply=$test$plusargs("BAD_REPLY");
 $readmemh("prog.hex",progs);$readmemh("gains.hex",gainrows);$readmemh("expected.hex",gold);$readmemh("sfu_program.hex",sfu_program);$readmemh("sfu_expected.hex",sfu_gold);
 for(cid=0;cid<NCASE;cid=cid+1)begin
  mode=0;active=0;cfg=0;cmd=0;w16=0;w1=0;tw=0;rst_n=0;repeat(64)@(negedge ck);
  user_id=cuser[cid];sid=csid[cid];logical_head=3'(chead[cid]);n=cn[cid];dso=cdso[cid];first_gain_store=-1;last_gain_store=-1;programme_store=-1;
  rst_n=1;repeat(512)@(negedge ck);
  for(j=0;j<n;j=j+16)begin w16=1;w16a=24'(cxbase[cid]+j);for(k=0;k<16;k=k+1)w16d[32*k+:32]=xvalue(j+k,user_id);@(negedge ck);end
  w16=0;w1=1;w1a=24'(crstd[cid]);w1d=32'h3f000000;@(negedge ck);w1=0;
  tw=1;twk=3;twa=24'(cpidx[cid]/2);twd=progs[cid];@(negedge ck);
  for(j=0;j<n/16;j=j+1)begin twk=1;twa=24'(68+128*user_id+j);twd=gainrows[cid*24+j];@(negedge ck);end
  tw=0;repeat(128)@(negedge ck);cfg=1;@(negedge ck);cfg=0;repeat(16)@(negedge ck);
  clear_dates();active=1;cmd=(116'(cpidx[cid])<<4)|116'd3;@(negedge ck);cmd=0;
  repeat(512)@(negedge ck);report_dates();
  if(count!=n/8||retires!=n/8||beats!=n/64||first_gain_store<0||last_gain_store<0||first_gain_read<=first_gain_store)$fatal(1,"HEAD_COUNT case%0d got%0d/%0d/%0d",cid,count,retires,beats);
  if(dut.su_fault||dut.vm_fault||sfault||xbad)$fatal(1,"NATIVE_FAULT head case%0d su%0b vm%0b pack%0b",cid,dut.su_fault,dut.vm_fault,sfault);
  total=total+count;totalbeats=totalbeats+beats;active=0;
 end
 // Real SFUs and minimal native class changes, one physical head. The controller
 // independently observes its actual inflight/ready state; no fixed busy charge.
 mode=1;active=0;rst_n=0;cmd=0;cfg=0;logical_head=0;repeat(64)@(negedge ck);rst_n=1;repeat(512)@(negedge ck);
 for(j=0;j<384;j=j+16)begin w16=1;w16a=j;for(k=0;k<16;k=k+1)w16d[32*k+:32]=((j+k)%3==0)?32'h40000000:((j+k)%3==1)?32'h40800000:32'h41000000;@(negedge ck);end
 w16=0;tw=1;twk=3;twa=0;twd=sfu_program[0];@(negedge ck);twa=1;twd=sfu_program[1];@(negedge ck);tw=0;repeat(128)@(negedge ck);
 for(op=0;op<4;op=op+1)begin
  clear_dates();active=1;cmd=(116'(op)<<4)|116'd3;@(negedge ck);cmd=0;
  expected_count=(op==3)?1:16;
  for(t=0;t<512;t=t+1)begin
   @(negedge ck);
   if(count==expected_count&&retires==expected_count&&dut.su_idle&&dut.u_suvm.u_su8.ready&&dut.u_suvm.u_su8.inflight==0)break;
  end
  report_dates();
  if(count!=expected_count||retires!=expected_count||dut.su_fault||dut.vm_fault)$fatal(1,"SFU_COUNT op%0d count%0d retire%0d fault%0b/%0b",op,count,retires,dut.su_fault,dut.vm_fault);
  active=0;@(negedge ck);
 end
 $display("MEM44_ONE_HEAD_PROFILE_PASS genuine_cases%0d actual_FP32words%0d fullcohort_BF16beats%0d independent_SILU_RSQ_PASS companions7golden extra_retire_transport0",NCASE,total,totalbeats);$finish;
end
endmodule
