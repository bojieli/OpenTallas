`timescale 1ps/1fs
`default_nettype none
// RTL-BUILD-HBM/stk 2026-10-18: ONE QUADRANT's DMA write-back path of the d4g per-quadrant services (plan item 10), with a
// lockstep reference of today's per-stack master.  Same structure and checks as tb_hbm_svc_wb_kshare_q (the GEN0 stack
// bench), restricted to the quadrant QE (0 = W: PCs 0..15, kshare sm 0..3; 1 = E: PCs 16..31, kshare sm 4..7):
//   DMA write-back pins (as ot_hgi_dma_back_static_vp4_banks drives them; sectors = QUADRANT ORDINALS)
//   -> ot_hbm_svc_wb_kport_q (quad = QE) -> 4 x ot_hbm_svc_vm_kshare (unchanged master, WB windows sharing the K ports
//      with the group read/write feeds and VM fill windows) -> 32 real ot_hbm_svc_pc_ctrl_leaf controllers (the other
//      half idle) -> ot_hbm_svc_command_dram_pipeline_fixture (off-chip DRAM, timing-checked).
// Checks: (a) at each block's completing wa every ordinal o of the block is in DRAM at fold_QE(o) with its data
// (bit-exact, true completion), and no WB write ever reaches a PC outside the quadrant (kshare hash check + here);
// (b) LOCKSTEP vs ot_hbm_svc_wb_kport (GEN0 master, same DMA pins, its K ports on an ideal sink): wbw_v on the same
// stream edge, wbw_base = fold(master base), wbw_total = real span; wb_ready equal at every first drain; per block the
// same posted total; the set {fold(master K address) -> data} equals the set the quadrant writes, sector for sector;
// (c) group reads/writes and VM fills on the quadrant's 16 PCs exact, no fault anywhere.
// Params: QE, KSMUT (kshare MUT), WBMUT (wb_kport_q MUT), WOPEN.  Exit: "PASS" line, else WB_INTEGRITY / FAIL.
module tb_hbm_svc_wb_kshare_qh;
 parameter integer QE=1, KSMUT=0, WBMUT=0, WOPEN=0;
 localparam [31:0] K_BASE=32'h28800000;localparam [31:0] O_BASE=K_BASE>>1;localparam integer K_MEM=65536;localparam [1:0] STK=2'd2;
 localparam integer P0=16*QE;
 integer errors=0,cur_cycle=0;
 reg hbm=0,stream=0,hrst=0,srst=0;
 always #512 hbm=~hbm;
 always #416.667 stream=~stream;
 function automatic [29:0] fold(input [28:0] o);fold={o[28:6],1'(QE)^o[10]^o[15],o[5:0]};endfunction
 // ---------------------------------------------------------------- DMA-side pins
 reg rv=0,rb=0,fb=0,fs=0;reg[15:0]re=0,fe=0;reg[11:0]rt=0;reg[31:0]rbase=0;reg[2311:0]wd=0;
 wire wb_ready,fault_wb;wire[11:0]wa;wire wbw_v;wire[29:0]wbw_base;wire[11:0]wbw_total;
 wire[15:0]w_k_v,w_k_rdy,w_k_wr_done;wire[479:0]w_k_addr;wire[4095:0]w_k_wdata;
 ot_hbm_svc_wb_kport_q #(.WOPEN(WOPEN),.MUT(WBMUT)) u_wbp(.stream_clk(stream),.stream_rst_n(srst),.hbm_clk(hbm),.hbm_rst_n(hrst),
  .stream_fifo_clk({4{stream}}),.stk(STK),.quad(1'(QE)),
  .wb_reserve_v(rv),.wb_reserve_bank(rb),.wb_fill_bank(fb),.wb_reserve_epoch(re),.wb_fill_epoch(fe),.wb_reserve_sectors(rt),
  .wb_reserve_base(rbase),.wb_fill_start(fs),.wd(wd),.wb_ready(wb_ready),.wa(wa),
  .wbw_v(wbw_v),.wbw_base(wbw_base),.wbw_total(wbw_total),
  .w_k_v(w_k_v),.w_k_rdy(w_k_rdy),.w_k_addr(w_k_addr),.w_k_wdata(w_k_wdata),.w_k_wr_done(w_k_wr_done),.fault(fault_wb));
 // ---------------------------------------------------------------- lockstep reference: GEN0 per-stack master on an ideal K sink
 wire r_ready,r_fault;wire[11:0]r_wa;wire r_wbw_v;wire[29:0]r_wbw_base;wire[11:0]r_wbw_total;
 wire[31:0]r_k_v;wire[959:0]r_k_addr;wire[8191:0]r_k_wdata;reg[31:0]r_done1=0,r_done2=0;
 ot_hbm_svc_wb_kport #(.WOPEN(WOPEN),.MUT(0)) u_ref(.stream_clk(stream),.stream_rst_n(srst),.hbm_clk(hbm),.hbm_rst_n(hrst),
  .stream_fifo_clk({4{stream}}),.stk(STK),
  .wb_reserve_v(rv),.wb_reserve_bank(rb),.wb_fill_bank(fb),.wb_reserve_epoch(re),.wb_fill_epoch(fe),.wb_reserve_sectors(rt),
  .wb_reserve_base(rbase),.wb_fill_start(fs),.wd(wd),.wb_ready(r_ready),.wa(r_wa),
  .wbw_v(r_wbw_v),.wbw_base(r_wbw_base),.wbw_total(r_wbw_total),
  .w_k_v(r_k_v),.w_k_rdy({32{1'b1}}),.w_k_addr(r_k_addr),.w_k_wdata(r_k_wdata),.w_k_wr_done(r_done2),.fault(r_fault));
 logic[255:0]ref_w[int];logic[255:0]dut_w[int];
 always @(posedge hbm) if(hrst) begin : refsink
  integer p;
  r_done1<=r_k_v;r_done2<=r_done1;   // ideal controller: true completion 2 hbm edges after acceptance
  for(p=0;p<32;p=p+1)if(r_k_v[p])begin
   if(ref_w.exists(int'(fold(r_k_addr[30*p+:29]))))begin errors=errors+1;$display("LOCKSTEP reference wrote ordinal %h twice",r_k_addr[30*p+:30]);end
   ref_w[int'(fold(r_k_addr[30*p+:29]))]=r_k_wdata[256*p+:256];
  end
  for(p=0;p<16;p=p+1)if(w_k_v[p]&&w_k_rdy[p])begin
   if(int'(hsh(w_k_addr[30*p+:30]))!=P0+p)begin errors=errors+1;$display("QUADRANT write to sector %h on K port %0d (PC %0d)",w_k_addr[30*p+:30],p,hsh(w_k_addr[30*p+:30]));end
   if(dut_w.exists(int'(w_k_addr[30*p+:30])))begin errors=errors+1;$display("QUADRANT sector %h written twice",w_k_addr[30*p+:30]);end
   dut_w[int'(w_k_addr[30*p+:30])]=w_k_wdata[256*p+:256];
  end
 end
 integer r_posted=0,r_blk=0,ls_win=0;
 always @(negedge stream) if(srst) begin : lockm
  reg[30:0]sp;
  if(wbw_v!==r_wbw_v)begin errors=errors+1;$display("LOCKSTEP wbw_v %b vs master %b at stream edge %0d",wbw_v,r_wbw_v,cur_cycle);end
  if(wbw_v&&r_wbw_v)begin
   ls_win=ls_win+1;
   sp={1'b0,fold(29'(r_wbw_base+30'(r_wbw_total)-30'd1))}-{1'b0,fold(r_wbw_base[28:0])}+31'd1;
   if(wbw_base!==fold(r_wbw_base[28:0])||{19'd0,wbw_total}!==sp)begin
    errors=errors+1;$display("LOCKSTEP window base %h total %0d vs fold(master %h, %0d) = %h, span %0d",wbw_base,wbw_total,r_wbw_base,r_wbw_total,fold(r_wbw_base[28:0]),sp);end
  end
  if(r_wa!=0)r_posted=r_posted+int'(r_wa);
  if(r_fault)begin errors=errors+1;$display("LOCKSTEP master fault");end
 end
 // ---------------------------------------------------------------- group feeds (32 lanes; the other half idle) and controllers
 reg[31:0]g_k_v=0,g_k_we=0,g_kr_rdy=0;reg[959:0]g_k_addr=0;reg[127:0]g_k_len=0;reg[543:0]g_k_tag=0;reg[8191:0]g_k_wdata=0;
 wire[1023:0]g_k_wstrb={1024{1'b1}};
 wire[31:0]g_k_rdy,g_k_wr_done,g_kr_v;wire[543:0]g_kr_tag;wire[127:0]g_kr_beat;wire[8191:0]g_kr_data;
 wire[31:0]c_k_v,c_k_rdy,c_k_we,c_kr_v,c_kr_rdy,c_k_wr_done;wire[959:0]c_k_addr;wire[127:0]c_k_len,c_kr_beat;wire[543:0]c_k_tag,c_kr_tag;
 wire[8191:0]c_k_wdata,c_kr_data;wire[1023:0]c_k_wstrb;
 reg vm_v=0,vm_bank=0;reg[15:0]vm_epoch=0;reg[14:0]vm_row=0;reg[3:0]vm_col=0;
 wire[31:0]fill_v,fill_bank;wire[191:0]fill_slot;wire[511:0]fill_epoch;wire[8191:0]fill_data;wire[3:0]ks_fault;
 // idle half of the controller array (bench only): no requests, responses dropped
 genvar k;
 generate for(k=0;k<8;k=k+1)begin:gks
  if(k/4==QE)begin:q
   localparam integer L=k%4;
   ot_hbm_svc_vm_kshare #(.MUT(KSMUT)) u(.sm(3'(k)),.hbm_clk(hbm),.hbm_rst_n(hrst),.stream_clk(stream),.stream_rst_n(srst),
    .g_k_v(g_k_v[4*k+:4]),.g_k_rdy(g_k_rdy[4*k+:4]),.g_k_addr(g_k_addr[120*k+:120]),.g_k_len(g_k_len[16*k+:16]),.g_k_tag(g_k_tag[68*k+:68]),
    .g_k_we(g_k_we[4*k+:4]),.g_k_wdata(g_k_wdata[1024*k+:1024]),.g_k_wstrb(g_k_wstrb[128*k+:128]),.g_k_wr_done(g_k_wr_done[4*k+:4]),
    .g_kr_v(g_kr_v[4*k+:4]),.g_kr_rdy(g_kr_rdy[4*k+:4]),.g_kr_tag(g_kr_tag[68*k+:68]),.g_kr_beat(g_kr_beat[16*k+:16]),.g_kr_data(g_kr_data[1024*k+:1024]),
    .c_k_v(c_k_v[4*k+:4]),.c_k_rdy(c_k_rdy[4*k+:4]),.c_k_addr(c_k_addr[120*k+:120]),.c_k_len(c_k_len[16*k+:16]),.c_k_tag(c_k_tag[68*k+:68]),
    .c_k_we(c_k_we[4*k+:4]),.c_k_wdata(c_k_wdata[1024*k+:1024]),.c_k_wstrb(c_k_wstrb[128*k+:128]),.c_k_wr_done(c_k_wr_done[4*k+:4]),
    .c_kr_v(c_kr_v[4*k+:4]),.c_kr_rdy(c_kr_rdy[4*k+:4]),.c_kr_tag(c_kr_tag[68*k+:68]),.c_kr_beat(c_kr_beat[16*k+:16]),.c_kr_data(c_kr_data[1024*k+:1024]),
    .vm_v(vm_v),.vm_bank(vm_bank),.vm_epoch(vm_epoch),.vm_row(vm_row),.vm_col(vm_col),
    .wbw_v(wbw_v),.wbw_base(wbw_base),.wbw_total(wbw_total),
    .w_k_v(w_k_v[4*L+:4]),.w_k_rdy(w_k_rdy[4*L+:4]),.w_k_addr(w_k_addr[120*L+:120]),.w_k_wdata(w_k_wdata[1024*L+:1024]),.w_k_wr_done(w_k_wr_done[4*L+:4]),
    .fill_v(fill_v[4*k+:4]),.fill_bank(fill_bank[4*k+:4]),.fill_slot(fill_slot[24*k+:24]),.fill_epoch(fill_epoch[64*k+:64]),.fill_data(fill_data[1024*k+:1024]),
    .fault(ks_fault[L]));
  end else begin:idle
   assign c_k_v[4*k+:4]=0;assign c_k_we[4*k+:4]=0;assign c_k_addr[120*k+:120]=0;assign c_k_len[16*k+:16]=0;assign c_k_tag[68*k+:68]=0;
   assign c_k_wdata[1024*k+:1024]=0;assign c_k_wstrb[128*k+:128]=0;assign c_kr_rdy[4*k+:4]=4'hf;
   assign g_k_rdy[4*k+:4]=0;assign g_k_wr_done[4*k+:4]=0;assign g_kr_v[4*k+:4]=0;assign g_kr_tag[68*k+:68]=0;assign g_kr_beat[16*k+:16]=0;
   assign g_kr_data[1024*k+:1024]=0;assign fill_v[4*k+:4]=0;assign fill_bank[4*k+:4]=0;assign fill_slot[24*k+:24]=0;
   assign fill_epoch[64*k+:64]=0;assign fill_data[1024*k+:1024]=0;
  end
 end endgenerate
 wire[31:0]row_v,col_v,col_we,dram_rvalid;wire[95:0]row_op;wire[159:0]row_bank,col_bank,col_col;wire[607:0]row_row;
 wire[8191:0]col_data,dram_rdata;wire[1023:0]col_strb;wire ctl_fault;
 ot_hbm_svc_native_sector_pipeline_leaves controller(.clk(hbm),.rst_n(hrst),.pc_clk({32{hbm}}),
  .k_v(c_k_v),.k_rdy(c_k_rdy),.k_we(c_k_we),.k_addr(c_k_addr),.k_len(c_k_len),.k_tag(c_k_tag),.k_wdata(c_k_wdata),.k_wstrb(c_k_wstrb),
  .kr_v(c_kr_v),.kr_rdy(c_kr_rdy),.kr_tag(c_kr_tag),.kr_beat(c_kr_beat),.kr_data(c_kr_data),.k_wr_done(c_k_wr_done),
  .row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),
  .col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),.fault(ctl_fault));
 ot_hbm_svc_command_dram_pipeline_fixture #(.K_BASE(K_BASE),.K_MEM(K_MEM)) dram(
  .clk(hbm),.rst_n(hrst),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),
  .col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata));
 // Fail immediately on an observed integrity violation, including in mutant runs.
 always @(negedge stream) if(srst && (errors!=0 || fault_wb || (|ks_fault) || ctl_fault))
  $fatal(1,"WB_INTEGRITY errors=%0d wb=%b kshare=%b controller=%b",errors,fault_wb,ks_fault,ctl_fault);
 // ---------------------------------------------------------------- data images
 function automatic [255:0] fimg(input [29:0] a);
  reg[255:0]r;integer i;begin for(i=0;i<8;i=i+1)r[32*i+:32]=(32'(a)*32'h9e3779b9)^(32'(i)*32'h85ebca6b)^32'h1234_0000;fimg=r;end
 endfunction
 function automatic [255:0] wbimg(input [29:0] a,input [15:0] e);
  reg[255:0]r;integer i;begin for(i=0;i<8;i=i+1)r[32*i+:32]=(32'(a)*32'h7feb352d)^(32'(e)*32'h846ca68b)^(32'(i)*32'h27d4eb2d)^32'h5a5a_0000;wbimg=r;end
 endfunction
 function automatic [255:0] gwimg(input [29:0] a,input integer n);
  reg[255:0]r;integer i;begin for(i=0;i<8;i=i+1)r[32*i+:32]=(32'(a)*32'h165667b1)^(32'(n)*32'hd3a2646c)^(32'(i)*32'hfd7046c5)^32'hc3c3_0000;gwimg=r;end
 endfunction
 function automatic [4:0] hsh(input [29:0] a);hsh=a[6:2]^a[11:7]^a[16:12];endfunction
 function automatic bit inq(input integer p);inq=(p/16)==QE;endfunction
 // ---------------------------------------------------------------- group model (quadrant PCs: reads in [0,0x8000), writes in [0xC000,0x10000))
 integer GN=120,NOWB=0,NOVM=0,NOGW=0;
 integer gi[0:31],grd_done[0:31],gw_iss[0:31],gw_done[0:31],grd_iss[0:31];
 reg[29:0]ga[0:31][0:511];reg[3:0]gl[0:31][0:511];reg[3:0]gs[0:31][0:511];
 logic[255:0]gexp[int];
 always @(posedge hbm) if(hrst) begin : grpm
  integer p,i;reg[29:0]a;reg[3:0]ln;reg[4:0]lo;reg[16:0]t;
  for(p=0;p<32;p=p+1)if(inq(p))begin
   if(g_k_v[p]&&g_k_rdy[p])begin gi[p]=gi[p]+1;g_k_v[p]<=0;end
   if(!(g_k_v[p]&&!g_k_rdy[p])&&gi[p]<GN&&($urandom%3)==0)begin
    if(!NOGW&&($urandom%3)==0)begin
     a=30'(K_BASE)+30'h0C000+30'($urandom%16384);a[1:0]=2'($urandom);a[6:2]=5'(p)^a[11:7]^a[16:12];
     gexp[int'(a)]=gwimg(a,gi[p]+1000*p);gw_iss[p]=gw_iss[p]+1;
     g_k_v[p]<=1;g_k_we[p]<=1;g_k_addr[30*p+:30]<=a;g_k_len[4*p+:4]<=1;g_k_tag[17*p+:17]<=17'(gi[p]);
     g_k_wdata[256*p+:256]<=gwimg(a,gi[p]+1000*p);gl[p][gi[p]]=0;
    end else begin
     ln=4'(1+$urandom%4);lo=5'($urandom%(5-ln));
     a=30'(K_BASE)+30'($urandom%32768);a[1:0]=lo[1:0];a[6:2]=5'(p)^a[11:7]^a[16:12];
     ga[p][gi[p]]=a;gl[p][gi[p]]=ln;gs[p][gi[p]]=0;grd_iss[p]=grd_iss[p]+1;
     g_k_v[p]<=1;g_k_we[p]<=0;g_k_addr[30*p+:30]<=a;g_k_len[4*p+:4]<=ln;g_k_tag[17*p+:17]<=17'(gi[p]);
    end
   end
   g_kr_rdy[p]<=($urandom%4)!=0;
   if(g_k_wr_done[p])gw_done[p]=gw_done[p]+1;
   if(g_kr_v[p]&&g_kr_rdy[p])begin
    t=g_kr_tag[17*p+:17];i=int'(t);
    if(i>=gi[p]||gl[p][i]==0||g_kr_beat[4*p+:4]>=gl[p][i]||gs[p][i][g_kr_beat[4*p+:4]]||
       g_kr_data[256*p+:256]!==fimg(ga[p][i]+30'(g_kr_beat[4*p+:4])))begin
     errors=errors+1;if(errors<12)$display("GROUP pc %0d bad beat tag %0d beat %0d",p,i,g_kr_beat[4*p+:4]);
    end else begin
     gs[p][i][g_kr_beat[4*p+:4]]=1'b1;if(gs[p][i]==((4'b1<<gl[p][i])-1))grd_done[p]=grd_done[p]+1;
    end
   end
  end
 end
 // ---------------------------------------------------------------- VM fill windows (read-only image region)
 integer fills[0:31];reg[63:0]seen[0:31];reg w_bank;reg[15:0]w_epoch;reg[14:0]w_row;reg[3:0]w_col;
 function automatic [29:0] vaddr(input integer pc,input [5:0] slot,input [14:0] row,input [3:0] col);
  reg[3:0]j;reg[4:0]c,h;begin j=slot[5:2];c={col,j[3]};h={row[1:0],j[2:0]};vaddr={row,j[2:0],c,5'(pc)^c^h,2'b00};end
 endfunction
 always @(posedge stream) if(srst) begin : film
  integer p;reg[5:0]s;
  for(p=0;p<32;p=p+1) if(fill_v[p])begin
   s=fill_slot[6*p+:6];
   if(!inq(p)||fill_bank[p]!==w_bank||fill_epoch[16*p+:16]!==w_epoch||seen[p][s]||
      fill_data[256*p+:256]!==fimg(vaddr(p,s,w_row,w_col)+30'(s[1:0])))begin
    errors=errors+1;if(errors<12)$display("VM FILL pc %0d slot %0d bad",p,s);
   end
   seen[p][s]=1;fills[p]=fills[p]+1;
  end
 end
 // ---------------------------------------------------------------- DMA write-back blocks (quadrant ordinals)
 localparam integer NB=8;
 integer boff[0:NB-1],btot[0:NB-1],rdy_ref[0:NB-1],rdy_dut[0:NB-1],rpost[0:NB-1];
 integer posted=0,blk_done=0,fill_at[0:NB-1],fence[0:NB-1];
 always @(posedge stream)cur_cycle=cur_cycle+1;
 always @(posedge stream) if(srst&&wa!=0) begin : wam
  integer s,bad;reg[29:0]o,a;
  posted=posted+int'(wa);
  if(blk_done>=NB||posted>btot[blk_done])begin errors=errors+1;$display("WA over-posted: %0d > block total",posted);end
  else if(posted==btot[blk_done])begin
   bad=0;
   for(s=0;s<btot[blk_done];s=s+1)begin
    o=30'(O_BASE)+30'(boff[blk_done]+s);a=fold(o[28:0]);
    if(dram.mem[int'(a-30'(K_BASE))]!==wbimg(o,16'(16'h300+blk_done)))bad=bad+1;
   end
   if(bad!=0)begin errors=errors+1;$display("BLOCK %0d: %0d of %0d sectors not in DRAM at the completing wa (premature posted count)",blk_done,bad,btot[blk_done]);end
   fence[blk_done]=cur_cycle-fill_at[blk_done];
   posted=0;blk_done=blk_done+1;
  end
 end
 task automatic run_block(input integer b);
  integer r,s,rows;reg[29:0]o;
  begin
   @(negedge stream);rv=1;rb=b[0];fb=b[0];re=16'h300+16'(b);fe=16'h300+16'(b);rt=12'(btot[b]);
   rbase={STK,30'(O_BASE)+30'(boff[b])};
   @(negedge stream);rv=0;
   repeat(12)@(negedge stream);      // drain_at - accept >= 10 (c_lag_ok) + descriptor pipeline
   rdy_dut[b]=wb_ready;rdy_ref[b]=r_ready;
   if(wb_ready!==1'b1||r_ready!==wb_ready)begin errors=errors+1;$display("BLOCK %0d: wb_ready %b (master %b) at the first drain",b,wb_ready,r_ready);end
   rpost[b]=r_posted;
   fs=1;fill_at[b]=cur_cycle;@(negedge stream);fs=0;
   rows=(btot[b]+7)/8;
   for(r=0;r<rows;r=r+1)begin
    wd=0;
    for(s=0;s<8;s=s+1)if(r*8+s<btot[b])begin
     o=30'(O_BASE)+30'(boff[b]+r*8+s);
     wd[289*s+:289]={1'b1,STK,o,wbimg(o,16'(16'h300+b))};
    end
    @(negedge stream);
   end
   wd=0;
  end
 endtask
 integer b,p,t,i,vw,tot;
 initial begin
  boff[0]=32'h4000;btot[0]=640;      // production h block (640 sectors / quadrant / token-layer)
  boff[1]=32'h4280;btot[1]=1;        // production PRE block
  boff[2]=32'h4423;btot[2]=13;
  boff[3]=32'h4505;btot[3]=1984;     // largest quadrant block for any alignment (real span 3968)
  boff[4]=32'h4d3f;btot[4]=1984;
  boff[5]=32'h5500;btot[5]=640;
  boff[6]=32'h57bf;btot[6]=300;
  boff[7]=32'h5a01;btot[7]=1;
  if($value$plusargs("GN=%d",GN));if($test$plusargs("NOWB"))NOWB=1;if($test$plusargs("NOVM"))NOVM=1;if($test$plusargs("NOGW"))NOGW=1;
  for(p=0;p<32;p=p+1)begin gi[p]=inq(p)?0:GN;grd_done[p]=0;gw_iss[p]=0;gw_done[p]=0;grd_iss[p]=0;fills[p]=0;seen[p]=inq(p)?0:'1;end
  for(i=0;i<K_MEM;i=i+1)dram.mem[i]=fimg(30'(K_BASE)+30'(i));
  #(20ns);hrst=1;srst=1;
  repeat(200)@(posedge stream);
  fork
   begin
    for(b=0;b<NB&&!NOWB;b=b+1)begin
     t=0;while(blk_done<b-1&&t<200000)begin @(posedge stream);t=t+1;end
     run_block(b);
     repeat(5+$urandom%40)@(posedge stream);
    end
   end
   begin
    for(vw=0;vw<4&&!NOVM;vw=vw+1)begin
     repeat(150+$urandom%300)@(posedge stream);
     @(negedge stream);
     w_bank=vw[0];w_epoch=16'h700+16'(vw);w_row=15'(K_BASE>>15);w_col=4'($urandom);
     for(p=0;p<32;p=p+1)seen[p]=inq(p)?0:'1;
     vm_v=1;vm_bank=w_bank;vm_epoch=w_epoch;vm_row=w_row;vm_col=w_col;
     @(negedge stream);vm_v=0;
     t=0;while(t<40000)begin
      i=1;for(p=0;p<32;p=p+1)if(!(&seen[p]))i=0;
      if(i)break;
      @(posedge stream);t=t+1;
     end
     if(t>=40000)begin errors=errors+1;$display("VM window %0d timed out",vw);end
    end
   end
  join
  t=0;while(blk_done<NB&&t<200000)begin @(posedge stream);t=t+1;end
  if(blk_done<NB)begin errors=errors+1;$display("only %0d of %0d write-back blocks completed (posted %0d)",blk_done,NB,posted);end
  t=0;
  while(t<100000)begin
   i=1;for(p=0;p<32;p=p+1)if(gi[p]<GN||grd_done[p]!=grd_iss[p]||gw_done[p]!=gw_iss[p])i=0;
   if(i)break;
   @(posedge hbm);t=t+1;
  end
  repeat(100)@(posedge stream);
  for(p=0;p<32;p=p+1)if(inq(p)&&(gi[p]!=GN||grd_done[p]!=grd_iss[p]||gw_done[p]!=gw_iss[p]||fills[p]!=64*4))begin
   errors=errors+1;if(errors<40)$display("pc %0d: issued %0d/%0d reads %0d/%0d writes %0d/%0d fills %0d",p,gi[p],GN,grd_done[p],grd_iss[p],gw_done[p],gw_iss[p],fills[p]);
  end
  begin : gwchk
   int a;i=0;
   foreach(gexp[a])if(dram.mem[a-int'(K_BASE)]!==gexp[a])i=i+1;
   if(i!=0)begin errors=errors+1;$display("%0d group-written sectors differ in DRAM",i);end
  end
  // lockstep: the master's write set (folded) equals the quadrant's, sector for sector, data for data; same posted totals
  tot=0;for(b=0;b<NB;b=b+1)tot=tot+btot[b];
  begin : lsset
   int a;i=0;
   if(ref_w.num()!=tot||dut_w.num()!=tot)begin errors=errors+1;$display("LOCKSTEP write sets: master %0d quadrant %0d expected %0d",ref_w.num(),dut_w.num(),tot);end
   foreach(ref_w[a])if(!dut_w.exists(a)||dut_w[a]!==ref_w[a])i=i+1;
   if(i!=0)begin errors=errors+1;$display("LOCKSTEP %0d folded master sectors differ from the quadrant's writes",i);end
  end
  if(r_posted!=tot)begin errors=errors+1;$display("LOCKSTEP master posted %0d of %0d",r_posted,tot);end
  if(ls_win!=NB)begin errors=errors+1;$display("LOCKSTEP %0d of %0d windows compared",ls_win,NB);end
  if(fault_wb||(|ks_fault)||ctl_fault)begin errors=errors+1;$display("fault: wb_kport_q %b kshare %b controller %b",fault_wb,ks_fault,ctl_fault);end
  for(b=0;b<blk_done;b=b+1)$display("WB_BLOCK %0d ordinals %0d fence_stream_edges %0d",b,btot[b],fence[b]);
  if(errors==0)$display("PASS tb_hbm_svc_wb_kshare_qh QE=%0d KSMUT=%0d WBMUT=%0d WOPEN=%0d blocks=%0d sectors=%0d lockstep_windows=%0d group_req=%0d vm_windows=4",
   QE,KSMUT,WBMUT,WOPEN,NB,tot,ls_win,16*GN);
  else $fatal(1,"FAIL tb_hbm_svc_wb_kshare_qh QE=%0d KSMUT=%0d WBMUT=%0d WOPEN=%0d errors=%0d",QE,KSMUT,WBMUT,WOPEN,errors);
  $finish;
 end
 initial begin #(20ms);$fatal(1,"FAIL timeout blocks %0d posted %0d",blk_done,posted);end
endmodule
`default_nettype wire
