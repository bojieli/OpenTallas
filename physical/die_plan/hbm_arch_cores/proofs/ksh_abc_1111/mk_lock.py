import re,sys
src,dst=sys.argv[1],sys.argv[2]
s=open(src).read()
s=s.replace("module tb_hbm_svc_wb_kshare_splitstrap_q;","module tb_ksh_lock;")
# shadow reference core next to each dut core, same inputs, own outputs
m=re.search(r"  ot_hbm_svc_vm_kshare_splitstrap #\(\.MUT\(KSMUT\)\) u\((.*?)\.fault\(ks_fault\[k\]\)\);\n",s,re.S)
body=m.group(1)
outs={'g_k_rdy':4,'g_k_wr_done':4,'g_kr_v':4,'g_kr_tag':68,'g_kr_beat':16,'g_kr_data':1024,'c_k_v':4,'c_k_addr':120,'c_k_len':16,
 'c_k_tag':68,'c_k_we':4,'c_k_wdata':1024,'c_k_wstrb':128,'c_kr_rdy':4,'w_k_rdy':4,'w_k_wr_done':4,'fill_v':4,'fill_bank':4,
 'fill_slot':24,'fill_epoch':64,'fill_data':1024}
rb=body
decl=""
for o,w in outs.items():
  rb=re.sub(r"\.%s\(%s\[[^\]]*\]\)"%(o,o),".%s(r_%s)"%(o,o),rb)
  decl+="  wire[%d:0]r_%s;\n"%(w-1,o)
