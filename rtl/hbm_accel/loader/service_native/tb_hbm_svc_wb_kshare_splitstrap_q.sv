`timescale 1ps/1fs
`default_nettype none
// H-NETLIST/dmawb 2026-10-16: one quadrant's DMA write-back path through the v16 die leaves:
//   DMA write-back pins (driven exactly as ot_hgi_dma_back_static_vp4_banks drives them: reserve at descriptor accept,
//   fill start = compiled drain edge + 1, eight sectors per stream edge {v, {stk,sector}, data}, wb_ready sampled once
//   at the first drain, wa = posted count)
//   -> ot_hbm_svc_wb_kport (pin regs + ot_hbm_svc_wb_cutthrough_cdc + receipts + WB window command)
//   -> 8 x ot_hbm_svc_vm_kshare (SM=0..7; WB write windows sharing the K ports with the SM group read/write feeds and
//      with VM fill windows)
//   -> ot_hbm_svc_native_sector_pipeline_leaves (32 real ot_hbm_svc_pc_ctrl_leaf controllers)
//   -> ot_hbm_svc_command_dram_pipeline_fixture (off-chip DRAM at the PHY row/column boundary, timing-checked).
// Checks: at each block's first wa that completes it, every sector of the block is already in DRAM with its data
// (bit-exact, true completion); wb_ready = 1 at every first drain; group reads return the DRAM image beat-exact, group
// writes all complete and land; VM fill windows deliver 64 exact slots per PC; no fault anywhere; DRAM command timing
// legal (fixture $fatal).  Reports the K-port window time per lane per block (hbm edges) and the DMA fence (stream edges
// from fill start to the completing wa).
// Params: KSMUT (kshare MUT), WBMUT (wb_kport MUT), WOPEN.  Exit: "PASS" line, else "FAIL".
module tb_hbm_svc_wb_kshare_splitstrap_q;
 parameter integer KSMUT=0, WBMUT=0, WOPEN=0;
 localparam [31:0] K_BASE=32'h28800000;localparam integer K_MEM=65536;localparam [1:0] STK=2'd2;
 reg hbm=0,stream=0,hrst=0,srst=0;
 always #512 hbm=~hbm;
 always #416.667 stream=~stream;
 // ---------------------------------------------------------------- DMA-side pins
 reg rv=0,rb=0,fb=0,fs=0;reg[15:0]re=0,fe=0;reg[11:0]rt=0;reg[31:0]rbase=0;reg[2311:0]wd=0;
 wire wb_ready,fault_wb;wire[11:0]wa;wire wbw_v;wire[29:0]wbw_base;wire[11:0]wbw_total;
 wire[31:0]w_k_v,w_k_rdy,w_k_wr_done;wire[959:0]w_k_addr;wire[8191:0]w_k_wdata;
 ot_hbm_svc_wb_kport #(.WOPEN(WOPEN),.MUT(WBMUT)) u_wbp(.stream_clk(stream),.stream_rst_n(srst),.hbm_clk(hbm),.hbm_rst_n(hrst),
  .stream_fifo_clk({4{stream}}),.stk(STK),
  .wb_reserve_v(rv),.wb_reserve_bank(rb),.wb_fill_bank(fb),.wb_reserve_epoch(re),.wb_fill_epoch(fe),.wb_reserve_sectors(rt),
  .wb_reserve_base(rbase),.wb_fill_start(fs),.wd(wd),.wb_ready(wb_ready),.wa(wa),
  .wbw_v(wbw_v),.wbw_base(wbw_base),.wbw_total(wbw_total),
  .w_k_v(w_k_v),.w_k_rdy(w_k_rdy),.w_k_addr(w_k_addr),.w_k_wdata(w_k_wdata),.w_k_wr_done(w_k_wr_done),.fault(fault_wb));
 // ---------------------------------------------------------------- group feeds (32 lanes) and controllers
 reg[31:0]g_k_v=0,g_k_we=0,g_kr_rdy=0;reg[959:0]g_k_addr=0;reg[127:0]g_k_len=0;reg[543:0]g_k_tag=0;reg[8191:0]g_k_wdata=0;
 wire[1023:0]g_k_wstrb={1024{1'b1}};
 wire[31:0]g_k_rdy,g_k_wr_done,g_kr_v;wire[543:0]g_kr_tag;wire[127:0]g_kr_beat;wire[8191:0]g_kr_data;
 wire[31:0]c_k_v,c_k_rdy,c_k_we,c_kr_v,c_kr_rdy,c_k_wr_done;wire[959:0]c_k_addr;wire[127:0]c_k_len,c_kr_beat;wire[543:0]c_k_tag,c_kr_tag;
 wire[8191:0]c_k_wdata,c_kr_data;wire[1023:0]c_k_wstrb;
 reg vm_v=0,vm_bank=0;reg[15:0]vm_epoch=0;reg[14:0]vm_row=0;reg[3:0]vm_col=0;
 wire[31:0]fill_v,fill_bank;wire[191:0]fill_slot;wire[511:0]fill_epoch;wire[8191:0]fill_data;wire[7:0]ks_fault;
 genvar k;
 generate for(k=0;k<8;k=k+1)begin:gks
  ot_hbm_svc_vm_kshare_splitstrap #(.MUT(KSMUT)) u(.sm_stream(3'(k)),.sm_hbm(3'(k)),.hbm_clk(hbm),.hbm_rst_n(hrst),.stream_clk(stream),.stream_rst_n(srst),
   .g_k_v(g_k_v[4*k+:4]),.g_k_rdy(g_k_rdy[4*k+:4]),.g_k_addr(g_k_addr[120*k+:120]),.g_k_len(g_k_len[16*k+:16]),.g_k_tag(g_k_tag[68*k+:68]),
   .g_k_we(g_k_we[4*k+:4]),.g_k_wdata(g_k_wdata[1024*k+:1024]),.g_k_wstrb(g_k_wstrb[128*k+:128]),.g_k_wr_done(g_k_wr_done[4*k+:4]),
   .g_kr_v(g_kr_v[4*k+:4]),.g_kr_rdy(g_kr_rdy[4*k+:4]),.g_kr_tag(g_kr_tag[68*k+:68]),.g_kr_beat(g_kr_beat[16*k+:16]),.g_kr_data(g_kr_data[1024*k+:1024]),
   .c_k_v(c_k_v[4*k+:4]),.c_k_rdy(c_k_rdy[4*k+:4]),.c_k_addr(c_k_addr[120*k+:120]),.c_k_len(c_k_len[16*k+:16]),.c_k_tag(c_k_tag[68*k+:68]),
   .c_k_we(c_k_we[4*k+:4]),.c_k_wdata(c_k_wdata[1024*k+:1024]),.c_k_wstrb(c_k_wstrb[128*k+:128]),.c_k_wr_done(c_k_wr_done[4*k+:4]),
   .c_kr_v(c_kr_v[4*k+:4]),.c_kr_rdy(c_kr_rdy[4*k+:4]),.c_kr_tag(c_kr_tag[68*k+:68]),.c_kr_beat(c_kr_beat[16*k+:16]),.c_kr_data(c_kr_data[1024*k+:1024]),
   .vm_v(vm_v),.vm_bank(vm_bank),.vm_epoch(vm_epoch),.vm_row(vm_row),.vm_col(vm_col),
   .wbw_v(wbw_v),.wbw_base(wbw_base),.wbw_total(wbw_total),
   .w_k_v(w_k_v[4*k+:4]),.w_k_rdy(w_k_rdy[4*k+:4]),.w_k_addr(w_k_addr[120*k+:120]),.w_k_wdata(w_k_wdata[1024*k+:1024]),.w_k_wr_done(w_k_wr_done[4*k+:4]),
   .fill_v(fill_v[4*k+:4]),.fill_bank(fill_bank[4*k+:4]),.fill_slot(fill_slot[24*k+:24]),.fill_epoch(fill_epoch[64*k+:64]),.fill_data(fill_data[1024*k+:1024]),
   .fault(ks_fault[k]));
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
`ifdef TRACE_PC
 localparam integer TP=`TRACE_PC;
 always @(posedge hbm) begin
  if(c_k_v[TP]&&c_k_rdy[TP])
   $display("KTP cyc%0d we%0d addr %h len%0d st%0d",dram.cyc,c_k_we[TP],c_k_addr[30*TP+:30],c_k_len[4*TP+:4],gks[TP/4].u.lane[TP%4].st);
  if(row_v[TP])$display("ROWTP cyc%0d op%0d bank%0d row%h",dram.cyc,row_op[3*TP+:3],row_bank[5*TP+:5],row_row[19*TP+:19]);
  if(col_v[TP])$display("COLTP cyc%0d we%0d bank%0d col%0d",dram.cyc,col_we[TP],col_bank[5*TP+:5],col_col[5*TP+:5]);
 end
`endif
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
 integer errors=0;
 // ---------------------------------------------------------------- group model (random reads in [0,0x8000), writes in [0xC000,0x10000))
 integer GN=120,NOWB=0,NOVM=0,NOGW=0;
 integer gi[0:31],grd_done[0:31],gw_iss[0:31],gw_done[0:31],grd_iss[0:31];
 reg[29:0]ga[0:31][0:511];reg[3:0]gl[0:31][0:511];reg[3:0]gs[0:31][0:511];
 logic[255:0]gexp[int];
 always @(posedge hbm) if(hrst) begin : grpm
  integer p,i;reg[29:0]a;reg[3:0]ln;reg[4:0]lo;reg[16:0]t;
  for(p=0;p<32;p=p+1)begin
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
   if(fill_bank[p]!==w_bank||fill_epoch[16*p+:16]!==w_epoch||seen[p][s]||
      fill_data[256*p+:256]!==fimg(vaddr(p,s,w_row,w_col)+30'(s[1:0])))begin
    errors=errors+1;if(errors<12)$display("VM FILL pc %0d slot %0d bad",p,s);
   end
   seen[p][s]=1;fills[p]=fills[p]+1;
  end
 end
 // ---------------------------------------------------------------- window time per lane (K port held by the WB window)
 integer wcyc[0:31],wmax_blk[0:31];integer cur_blk_win[0:31];
 generate for(k=0;k<32;k=k+1)begin:gmon
  wire[2:0]st=gks[k/4].u.lane[k%4].st;
  always @(posedge hbm)begin
   if(st==3'd4||st==3'd5)begin wcyc[k]=wcyc[k]+1;cur_blk_win[k]=cur_blk_win[k]+1;end
  end
 end endgenerate
 // ---------------------------------------------------------------- DMA write-back blocks
 localparam integer NB=7;
 integer boff[0:NB-1],btot[0:NB-1];
 integer posted=0,blk_done=0,cur_cycle=0,fill_at[0:NB-1],fence[0:NB-1],winmax[0:NB-1],winsum[0:NB-1];
 always @(posedge stream)cur_cycle=cur_cycle+1;
 // wa monitor: blocks complete in order
 always @(posedge stream) if(srst&&wa!=0) begin : wam
  integer s,bad,p;reg[29:0]a;
  posted=posted+int'(wa);
  if(blk_done>=NB||posted>btot[blk_done])begin errors=errors+1;$display("WA over-posted: %0d > block total",posted);end
  else if(posted==btot[blk_done])begin
   bad=0;
   for(s=0;s<btot[blk_done];s=s+1)begin
    a=30'(K_BASE)+30'(boff[blk_done]+s);
    if(dram.mem[int'(a-30'(K_BASE))]!==wbimg(a,16'(16'h300+blk_done)))bad=bad+1;
   end
   if(bad!=0)begin errors=errors+1;$display("BLOCK %0d: %0d of %0d sectors not in DRAM at the completing wa (premature posted count)",blk_done,bad,btot[blk_done]);end
   fence[blk_done]=cur_cycle-fill_at[blk_done];
   winmax[blk_done]=0;winsum[blk_done]=0;
   for(p=0;p<32;p=p+1)begin if(cur_blk_win[p]>winmax[blk_done])winmax[blk_done]=cur_blk_win[p];winsum[blk_done]=winsum[blk_done]+cur_blk_win[p];cur_blk_win[p]=0;end
   posted=0;blk_done=blk_done+1;
  end
 end
 task automatic run_block(input integer b);
  integer r,s,rows;reg[29:0]a;
  begin
   // reserve (descriptor accept edge); the DMA drives fill bank/epoch with the reservation
   @(negedge stream);rv=1;rb=b[0];fb=b[0];re=16'h300+16'(b);fe=16'h300+16'(b);rt=12'(btot[b]);
   rbase={STK,30'(K_BASE)+30'(boff[b])};
   @(negedge stream);rv=0;
   repeat(12)@(negedge stream);      // drain_at - accept >= 10 (c_lag_ok) + descriptor pipeline
   if(wb_ready!==1'b1)begin errors=errors+1;$display("BLOCK %0d: wb_ready low at the first drain",b);end
   fs=1;fill_at[b]=cur_cycle;@(negedge stream);fs=0;
   rows=(btot[b]+7)/8;
   for(r=0;r<rows;r=r+1)begin
    wd=0;
    for(s=0;s<8;s=s+1)if(r*8+s<btot[b])begin
     a=30'(K_BASE)+30'(boff[b]+r*8+s);
     wd[289*s+:289]={1'b1,STK,a,wbimg(a,16'(16'h300+b))};
    end
    @(negedge stream);
   end
   wd=0;
  end
 endtask
 integer b,p,t,i,vw;
 initial begin
  boff[0]=32'h8000;btot[0]=640;      // production h block (640 sectors / quadrant / token-layer)
  boff[1]=32'h8280;btot[1]=1;        // production PRE block
  boff[2]=32'h8423;btot[2]=13;
  boff[3]=32'h8505;btot[3]=2048;
  boff[4]=32'h9000;btot[4]=640;
  boff[5]=32'hA07f;btot[5]=300;
  boff[6]=32'hB001;btot[6]=1;
  if($value$plusargs("GN=%d",GN));if($test$plusargs("NOWB"))NOWB=1;if($test$plusargs("NOVM"))NOVM=1;if($test$plusargs("NOGW"))NOGW=1;
  for(p=0;p<32;p=p+1)begin gi[p]=0;grd_done[p]=0;gw_iss[p]=0;gw_done[p]=0;grd_iss[p]=0;fills[p]=0;seen[p]=0;wcyc[p]=0;cur_blk_win[p]=0;end
  for(i=0;i<K_MEM;i=i+1)dram.mem[i]=fimg(30'(K_BASE)+30'(i));
  #(20ns);hrst=1;srst=1;
  repeat(200)@(posedge stream);
  fork
   begin // DMA: block b+1 reserved after block b's fill, once block b-1 has returned its buffer
    for(b=0;b<NB&&!NOWB;b=b+1)begin
     t=0;while(blk_done<b-1&&t<200000)begin @(posedge stream);t=t+1;end
     run_block(b);
     repeat(5+$urandom%40)@(posedge stream);
    end
   end
   begin // VM fill windows interleaved
    for(vw=0;vw<4&&!NOVM;vw=vw+1)begin
     repeat(150+$urandom%300)@(posedge stream);
     @(negedge stream);
     w_bank=vw[0];w_epoch=16'h700+16'(vw);w_row=15'(K_BASE>>15);w_col=4'($urandom);
     for(p=0;p<32;p=p+1)seen[p]=0;
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
  for(p=0;p<32;p=p+1)if(gi[p]!=GN||grd_done[p]!=grd_iss[p]||gw_done[p]!=gw_iss[p]||fills[p]!=64*4)begin
   errors=errors+1;if(errors<40)$display("pc %0d: issued %0d/%0d reads %0d/%0d writes %0d/%0d fills %0d",p,gi[p],GN,grd_done[p],grd_iss[p],gw_done[p],gw_iss[p],fills[p]);
  end
  begin : gwchk
   int a;i=0;
   foreach(gexp[a])if(dram.mem[a-int'(K_BASE)]!==gexp[a])i=i+1;
   if(i!=0)begin errors=errors+1;$display("%0d group-written sectors differ in DRAM",i);end
  end
  if(fault_wb||(|ks_fault)||ctl_fault)begin errors=errors+1;$display("fault: wb_kport %b kshare %b controller %b",fault_wb,ks_fault,ctl_fault);end
  for(b=0;b<blk_done;b=b+1)$display("WB_BLOCK %0d sectors %0d fence_stream_edges %0d window_hbm_edges max %0d mean %0d",
   b,btot[b],fence[b],winmax[b],winsum[b]/32);
  if(errors==0)$display("PASS tb_hbm_svc_wb_kshare_splitstrap_q KSMUT=%0d WBMUT=%0d WOPEN=%0d blocks=%0d group_req=%0d vm_windows=4",KSMUT,WBMUT,WOPEN,NB,32*GN);
  else $fatal(1,"FAIL tb_hbm_svc_wb_kshare_splitstrap_q KSMUT=%0d WBMUT=%0d WOPEN=%0d errors=%0d",KSMUT,WBMUT,WOPEN,errors);
  $finish;
 end
 initial begin #(20ms);$fatal(1,"FAIL timeout blocks %0d posted %0d",blk_done,posted);end
endmodule
`default_nettype wire
