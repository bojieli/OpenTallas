`timescale 1ps/1fs
// HBM-BW 2026-10-19: controller-only HBM boundary bench for ONE SM's four pseudo-channels.  Four real controller leaves
// (ot_hbm_svc_pc_ctrl_leaf, or with +define+MR the multi-row ot_hbm_svc_pc_ctrl_leaf_mr) -> the DRAM command fixture
// (tb_svg_rel_dram_sparse: the same JEDEC-class timing checks, $fatal on any violation).  Each PC is driven exactly as
// the SM service's prefetch owner drives it (ot_hbm_svc_prefetch_overlap_owner_rel_id): per block, len-4 requests over
// the block's per-PC words t = 0, 4, ... at k_addr = {row, bhi, col, pc^col^hi5, blo} with the sub-row slot in t[9:7],
// 32 outstanding requests per PC (OWNER_AW 5), the next block's requests right after the current block's (OVERLAP=1),
// responses always taken.  It plays a compiler block list (+BLK=file of "row15 slot3 words8" hex, +NB=n) and prints the
// sustained rate: sectors x 32 B per stream edge (stream 1.2 GHz, HBM controller 0.9766 GHz).
module tb_hbm_bw_pc4;
 parameter integer MAXB=4096;
 reg hbm=0;initial forever #512 hbm=~hbm;
 reg rst_n=0;reg owner_enable=0;
 reg [25:0]blk_m[0:MAXB-1];integer nb,warm;string fb;
 wire[31:0]kv_w,krdy,kwe,kdone,rv_,rrdy;wire[959:0]ka;wire[127:0]kl,rb;wire[543:0]kt,rt;wire[8191:0]kw,rd;wire[1023:0]ks;
 wire[31:0]row_v,col_v,col_we,dram_rvalid;wire[95:0]row_op;wire[159:0]row_bank,col_bank,col_col;wire[607:0]row_row;
 wire[8191:0]col_data,dram_rdata;wire[1023:0]col_strb;wire[3:0]pcf,owf;
 reg[3:0]kv;reg[29:0]kaddr[0:3];reg[3:0]klen[0:3];reg[16:0]ktag[0:3];
 for(genvar p=0;p<4;p=p+1)begin:g_pc
`ifdef H9B
  wire[5:0]ofs;assign owf[p]=|ofs;
  localparam integer RP=(p*118/32)%118;
  localparam integer RELOAD=118+RP+((RP+118+p)%2);
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b u(.pc_id(5'(p)),.refresh_reload(8'(RELOAD)),.owner_fault_split(ofs),
`else
`ifdef MR
`ifdef SAFE
  ot_hbm_svc_pc_ctrl_leaf_safe #(.P(p)
`else
  ot_hbm_svc_pc_ctrl_leaf_mr #(.P(p)
`endif
`ifdef MRKEY0
   ,.MRKEY(0)
`endif
  ) u(
`else
  ot_hbm_svc_pc_ctrl_leaf #(.P(p)) u(
`endif
`endif
   .clk(hbm),.rst_n(rst_n),.k_v(kv[p]),.k_rdy(krdy[p]),.k_we(1'b0),.k_addr(kaddr[p]),.k_len(klen[p]),.k_tag(ktag[p]),
   .k_wdata(256'b0),.k_wstrb(32'b0),.kr_v(rv_[p]),.kr_rdy(1'b1),.kr_tag(rt[p*17+:17]),.kr_beat(rb[p*4+:4]),.kr_data(rd[p*256+:256]),
   .k_wr_done(kdone[p]),.row_v(row_v[p]),.row_op(row_op[p*3+:3]),.row_bank(row_bank[p*5+:5]),.row_row(row_row[p*19+:19]),
   .col_v(col_v[p]),.col_we(col_we[p]),.col_bank(col_bank[p*5+:5]),.col_col(col_col[p*5+:5]),.col_data(col_data[p*256+:256]),
   .col_strb(col_strb[p*32+:32]),.dram_rvalid(dram_rvalid[p]),.dram_rdata(dram_rdata[p*256+:256]),.pc_fault(pcf[p])
`ifndef H9B
   ,.owner_fault(owf[p])
`endif
  );
 end
 assign row_v[31:4]=0;assign col_v[31:4]=0;assign col_we[31:4]=0;
 tb_svg_rel_dram_sparse dram(.clk(hbm),.rst_n(rst_n),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),
  .col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata));
 // ---------------- owner model per PC
 integer cyc=0;integer pause_until[0:3];
 integer bi[0:3],t[0:3],outst[0:3],beats[0:3][0:31],done_at[0:3],first_at[0:3],warm_at[0:3],cols[0:3],ret[0:3],refs[0:3],acts[0:3];
 integer blk_ret[0:3][0:MAXB-1],blk_need[0:3][0:MAXB-1],tagblk[0:3][0:31];
 integer gap_n[0:3],gap_cyc[0:3],last_col[0:3];
 initial for(integer p=0;p<4;p=p+1)begin pause_until[p]=0;bi[p]=0;t[p]=0;outst[p]=0;done_at[p]=-1;first_at[p]=-1;warm_at[p]=-1;cols[p]=0;ret[p]=0;refs[p]=0;acts[p]=0;
  gap_n[p]=0;gap_cyc[p]=0;last_col[p]=-1;for(integer e=0;e<32;e=e+1)beats[p][e]=0;end
 function automatic [29:0]addr_of(input integer pc,input [14:0]row,input [2:0]slot,input [9:0]tt,input full);
  reg[9:0]ts,mt;reg[4:0]db,col,hi5;reg[2:0]bhi;reg[1:0]blo;
  begin ts={tt[9:7]|slot,tt[6:0]};mt=full?{ts[9:2],row[1:0]}:ts;db={mt[9:7],mt[1:0]};col=mt[6:2];
   bhi=db[4:2]^row[4:2];blo=db[1:0]^row[1:0];hi5={row[1:0],bhi};addr_of={row,bhi,col,5'(pc)^col^hi5,blo};end
 endfunction
 always @(posedge hbm)if(rst_n&&owner_enable)begin:OWN
  reg[14:0]row;reg[2:0]slot;integer w;reg full;
  cyc<=cyc+1;
  for(integer p=0;p<4;p=p+1)begin
   // response side (always taken)
   if(rv_[p])begin:R
    integer e;e=rt[p*17+:5];
    beats[p][e]=beats[p][e]-1;ret[p]=ret[p]+1;
    if(beats[p][e]==0)begin outst[p]=outst[p]-1;blk_need[p][tagblk[p][e]]=blk_need[p][tagblk[p][e]]-1;
     if(blk_need[p][tagblk[p][e]]==0)begin blk_ret[p][tagblk[p][e]]=cyc;if(tagblk[p][e]==nb-1)done_at[p]=cyc;if(tagblk[p][e]==warm-1)warm_at[p]=cyc;end end
   end
   // request side: the registered offer kv/kaddr/klen/ktag is accepted on k_rdy; the next offer follows the owner
   if(kv[p]&&krdy[p])begin
    if(first_at[p]<0)first_at[p]=cyc;
    beats[p][ktag[p][4:0]]=klen[p];tagblk[p][ktag[p][4:0]]=bi[p];outst[p]=outst[p]+1;
    w=blk_m[bi[p]][7:0];t[p]=t[p]+klen[p];if(t[p]>=w)begin bi[p]=bi[p]+1;t[p]=0;
`ifdef BURST_GAPS
      pause_until[p]=cyc+((bi[p]*37)%97);
`endif
     end
   end
   if(!(kv[p]&&!krdy[p]))begin:ISS
    integer e2;
    kv[p]<=0;e2=-1;for(integer e=31;e>=0;e=e-1)if(beats[p][e]==0)e2=e;
    if(bi[p]<nb&&outst[p]<32&&e2>=0&&cyc>=pause_until[p])begin
     row=blk_m[bi[p]][25:11];slot=blk_m[bi[p]][10:8];w=blk_m[bi[p]][7:0];full=(w>=t[p]+4);
     kv[p]<=1;kaddr[p]<=addr_of(p,row,slot,10'(t[p]),full);klen[p]<=full?4'd4:4'd1;ktag[p]<=17'(e2);
    end
   end
   if(col_v[p])begin cols[p]=cols[p]+1;if(last_col[p]>=0&&cyc-last_col[p]>8&&bi[p]<nb)begin gap_n[p]=gap_n[p]+1;gap_cyc[p]=gap_cyc[p]+cyc-last_col[p]-1;
`ifdef GAPS
     $display("GAP pc%0d cyc %0d len %0d blk %0d",p,cyc,cyc-last_col[p]-1,bi[p]);
`endif
    end last_col[p]=cyc;end
   if(row_v[p]&&row_op[p*3+:3]==6)refs[p]=refs[p]+1;
`ifdef GAPS
`ifdef MR
   if(row_v[p]&&row_op[p*3+:3]==6)case(p)
    0:$display("REF pc0 cyc %0d bank %0d key %0d tail %0d",cyc,row_bank[4:0],g_pc[0].u.u_cfg.controller.rkey,g_pc[0].u.u_cfg.controller.tail_set);
    1:$display("REF pc1 cyc %0d bank %0d key %0d tail %0d",cyc,row_bank[9:5],g_pc[1].u.u_cfg.controller.rkey,g_pc[1].u.u_cfg.controller.tail_set);
    default:;
   endcase
`endif
`endif
   if(row_v[p]&&row_op[p*3+:3]==1)acts[p]=acts[p]+1;
   if(pcf[p]||owf[p])begin $display("FAULT pc%0d pc_fault %0d owner_fault %0d cyc %0d",p,pcf[p],owf[p],cyc);$fatal(1,"leaf fault");end
  end
 end
`ifdef EXPOSE
 // HBM-MC2 (10-19): exposed-bank-latency census of the SAFE controller (MR+SAFE only).  Every HBM edge of each PC between
 // its first request and its last response is classified by the in-order column head: busy (a column issued), empty
 // (no queued entry: request/response-reservation side), refresh (head bank in tRFCpb), closed (head bank not open:
 // waiting tRP/tRRD/tFAW/ACT select), conflict (head bank open on another row: PRE+ACT), trcd (open on the row, tRCD
 // timer running), other (tCCD_L / RD-WR turnaround / precharge flag).  Pure observation, no DUT change.
 integer ex_busy[0:3],ex_empty[0:3],ex_ref[0:3],ex_closed[0:3],ex_conf[0:3],ex_rcd[0:3],ex_oth[0:3];
 initial for(integer p=0;p<4;p=p+1)begin ex_busy[p]=0;ex_empty[p]=0;ex_ref[p]=0;ex_closed[p]=0;ex_conf[p]=0;ex_rcd[p]=0;ex_oth[p]=0;end
 for(genvar p=0;p<4;p=p+1)begin:g_ex
  always @(posedge hbm)if(rst_n&&owner_enable&&first_at[p]>=0&&done_at[p]<0)begin
   if(col_v[p])ex_busy[p]=ex_busy[p]+1;
   else if(!g_pc[p].u.u_cfg.controller.q_ne)ex_empty[p]=ex_empty[p]+1;
   else if(g_pc[p].u.u_cfg.controller.blk[g_pc[p].u.u_cfg.controller.hb])ex_ref[p]=ex_ref[p]+1;
   else if(!g_pc[p].u.u_cfg.controller.open[g_pc[p].u.u_cfg.controller.hb])ex_closed[p]=ex_closed[p]+1;
   else if(!g_pc[p].u.u_cfg.controller.head_row_match[g_pc[p].u.u_cfg.controller.hb])ex_conf[p]=ex_conf[p]+1;
   else if(!g_pc[p].u.u_cfg.controller.head_timer_ready[g_pc[p].u.u_cfg.controller.hb])ex_rcd[p]=ex_rcd[p]+1;
   else ex_oth[p]=ex_oth[p]+1;
  end
 end
`endif
 initial begin
  if(!$value$plusargs("BLK=%s",fb)||!$value$plusargs("NB=%d",nb))$fatal(1,"plusargs");
  if(!$value$plusargs("WARM=%d",warm))warm=8;
  if(nb>MAXB)$fatal(1,"NB");
  $readmemh(fb,blk_m,0,nb-1);
  for(integer p=0;p<4;p=p+1)begin kv[p]=0;kaddr[p]=0;klen[p]=0;ktag[p]=0;
   for(integer b=0;b<nb;b=b+1)begin blk_need[p][b]=blk_m[b][7:0]/4+blk_m[b][7:0]%4;blk_ret[p][b]=-1;end end
  repeat(5)@(negedge hbm);rst_n=1;
  // Start traffic after the leaf reset relay and captured PC straps settle.
  // Offering during reset can appear ready while the skid is held empty.
  repeat(8)@(negedge hbm);owner_enable=1;
  wait(done_at[0]>=0&&done_at[1]>=0&&done_at[2]>=0&&done_at[3]>=0);
  begin:REP
   integer secs,secw,tot,totw;real cyc_all,cyc_st,bpe,bpe_st;
   secs=0;secw=0;for(integer b=0;b<nb;b=b+1)begin secs=secs+blk_m[b][7:0];if(b>=warm)secw=secw+blk_m[b][7:0];end
   for(integer p=0;p<4;p=p+1)if(cols[p]!=secs||ret[p]!=secs)
    $fatal(1,"sector conservation pc%0d wanted%0d cols%0d returns%0d",p,secs,cols[p],ret[p]);
   tot=0;totw=0;for(integer p=0;p<4;p=p+1)begin if(done_at[p]-first_at[p]>tot)tot=done_at[p]-first_at[p];if(done_at[p]-warm_at[p]>totw)totw=done_at[p]-warm_at[p];end
   // bytes per stream edge: 4 PCs x sectors x 32 B over (hbm cycles x 1.024 ns / 0.8333 ns)
   bpe=4.0*secs*32.0/(tot*1.024/0.83333333);bpe_st=4.0*secw*32.0/(totw*1.024/0.83333333);
   $display("BW blocks=%0d sectors_per_pc=%0d hbm_cycles=%0d B_per_edge=%.2f steady_blocks=%0d steady_cycles=%0d steady_B_per_edge=%.2f peak=104.17",
    nb,secs,tot,bpe,nb-warm,totw,bpe_st);
   for(integer p=0;p<4;p=p+1)$display("PC%0d cols=%0d returns=%0d acts=%0d refs=%0d gaps>8=%0d gap_cycles=%0d first=%0d done=%0d",p,cols[p],ret[p],acts[p],refs[p],gap_n[p],gap_cyc[p],first_at[p],done_at[p]);
`ifdef EXPOSE
   for(integer p=0;p<4;p=p+1)$display("EXPOSE pc%0d busy=%0d empty=%0d refresh=%0d closed=%0d conflict=%0d trcd=%0d other=%0d acts=%0d",
    p,ex_busy[p],ex_empty[p],ex_ref[p],ex_closed[p],ex_conf[p],ex_rcd[p],ex_oth[p],acts[p]);
`endif
   for(integer b=0;b<nb&&b<400;b=b+1)$display("BLK %0d row %0d slot %0d words %0d ret %0d %0d %0d %0d",b,blk_m[b][25:11],blk_m[b][10:8],blk_m[b][7:0],blk_ret[0][b],blk_ret[1][b],blk_ret[2][b],blk_ret[3][b]);
  end
  $display("DONE dram_reads=%0d refreshes=%0d",dram.reads,dram.refreshes);
  $finish;
 end
 initial begin #2000000000;$display("TIMEOUT");$fatal(1,"timeout");end
endmodule