decl+="  wire r_fault;\n"
ref="  ot_hbm_svc_vm_kshare_splitstrap_REF #(.MUT(0)) r(%s.fault(r_fault));\n"%rb
s=s[:m.end()]+decl+ref+s[m.end():]
cmp=r'''
 // ---------------------------------------------------------------- LOCK-STEP vs the reference core (HBM-CORES-B 11-11)
 integer lk_err=0,lk_fw=0,lk_ww=0,lk_hcyc=0,lk_scyc=0,lk_out=0;
 always @(posedge hbm) if(hrst) lk_hcyc=lk_hcyc+1;
 always @(posedge stream) if(srst) lk_scyc=lk_scyc+1;
 generate for(k=0;k<8;k=k+1)begin:glk
  // hbm-domain K-port outputs (cycle exact for forms A and C; form B moves WB windows by design)
  wire[2499:0]ho_u={g_k_rdy[4*k+:4],g_k_wr_done[4*k+:4],g_kr_v[4*k+:4],g_kr_tag[68*k+:68],g_kr_beat[16*k+:16],g_kr_data[1024*k+:1024],
    c_k_v[4*k+:4],c_k_addr[120*k+:120],c_k_len[16*k+:16],c_k_tag[68*k+:68],c_k_we[4*k+:4],c_k_wdata[1024*k+:1024],c_k_wstrb[128*k+:128],
    c_kr_rdy[4*k+:4],w_k_rdy[4*k+:4],w_k_wr_done[4*k+:4]};
  wire[2499:0]ho_r={gks[k].r_g_k_rdy,gks[k].r_g_k_wr_done,gks[k].r_g_kr_v,gks[k].r_g_kr_tag,gks[k].r_g_kr_beat,gks[k].r_g_kr_data,
    gks[k].r_c_k_v,gks[k].r_c_k_addr,gks[k].r_c_k_len,gks[k].r_c_k_tag,gks[k].r_c_k_we,gks[k].r_c_k_wdata,gks[k].r_c_k_wstrb,
    gks[k].r_c_kr_rdy,gks[k].r_w_k_rdy,gks[k].r_w_k_wr_done};
`ifndef LK_NO_HBM_EXACT
  always @(posedge hbm) if(hrst&&ho_u!==ho_r)begin lk_err=lk_err+1;if(lk_err<10)$display("LOCK hbm outputs differ k%0d cyc%0d",k,lk_hcyc);end
`endif
  // stream WB command into u_wcmd: dut = reference + LK_WSHIFT stream edges
  reg[74:0]wr_d1,wr_d0;
  always @(posedge stream) if(srst)begin
   wr_d0<={gks[k].r.u_wcmd.wr_valid,gks[k].r.u_wcmd.wr_data};wr_d1<=wr_d0;
   if(gks[k].u.u_wcmd.wr_valid)lk_ww=lk_ww+1;
   if({gks[k].u.u_wcmd.wr_valid,gks[k].u.u_wcmd.wr_data}!==((`LK_WSHIFT)?wr_d0:{gks[k].r.u_wcmd.wr_valid,gks[k].r.u_wcmd.wr_data}))begin
    lk_err=lk_err+1;if(lk_err<10)$display("LOCK u_wcmd write differs k%0d scyc%0d",k,lk_scyc);end
  end
  for(genvar l=0;l<4;l=l+1)begin:gl
   // VM fill FIFO write: dut = reference + LK_FSHIFT hbm edges (cycle exact while the FIFO accepts)
   reg[279:0]fw_d0;reg hf_d0;
   always @(posedge hbm) if(hrst)begin
    fw_d0<={gks[k].r.lane[l].u_fill.wr_valid,gks[k].r.lane[l].u_fill.wr_data};hf_d0<=gks[k].r.lane[l].hf;
    if(gks[k].u.lane[l].u_fill.wr_valid)lk_fw=lk_fw+1;
    if(!gks[k].u.lane[l].u_fill.wr_ready&&gks[k].u.lane[l].u_fill.wr_valid)begin lk_err=lk_err+1;$display("LOCK fill overflow k%0d l%0d",k,l);end
`ifndef LK_NO_FILL_EXACT
    if({gks[k].u.lane[l].u_fill.wr_valid,gks[k].u.lane[l].u_fill.wr_data}!==((`LK_FSHIFT)?fw_d0:{gks[k].r.lane[l].u_fill.wr_valid,gks[k].r.lane[l].u_fill.wr_data})
       ||gks[k].u.lane[l].hf!==((`LK_FSHIFT)?hf_d0:gks[k].r.lane[l].hf))begin
     lk_err=lk_err+1;if(lk_err<10)$display("LOCK u_fill write/hf differs k%0d l%0d cyc%0d",k,l,lk_hcyc);end
`endif
   end
  end
 end endgenerate
 // stream fill outputs: same beats, same order per PC (time may move by the CDC); per-beat arrival offset histogram
 integer fq_r[0:31][$];integer fq_u[0:31][$];integer offh[-4:4];integer lk_fill=0;
 generate for(k=0;k<32;k=k+1)begin:gfo
  always @(posedge stream) if(srst)begin : fo
   if(gks[k/4].r_fill_v[k%4])fq_r[k].push_back(lk_scyc);
   if(fill_v[k])begin fq_u[k].push_back(lk_scyc);lk_fill=lk_fill+1;end
   while(fq_r[k].size()>0&&fq_u[k].size()>0)begin : pr
    integer d;d=fq_u[k].pop_front()-fq_r[k].pop_front();
    if(d<-4||d>4)begin lk_err=lk_err+1;$display("LOCK fill offset %0d pc%0d",d,k);end else offh[d]=offh[d]+1;
   end
  end
  // fill content: compare the stream fill words in order
  logic[278:0]cq_r[$],cq_u[$];
  always @(posedge stream) if(srst)begin
   if(gks[k/4].r_fill_v[k%4])cq_r.push_back({gks[k/4].r_fill_bank[k%4],gks[k/4].r_fill_epoch[16*(k%4)+:16],gks[k/4].r_fill_slot[6*(k%4)+:6],gks[k/4].r_fill_data[256*(k%4)+:256]});
   if(fill_v[k])cq_u.push_back({fill_bank[k],fill_epoch[16*k+:16],fill_slot[6*k+:6],fill_data[256*k+:256]});
   while(cq_r.size()>0&&cq_u.size()>0)if(cq_r.pop_front()!==cq_u.pop_front())begin lk_err=lk_err+1;$display("LOCK fill word differs pc%0d",k);end
  end
 end endgenerate
 initial for(int d=-4;d<=4;d++)offh[d]=0;
 final begin
  $display("LOCK cfg=%s hbm_cycles=%0d stream_cycles=%0d fill_fifo_writes=%0d wcmd_writes=%0d fills=%0d mismatches=%0d",`LK_CFG,lk_hcyc,lk_scyc,lk_fw,lk_ww,lk_fill,lk_err);
  $display("LOCK fill_v offset dut-ref stream edges: -1:%0d 0:%0d +1:%0d +2:%0d +3:%0d",offh[-1],offh[0],offh[1],offh[2],offh[3]);
 end
'''
anchor=" // ---------------------------------------------------------------- data images"
s=s.replace(anchor,cmp+anchor,1)
# lock errors make the run fail
s=s.replace("  if(errors==0)$display(\"PASS","  errors=errors+lk_err;$display(\"LOCK cfg=%s hbm_cycles=%0d mismatches=%0d fill_fifo_writes=%0d wcmd_writes=%0d\",`LK_CFG,lk_hcyc,lk_err,lk_fw,lk_ww);\n  if(errors==0)$display(\"PASS",1)
open(dst,'w').write(s)
