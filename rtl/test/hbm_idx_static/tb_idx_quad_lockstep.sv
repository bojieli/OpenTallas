`timescale 1ns/1ps
// HBM-B-RTL2 IDX lockstep (2026-10-17): today's stack-scorer client ot_hbm_idx_scheduled_static (N_Q=2, TP=192:
// calendar + vm_query + query + 2 x ot_hbm_idx_score_static + selector + topk link) against the d4g per-quadrant
// client ot_hbm_idx_client_static_quad (4 quadrant calendars/operand readers/query units/quarter scorers, registered
// XQ tree, root ctl, the same selector/link), on IDENTICAL stimulus: the same compiler programme source
// (old: --score-chain 8 = its 16-leaf cluster chain; new: 8 + CHAIN, CHAIN = 6 = quarter pins 2 + XQ tree 4), the same VM operand image (one copy per quadrant VM), the same key
// lines (stack s, PCs 4H..4H+3 to quadrant (s,H)). Checks on EVERY edge, against the old design delayed by the
// documented latency: key beats (+2, all 4 quadrant beats identical), every score field of every lane (+4), every
// TX flit (+DTX = 2 + CHAIN), done (+2), no fault in either; plus the old design's own golden counts.
module tb_idx_quad_lockstep;
 parameter integer TP=192,RANK=191,NKEYS=5472,CHAIN=6,QSWAP=0;
 localparam integer RW=$clog2(TP),GB=(TP==192?0:1),DK=2,DS=4,DTX=2+CHAIN,DD=2;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,pwe=0,start=0;reg[7:0]paddr=0;reg[255:0]pdo=0,pdn=0;reg[11:0]len_o=0,len_n=0;
 integer frame_rank=RANK,frame_nkeys=NKEYS;
 // ---------------- old design
 wire[135:0]vrq_o;wire[2055:0]vrr_o;wire ks_o;wire[7:0]ki_o;reg[2*8792-1:0]kl_o;
 wire[3:0]txv_o;wire[2179:0]tx_o;wire[2*610-1:0]so_o;wire done_o,fault_o;
 reg pwe_o=0,pwe_n=0;
 ot_hbm_idx_scheduled_static #(.N_Q(2),.TP(TP)) old(.clk_program(clk),.clk_program_mem(clk),.program_we(pwe_o),.program_addr(paddr),
 .program_data(pdo),.start(start),.length(len_o),
 .clk_operand(clk),.clk_query(clk),.clk_quant(clk),.clk_quant_delay(clk),.clk_query_bank({4{clk}}),
 .clk_score({2{clk}}),.clk_engine({8{clk}}),.clk_meta({8{clk}}),.clk_tail({8{clk}}),.clk_chunk({32{clk}}),.clk_hslice({1024{clk}}),
 .clk_sel(clk),.clk_sel_q({4{clk}}),.clk_sel_mem({12{clk}}),.clk_link(clk),.clk_link_mem({8{clk}}),.rst_n(rst_n),.sid(2'd0),
 .weight_sector(16'd512),.query_sector(16'd0),.vm_rq(vrq_o),.vm_rr(vrr_o),.rank(RW'(frame_rank)),.gbase(8'(GB)),.nkeys(14'(frame_nkeys)),
 .keep_en(1'b0),.keep_bitmap({684{1'b0}}),.key_slot(ks_o),.key_index(ki_o),.key_lines(kl_o),
 .tx_v(txv_o),.tx(tx_o),.score_observe(so_o),.done(done_o),.fault(fault_o));
 // ---------------- new design
 wire[135:0]vrq_n;wire[2055:0]vrr_n;wire[3*136-1:0]vrq_q;wire[3*2056-1:0]vrr_q;wire[3:0]ks_n;wire[31:0]ki_n;reg[2*8792-1:0]kl_n;
 wire[3:0]txv_n;wire[2179:0]tx_n;wire[4*306-1:0]so_n;wire done_n,fault_n;
 wire[337:0]cq;wire[1:0]cq_seq;wire tb_busy,tk_done,tk_fault,share_fault;wire[2055:0]amr;
 ot_hbm_idx_client_static_quad #(.TP(TP),.QS(4'b1100),.QH(QSWAP?4'b0101:4'b1010)) dut(.clk_program(clk),.clk_program_mem(clk),
 .clk_qprog({4{clk}}),.clk_qprog_mem({4{clk}}),.program_we(pwe_n),.program_addr(paddr),.program_data(pdn),.start(start),.length(len_n),
 .clk_operand({4{clk}}),.clk_query({4{clk}}),.clk_quant({4{clk}}),.clk_quant_delay({4{clk}}),.clk_query_bank({16{clk}}),
 .clk_score({4{clk}}),.clk_engine({8{clk}}),.clk_meta({8{clk}}),.clk_tail({8{clk}}),.clk_chunk({32{clk}}),.clk_hslice({1024{clk}}),.clk_xq({3{clk}}),
 .clk_sel(clk),.clk_sel_q({4{clk}}),.clk_sel_mem({12{clk}}),.clk_link(clk),.clk_link_mem({8{clk}}),.clk_pair({4{clk}}),.clk_topk(clk),.rst_n(rst_n),
 .weight_sector(16'd512),.query_sector(16'd0),.vm_rq(vrq_n),.vm_rr(vrr_n),.vm_rq_q(vrq_q),.vm_rr_q(vrr_q),
 .rank(RW'(frame_rank)),.gbase(8'(GB)),.nkeys(14'(frame_nkeys)),.keep_en(1'b0),.keep_bitmap({684{1'b0}}),
 .key_slot(ks_n),.key_index(ki_n),.key_lines(kl_n),.tx_v(txv_n),.tx(tx_n),.score_observe(so_n),.done(done_n),.fault(fault_n),
 .topk_go(1'b0),.topk_k(4'd0),.topk_order(1'b0),.topk_n(20'd0),.topk_m(20'd0),.topk_a_mirror(1'b0),.topk_a_base(18'd0),.topk_a_str(18'd0),
 .topk_o_mirror(1'b0),.topk_o_base(18'd0),.topk_o_str(18'd0),.topk_has_r(1'b0),.topk_r_base(18'd0),.topk_r_str(18'd0),
 .cq(cq),.cq_seq(cq_seq),.cr(274'd0),.topk_busy(tb_busy),.topk_done(tk_done),.topk_fault(tk_fault),.share_fault(share_fault),
 .argmax_rq(136'd0),.argmax_rr(amr));
 // ---------------- VMs: old 1, new 4 (quadrant 0 through the SW share), identical images
 reg[2247:0]wr=0;wire[18*8*5-1:0]status;
 for(genvar v=0;v<5;v=v+1)begin:vm
  wire[135:0]rq=(v==0)?vrq_o:(v==1)?vrq_n:vrq_q[(v-2)*136+:136];
  wire[2055:0]rr;
  if(v==0)begin:a assign vrr_o=rr;end else if(v==1)begin:b assign vrr_n=rr;end else begin:c assign vrr_q[(v-2)*2056+:2056]=rr;end
  for(genvar b=0;b<8;b=b+1)begin:bank
   wire wd,dqd,kqd,xd,x2d;wire[275:0]eg;wire[265:0]pr;
   ot_vms_bank_static #(.RG(1),.WG(1))mem(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd0),.rslot_v(rq[b*17+16]),.rslot(1'b0),
    .wslot_v(wr[b*281+280]),.wslot(3'd0),.rq(rq[b*17+:17]),.rr(rr[b*257+:257]),.wq(wr[b*281+:281]),.wq_done(wd),
    .dq(281'd0),.dq_done(dqd),.kq(281'd0),.kq_done(kqd),.xq(276'd0),.xq_done(xd),.xq2(276'd0),.xq2_done(x2d),.eg(eg),.pq(285'd0),.pr(pr),.status(status[(v*8+b)*18+:18]));
  end
 end
 reg[1023:0]x[0:127];reg[511:0]weights[0:0];reg[2*8792-1:0]keys[0:170];reg[31:0]progo[0:2047],progn[0:2047];reg[255:0]data;
 integer no=0,nn=0,mutation=0;
 always @* begin kl_o=0;if(ks_o)kl_o=keys[ki_o]; kl_n=0;if(ks_n[0])kl_n=keys[ki_n[0+:8]];
  if(mutation==2&&ks_n[0]&&ki_n[0+:8]==8'd100)kl_n[2*8792-100]=~kl_n[2*8792-100]; end
 // ---------------- lockstep checks: old outputs delayed by the documented latency
 localparam integer DMAX=16;
 reg[2*610-1:0]so_d[0:DMAX];reg[3:0]txv_d[0:DMAX];reg[2179:0]tx_d[0:DMAX];reg ks_d[0:DMAX];reg[7:0]ki_d[0:DMAX];reg done_d[0:DMAX];
 integer cyc=0,errors=0,scores=0,flits=0,beats=0,tstart=0,ftx_o=-1,ftx_n=-1,fk_o=-1,fk_n=-1,fs_o=-1,fs_n=-1,dn_o=-1,dn_n=-1;
 always @(posedge clk)begin
  cyc<=cyc+1;
  so_d[0]<=so_o;txv_d[0]<=txv_o;tx_d[0]<=tx_o;ks_d[0]<=ks_o;ki_d[0]<=ki_o;done_d[0]<=done_o;
  for(integer i=1;i<=DMAX;i=i+1)begin so_d[i]<=so_d[i-1];txv_d[i]<=txv_d[i-1];tx_d[i]<=tx_d[i-1];ks_d[i]<=ks_d[i-1];ki_d[i]<=ki_d[i-1];done_d[i]<=done_d[i-1];end
 end
 // so_d[i] = so_o of i+1 edges ago (sampled at negedge below): a delay of D edges is so_d[D-1]
 always @(negedge clk)if(rst_n)begin
  if(ks_o&&fk_o<0)fk_o=cyc; if(ks_n[0]&&fk_n<0)fk_n=cyc;
  if(so_o[0]&&fs_o<0)fs_o=cyc; if(so_n[0]&&fs_n<0)fs_n=cyc;
  if(|txv_o&&ftx_o<0)ftx_o=cyc; if(|txv_n&&ftx_n<0)ftx_n=cyc;
  if(done_o&&dn_o<0)dn_o=cyc; if(done_n&&dn_n<0)dn_n=cyc;
  // key beats
  if(ks_n!={4{ks_n[0]}}||ki_n!={4{ki_n[0+:8]}})begin errors++;if(errors<8)$display("QBEAT disagree cyc%0d",cyc);end
  if(ks_n[0]!==ks_d[DK-1]||(ks_n[0]&&ki_n[0+:8]!==ki_d[DK-1]))begin errors++;if(errors<8)$display("BEATBAD cyc%0d",cyc);end
  if(ks_n[0])beats++;
  // scores: quarter (s,h) lanes = stack scorer s lanes 8h..8h+7
  for(integer q=0;q<4;q=q+1)begin:sq
   integer s,h;reg[609:0]o;reg[305:0]n;
   s=q/2;h=q%2;o=so_d[DS-1][s*610+:610];n=so_n[q*306+:306];
   if(n[0]!==o[0])begin errors++;if(errors<8)$display("EVBAD cyc%0d q%0d new%b old%b",cyc,q,n[0],o[0]);end
   else if(o[0])begin
    if(n[1]!==o[1])errors++;
    for(integer l=0;l<8;l=l+1)begin
     if(n[146+l*20+:20]!==o[290+(8*h+l)*20+:20]||n[18+l*16+:16]!==o[34+(8*h+l)*16+:16]||n[10+l]!==o[18+8*h+l]||n[2+l]!==o[2+8*h+l])begin
      errors++;if(errors<8)$display("SCOREBAD cyc%0d q%0d lane%0d new{%h %h %b} old{%h %h %b}",cyc,q,l,n[146+l*20+:20],n[18+l*16+:16],n[10+l],o[290+(8*h+l)*20+:20],o[34+(8*h+l)*16+:16],o[18+8*h+l]);end
     if(o[18+8*h+l])scores++;
    end
   end
  end
  // TX flits
  if(txv_n!==txv_d[DTX-1]||(|txv_n&&tx_n!==tx_d[DTX-1]))begin errors++;if(errors<12)$display("TXBAD cyc%0d new%b old%b",cyc,txv_n,txv_d[DTX-1]);end
  for(integer l=0;l<4;l=l+1)if(txv_n[l])flits++;
  if(done_n!==done_d[DD-1])begin errors++;if(errors<12)$display("DONEBAD cyc%0d",cyc);end
 end
 initial begin
  if($value$plusargs("MUT=%d",mutation))begin end
  if(!$value$plusargs("NO=%d",no))$fatal(1,"+NO");if(!$value$plusargs("NN=%d",nn))$fatal(1,"+NN");
  $readmemh("query.hex",x);$readmemh("weights.hex",weights);$readmemh("keylines.hex",keys);
  for(integer i=0;i<2048;i=i+1)begin progo[i]=0;progn[i]=0;end
  $readmemh("cal_old.hex",progo);$readmemh("cal_new.hex",progn);
  repeat(4)@(negedge clk);rst_n=1;repeat(4)@(negedge clk);
  for(integer row=0;row<256;row=row+1)begin
   if(row<64)for(integer b=0;b<8;b=b+1)begin data=x[(row*8+b)/4][((row*8+b)%4)*256+:256];wr[b*281+:281]={1'b1,1'b0,2'd0,10'(row),3'(b),data,8'hff};end
   else wr=0;
   pwe_o=row<(no+7)/8;pwe_n=row<(nn+7)/8;paddr=8'(row);
   for(integer j=0;j<8;j=j+1)begin pdo[j*32+:32]=progo[row*8+j];pdn[j*32+:32]=progn[row*8+j];end
   @(negedge clk);
  end
  pwe_o=0;pwe_n=0;wr=0;
  for(integer b=0;b<2;b=b+1)wr[b*281+:281]={1'b1,1'b0,2'd0,10'd64,3'(b),weights[0][b*256+:256],8'hff};
  @(negedge clk);wr=0;repeat(8)@(negedge clk);
  len_o=12'(no);len_n=12'(nn);start=1;tstart=cyc;@(negedge clk);start=0;
  repeat((no>nn?no:nn)+60)@(negedge clk);
  $display("IDX_QUAD_LOCKSTEP chain%0d qswap%0d mut%0d errors%0d scores%0d flits%0d beats%0d fault_old%0d fault_new%0d status%0d | edges from start: key old%0d new%0d score old%0d new%0d tx old%0d new%0d done old%0d new%0d",
   CHAIN,QSWAP,mutation,errors,scores,flits,beats,fault_o,fault_n,|status,fk_o-tstart,fk_n-tstart,fs_o-tstart,fs_n-tstart,ftx_o-tstart,ftx_n-tstart,dn_o-tstart,dn_n-tstart);
  if(errors||fault_o||fault_n||(|status)||scores!=frame_nkeys||flits!=64||ftx_o<0)$fatal(1,"IDX quad lockstep MISMATCH");
  $display("IDX_QUAD_LOCKSTEP PASS");$finish;
 end
endmodule
