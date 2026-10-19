`timescale 1ns/1ps
// HBM-NEXT-UNITS IDXQ 2026-10-19: lockstep of the IDXN per-quadrant client ot_hnx_idxq_client_quad against the IDXN
// stack-scorer client ot_hnx_idxn_scheduled (N_Q=2, TP=192, OT_IDX_SCORE_CLUSTER = the die's chained 16-leaf cluster),
// N query rows over ONE key stream, on IDENTICAL stimulus: the same IDXN row frame source (old --score-chain 8, new
// 8 + CHAIN, CHAIN 6 = quarter pins 2 + XQ tree 4), the same n_rows / pitch / operand row strides, the same VM image
// (one copy per quadrant VM: query row r at sectors 512 r.., head weights row r at WSEC + 8 r), the same key lines (stack
// s, PCs 4H..4H+3 to quadrant (s,H)), delivered ONLY on each design's row-0 key_slot edges (171 per record).
// Checks on EVERY edge, against the old design delayed by the documented latency: row-0 service beats and the beats
// of every row (+2, all 4 quadrants identical), every score field of every lane (+4), every TX flit (+2 + CHAIN),
// done (+2 + CHAIN: done is the frame's last instruction, and the new frame is CHAIN edges longer), no fault in either. The old design is also checked against the exact oracle (hnx_idxq_vectors.py): every
// score of every row and every row's 512 records (golden set, score payload), 64 flits per row.
// Mutants (one build; new design only): +MUT=2 key bit flip on the live beat 100, +MUT=3 quadrant halves swapped on
// the key lines, +MUT=4 quadrant 1 replay buffer bypassed (replay_v forced 0), +MUT=6 link row slots dropped, +MUT=7
// every row on selector 0, +MUT=8 quadrant 2 calendar copy at pitch + 1; compiler mutant: new programme --score-chain 13.
module tb_hnx_idxq_lockstep;
 parameter integer TP=192,RANK=191,NKEYS=5456,CHAIN=6,MAXR=6,WSEC=4096;
 localparam integer RW=$clog2(TP),GB=(TP==192?0:1),DK=2,DS=4,DTX=2+CHAIN,DD=2+CHAIN;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start=0;reg[7:0]paddr=0;reg[255:0]pdo=0,pdn=0;reg[11:0]len_o=0,len_n=0;
 integer frame_rank=RANK,frame_nkeys=NKEYS,rows=1,pitch=0,qstr=512,wstr=8,mutation=0;
 reg pwe_o=0,pwe_n=0;
 // ---------------- old design (IDXN stack scorers)
 wire[135:0]vrq_o;wire[2055:0]vrr_o;wire ks_o;wire[7:0]ki_o;reg[2*8792-1:0]kl_o;
 wire[3:0]txv_o;wire[2179:0]tx_o;wire[2*610-1:0]so_o;wire done_o,fault_o;
 ot_hnx_idxn_scheduled #(.N_Q(2),.TP(TP)) old(.clk_program(clk),.clk_program_mem(clk),.program_we(pwe_o),.program_addr(paddr),
 .program_data(pdo),.start(start),.length(len_o),.n_rows(5'(rows)),.row_pitch(12'(pitch)),
 .weight_row_stride(16'(wstr)),.query_row_stride(16'(qstr)),
 .clk_operand(clk),.clk_query(clk),.clk_quant(clk),.clk_quant_delay(clk),.clk_query_bank({4{clk}}),
 .clk_score({2{clk}}),.clk_engine({8{clk}}),.clk_meta({8{clk}}),.clk_tail({8{clk}}),.clk_chunk({32{clk}}),.clk_hslice({1024{clk}}),
 .clk_sel(clk),.clk_sel_q({4{clk}}),.clk_sel_mem({12{clk}}),.clk_link(clk),.clk_link_mem({8{clk}}),.rst_n(rst_n),.sid(2'd0),
 .weight_sector(16'(WSEC)),.query_sector(16'd0),.vm_rq(vrq_o),.vm_rr(vrr_o),.rank(RW'(frame_rank)),.gbase(8'(GB)),.nkeys(14'(frame_nkeys)),
 .keep_en(1'b0),.keep_bitmap({684{1'b0}}),.key_slot(ks_o),.key_index(ki_o),.key_lines(kl_o),
 .tx_v(txv_o),.tx(tx_o),.score_observe(so_o),.done(done_o),.fault(fault_o));
 // ---------------- new design (IDXN per-quadrant)
 wire[135:0]vrq_n;wire[2055:0]vrr_n;wire[3*136-1:0]vrq_q;wire[3*2056-1:0]vrr_q;wire[3:0]ks_n;wire[31:0]ki_n;reg[2*8792-1:0]kl_n;
 wire[3:0]txv_n;wire[2179:0]tx_n;wire[4*306-1:0]so_n;wire done_n,fault_n;
 wire[337:0]cq;wire[1:0]cq_seq;wire tb_busy,tk_done,tk_fault,share_fault;wire[2055:0]amr;
 ot_hnx_idxq_client_quad #(.TP(TP),.QS(4'b1100),.QH(4'b1010)) dut(.clk_program(clk),.clk_program_mem(clk),
 .clk_qprog({4{clk}}),.clk_qprog_mem({4{clk}}),.program_we(pwe_n),.program_addr(paddr),.program_data(pdn),.start(start),.length(len_n),
 .n_rows(5'(rows)),.row_pitch(12'(pitch)),.weight_row_stride(16'(wstr)),.query_row_stride(16'(qstr)),
 .clk_operand({4{clk}}),.clk_query({4{clk}}),.clk_quant({4{clk}}),.clk_quant_delay({4{clk}}),.clk_query_bank({16{clk}}),
 .clk_kb({4{clk}}),.clk_score({4{clk}}),.clk_engine({8{clk}}),.clk_meta({8{clk}}),.clk_tail({8{clk}}),.clk_chunk({32{clk}}),.clk_hslice({1024{clk}}),.clk_xq({3{clk}}),
 .clk_sel(clk),.clk_sel_q({4{clk}}),.clk_sel_mem({12{clk}}),.clk_link(clk),.clk_link_mem({8{clk}}),.clk_pair({4{clk}}),.clk_topk(clk),.rst_n(rst_n),
 .weight_sector(16'(WSEC)),.query_sector(16'd0),.vm_rq(vrq_n),.vm_rr(vrr_n),.vm_rq_q(vrq_q),.vm_rr_q(vrr_q),
 .rank(RW'(frame_rank)),.gbase(8'(GB)),.nkeys(14'(frame_nkeys)),.keep_en(1'b0),.keep_bitmap({684{1'b0}}),
 .key_slot(ks_n),.key_index(ki_n),.key_lines(kl_n),.tx_v(txv_n),.tx(tx_n),.score_observe(so_n),.done(done_n),.fault(fault_n),
 .topk_go(1'b0),.topk_k(4'd0),.topk_order(1'b0),.topk_n(20'd0),.topk_m(20'd0),.topk_a_mirror(1'b0),.topk_a_base(18'd0),.topk_a_str(18'd0),
 .topk_o_mirror(1'b0),.topk_o_base(18'd0),.topk_o_str(18'd0),.topk_has_r(1'b0),.topk_r_base(18'd0),.topk_r_str(18'd0),
 .cq(cq),.cq_seq(cq_seq),.cr(274'd0),.topk_busy(tb_busy),.topk_done(tk_done),.topk_fault(tk_fault),.share_fault(share_fault),
 .argmax_rq(136'd0),.argmax_rr(amr));
 // ---------------- mutants (forced on named wires of the new design)
 initial begin
  if($value$plusargs("MUT=%d",mutation))begin end
  if($value$plusargs("PITCH=%d",pitch))begin end
  if(mutation==4)force dut.gq[1].replay_v=1'b0;
  if(mutation==6)begin force dut.link_in_slot=3'd0;force dut.link_out_slot=3'd0;end
  if(mutation==7)force dut.ctl.calendar.sel_of='0;
  if(mutation==8)force dut.gq[2].ctl.pi_r=12'(pitch+1);
 end
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
 reg[1023:0]x[0:128*MAXR-1];reg[511:0]weights[0:MAXR-1];reg[2*8792-1:0]keys[0:170];reg[31:0]progo[0:2047],progn[0:2047];reg[255:0]data;
 reg[15:0]scores[0:MAXR*NKEYS-1];reg gold[0:MAXR*NKEYS-1],seen[0:MAXR*NKEYS-1];
 integer no=0,nn=0;
 always @* begin
  kl_o=0;if(ks_o)kl_o=keys[ki_o];
  kl_n=0;if(ks_n[0])kl_n=keys[ki_n[0+:8]];
  if(mutation==2&&ks_n[0]&&ki_n[0+:8]==8'd100)kl_n[2*8792-100]=~kl_n[2*8792-100];
  if(mutation==3)for(integer s=0;s<2;s=s+1)begin reg[4395:0]t;t=kl_n[s*8792+:4396];kl_n[s*8792+:4396]=kl_n[s*8792+4396+:4396];kl_n[s*8792+4396+:4396]=t;end
 end
 // ---------------- lockstep: old outputs delayed by the documented latency (d[i] = i+1 edges ago at negedge)
 localparam integer DMAX=16;
 wire kv_o=old.kv;wire[4:0]kr_o=old.kr;wire kv_n=dut.gq[0].kv;wire[4:0]kr_n=dut.gq[0].kr;
 reg[2*610-1:0]so_d[0:DMAX];reg[3:0]txv_d[0:DMAX];reg[2179:0]tx_d[0:DMAX];reg ks_d[0:DMAX],kv_d[0:DMAX],done_d[0:DMAX];reg[7:0]ki_d[0:DMAX];reg[4:0]kr_d[0:DMAX];
 integer cyc=0,errors=0,oerr=0,scores_n=0,flits_n=0,beats_o=0,beats_n=0,live_o=0,live_n=0,tstart=0,ftx_o=-1,ftx_n=-1,fk_o=-1,fk_n=-1,dn_o=-1,dn_n=-1;
 integer checked=0,records=0,flits_o=0;
 always @(posedge clk)begin
  cyc<=cyc+1;
  so_d[0]<=so_o;txv_d[0]<=txv_o;tx_d[0]<=tx_o;ks_d[0]<=ks_o;ki_d[0]<=ki_o;kv_d[0]<=kv_o;kr_d[0]<=kr_o;done_d[0]<=done_o;
  for(integer i=1;i<=DMAX;i=i+1)begin so_d[i]<=so_d[i-1];txv_d[i]<=txv_d[i-1];tx_d[i]<=tx_d[i-1];ks_d[i]<=ks_d[i-1];ki_d[i]<=ki_d[i-1];
   kv_d[i]<=kv_d[i-1];kr_d[i]<=kr_d[i-1];done_d[i]<=done_d[i-1];end
 end
 always @(negedge clk)if(rst_n)begin
  if(ks_o)live_o++; if(ks_n[0])live_n++; if(kv_o)beats_o++; if(kv_n)beats_n++;
  if(ks_o&&fk_o<0)fk_o=cyc; if(ks_n[0]&&fk_n<0)fk_n=cyc;
  if(|txv_o&&ftx_o<0)ftx_o=cyc; if(|txv_n&&ftx_n<0)ftx_n=cyc;
  if(done_o&&dn_o<0)dn_o=cyc; if(done_n&&dn_n<0)dn_n=cyc;
  // key beats: service (row 0) and every row's scorer beat, 4 quadrants identical
  if(ks_n!={4{ks_n[0]}}||ki_n!={4{ki_n[0+:8]}})begin errors++;if(errors<8)$display("QBEAT disagree cyc%0d",cyc);end
  if(ks_n[0]!==ks_d[DK-1]||(ks_n[0]&&ki_n[0+:8]!==ki_d[DK-1]))begin errors++;if(errors<8)$display("BEATBAD cyc%0d",cyc);end
  if(kv_n!==kv_d[DK-1]||(kv_n&&kr_n!==kr_d[DK-1]))begin errors++;if(errors<8)$display("ROWBEATBAD cyc%0d new%b/%0d old%b/%0d",cyc,kv_n,kr_n,kv_d[DK-1],kr_d[DK-1]);end
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
     if(n[10+l])scores_n++;
    end
   end
  end
  // TX flits and done
  if(txv_n!==txv_d[DTX-1]||(|txv_n&&tx_n!==tx_d[DTX-1]))begin errors++;if(errors<12)$display("TXBAD cyc%0d new%b old%b",cyc,txv_n,txv_d[DTX-1]);end
  for(integer l=0;l<4;l=l+1)if(txv_n[l])flits_n++;
  if(done_n!==done_d[DD-1])begin errors++;if(errors<12)$display("DONEBAD cyc%0d",cyc);end
  // exact oracle on the old design: scores of every row
  for(integer q=0;q<2;q=q+1)if(so_o[q*610])for(integer l=0;l<16;l=l+1)if(so_o[q*610+18+l])begin
   integer id,ord,r;id=int'(so_o[q*610+290+l*20+:20]);ord=(id/(8*TP))*8+id%8;r=checked/frame_nkeys;checked++;
   if(r>=rows||(id%(8*TP))/8!=frame_rank||ord>=frame_nkeys)begin oerr++;if(oerr<8)$display("ORACLE extra/rank row%0d id%0d",r,id);end
   else if(so_o[q*610+34+l*16+:16]!==scores[r*NKEYS+ord]||so_o[q*610+2+l])begin oerr++;
    if(oerr<8)$display("ORACLE SCOREBAD row%0d ord%0d expected%h got%h",r,ord,scores[r*NKEYS+ord],so_o[q*610+34+l*16+:16]);end
  end
  // exact oracle on the old design: each row's 512 records
  if(|txv_o)for(integer l=0;l<4;l=l+1)begin
   integer r;r=flits_o/64;
   if(tx_o[l*545+512+:16]!==16'((frame_rank-GB)*64+flits_o%64))begin oerr++;if(oerr<8)$display("ORACLE SEQBAD row%0d",r);end
   flits_o++;
   for(integer k=0;k<8;k=k+1)begin
    integer id,ord;id=int'(tx_o[l*545+256+k*32+:32]);ord=(id/(8*TP))*8+id%8;records++;
    if(r>=rows||(id%(8*TP))/8!=frame_rank||ord>=frame_nkeys)oerr++;
    else begin
     if(!gold[r*NKEYS+ord]||seen[r*NKEYS+ord]||tx_o[l*545+k*32+:32]!=={scores[r*NKEYS+ord],16'd0})begin oerr++;
      if(oerr<8)$display("ORACLE TXBAD row%0d ord%0d gold%0d seen%0d",r,ord,gold[r*NKEYS+ord],seen[r*NKEYS+ord]);end
     seen[r*NKEYS+ord]=1;
    end
   end
  end
 end
 initial begin
  integer nko;
  if(!$value$plusargs("NO=%d",no))$fatal(1,"+NO");if(!$value$plusargs("NN=%d",nn))$fatal(1,"+NN");
  if($value$plusargs("ROWS=%d",rows))begin end
  if($value$plusargs("QSTR=%d",qstr))begin end
  if($value$plusargs("WSTR=%d",wstr))begin end
  if(rows<1||rows>MAXR)$fatal(1,"rows 1..%0d",MAXR);
  $readmemh("query.hex",x);$readmemh("weights.hex",weights);$readmemh("keylines.hex",keys);$readmemh("scores.hex",scores);$readmemh("gold.hex",gold);
  for(integer i=0;i<MAXR*NKEYS;i=i+1)seen[i]=0;
  for(integer i=0;i<2048;i=i+1)begin progo[i]=0;progn[i]=0;end
  $readmemh("cal_old.hex",progo);$readmemh("cal_new.hex",progn);
  repeat(4)@(negedge clk);rst_n=1;repeat(4)@(negedge clk);
  for(integer row=0;row<64*MAXR;row=row+1)begin
   for(integer b=0;b<8;b=b+1)begin data=x[(row*8+b)/4][((row*8+b)%4)*256+:256];wr[b*281+:281]={1'b1,1'b0,2'd0,10'(row),3'(b),data,8'hff};end
   @(negedge clk);
  end
  wr=0;
  for(integer r=0;r<MAXR;r=r+1)begin
   for(integer b=0;b<2;b=b+1)wr[b*281+:281]={1'b1,1'b0,2'd0,10'(WSEC/8+r),3'(b),weights[r][b*256+:256],8'hff};
   @(negedge clk);
  end
  wr=0;
  for(integer row=0;row<256;row=row+1)begin
   pwe_o=row<(no+7)/8;pwe_n=row<(nn+7)/8;paddr=8'(row);
   for(integer j=0;j<8;j=j+1)begin pdo[j*32+:32]=progo[row*8+j];pdn[j*32+:32]=progn[row*8+j];end
   @(negedge clk);
  end
  pwe_o=0;pwe_n=0;repeat(8)@(negedge clk);
  len_o=12'(no);len_n=12'(nn);start=1;tstart=cyc;@(negedge clk);start=0;
  repeat((no>nn?no:nn)+(rows-1)*pitch+60)@(negedge clk);
  for(integer r=0;r<rows;r=r+1)for(integer i=0;i<frame_nkeys;i=i+1)if(gold[r*NKEYS+i]!==seen[r*NKEYS+i])oerr++;
  $display("IDXQ_LOCKSTEP rows%0d pitch%0d chainNew%0d mut%0d errors%0d oracle_errors%0d scores_new%0d scores_old%0d records_old%0d flits_new%0d flits_old%0d live_beats old%0d new%0d row_beats old%0d new%0d fault_old%0d fault_new%0d status%0d | edges from start: key old%0d new%0d tx old%0d new%0d done old%0d new%0d",
   rows,pitch,CHAIN,mutation,errors,oerr,scores_n,checked,records,flits_n,flits_o,live_o,live_n,beats_o,beats_n,fault_o,fault_n,|status,
   fk_o-tstart,fk_n-tstart,ftx_o-tstart,ftx_n-tstart,dn_o-tstart,dn_n-tstart);
  $display("IDXQ_ROWS_CYCLES rows%0d pitch%0d new_done_edge%0d old_done_edge%0d",rows,pitch,dn_n-tstart,dn_o-tstart);
  if(errors||oerr||fault_o||fault_n||(|status)||scores_n!=rows*frame_nkeys||checked!=rows*frame_nkeys||records!=rows*512||
     flits_n!=rows*64||live_o!=171||live_n!=171||beats_o!=rows*171||beats_n!=rows*171)
   $fatal(1,"IDXQ_LOCKSTEP FAIL: IDXN quad vs stack mismatch");
  $display("IDXQ_LOCKSTEP PASS");$finish;
 end
endmodule
