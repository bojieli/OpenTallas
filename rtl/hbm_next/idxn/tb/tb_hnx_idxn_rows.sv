`timescale 1ns/1ps
// HBM-NEXT-UNITS-IDXN 2026-10-19: full-shape N-row IDX.INDEX bench, ONE key stream (fork of rtl/hbm_next/idx/tb/tb_hnx_idx_rows.sv).
// DUT ot_hnx_idxn_scheduled (pipelined row streams + key replay buffers + S time-shared selectors + row-slot link) or, with
// +define+D4G_DUT, the d4g ot_hbm_idx_scheduled_static (N = 1 only) for the bit-for-bit equivalence dump.
// N rows (+ROWS <= 6) of one record: row r reads its query at VM sector 512 r and head weights at 4096 + 8 r (strides +QSTR /
// +WSTR, default 512 / 8). The key-line source answers ONLY the DUT's key_slot edges, and the bench requires exactly 171 of
// them per record (one key stream; rows >= 1 must come from the DUT's replay buffer). Checks per row: all 10,928 scores
// bit-exact vs that row's oracle, the 512 records exactly that row's golden set, 64 flits in sequence at 8-edge spacing,
// row r's first key beat / first TX edge = row 0's compiled edge + r x pitch; no fault.
// Dump (tx_dump.txt): every TX edge (from start) and payload + every score line, for the N = 1 d4g equivalence diff.
// Mutants (+MUT, forced on named DUT wires, one build): 21 replay read on the replay edge (no PRE lookahead), 22 every row
// on selector 0 (selectors not time-shared), 23 link row slots dropped (every row in slot 0); compiler mutants are run
// scripts (+PITCH below the row II, a frame compiled with G2 below the query-reload hazard, +QSTR=0 +WSTR=0).
module tb_hnx_idxn_rows;
 parameter integer N_Q=4,TP=96,RANK=3,NKEYS=10928,MAXR=6,WSEC=4096;
 localparam integer RW=(TP<=1?1:$clog2(TP)),GB=(TP==192?0:1);
 integer frame_rank=RANK,frame_nkeys=NKEYS;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,program_we=0,start=0;reg[7:0]program_addr=0;reg[255:0]program_data=0;reg[11:0]length=0;
 integer rows=1,pitch=0,qstr=512,wstr=8;
 wire[135:0]vm_rq;wire[2055:0]vm_rr;
 reg[2247:0]wr=0;wire[143:0]status;
 wire key_slot;wire[7:0]key_index;reg[8792*N_Q-1:0]key_lines;
 wire[3:0]tx_v;wire[2179:0]tx;wire[610*N_Q-1:0]score_observe;wire done,fault;
 integer mutation=0;
`ifdef D4G_DUT
 ot_hbm_idx_scheduled_static #(.N_Q(N_Q),.TP(TP)) dut(.clk_program(clk),.clk_program_mem(clk),.program_we(program_we),.program_addr(program_addr),
 .program_data(program_data),.start(start),.length(length),
`else
 ot_hnx_idxn_scheduled #(.N_Q(N_Q),.TP(TP)) dut(.clk_program(clk),.clk_program_mem(clk),.program_we(program_we),.program_addr(program_addr),
 .program_data(program_data),.start(start),.length(length),.n_rows(5'(rows)),.row_pitch(12'(pitch)),
 .weight_row_stride(16'(wstr)),.query_row_stride(16'(qstr)),
`endif
 .clk_operand(clk),.clk_query(clk),.clk_quant(clk),.clk_quant_delay(clk),.clk_query_bank({4{clk}}),
 .clk_score({N_Q{clk}}),.clk_engine({(4*N_Q){clk}}),.clk_meta({(4*N_Q){clk}}),.clk_tail({(4*N_Q){clk}}),.clk_chunk({(16*N_Q){clk}}),.clk_hslice({(512*N_Q){clk}}),
 .clk_sel(clk),.clk_sel_q({4{clk}}),.clk_sel_mem({12{clk}}),.clk_link(clk),.clk_link_mem({8{clk}}),.rst_n(rst_n),.sid(2'd0),
 .weight_sector(16'(WSEC)),.query_sector(16'd0),.vm_rq(vm_rq),.vm_rr(vm_rr),.rank(RW'(frame_rank)),.gbase(8'(GB)),.nkeys(14'(frame_nkeys)),
 .keep_en(1'b0),.keep_bitmap({(342*N_Q){1'b0}}),.key_slot(key_slot),.key_index(key_index),.key_lines(key_lines),
 .tx_v(tx_v),.tx(tx),.score_observe(score_observe),.done(done),.fault(fault));
`ifndef D4G_DUT
 initial begin
  if($test$plusargs("MUT21"))begin force dut.parent.kb_pre_v=dut.parent.replay_v;force dut.parent.kb_pre_index=dut.parent.key_index;end
  if($test$plusargs("MUT22"))force dut.calendar.sel_of='0;
  if($test$plusargs("MUT23"))begin force dut.parent.link_in_slot=3'd0;force dut.parent.link_out_slot=3'd0;end
 end
 wire beat_any=dut.kv;wire[4:0]beat_row=dut.kr;
`else
 wire beat_any=key_slot;wire[4:0]beat_row=5'd0;
`endif
 for(genvar b=0;b<8;b=b+1)begin:bank
  wire wd,dqd,kqd,xd,x2d;wire[275:0]eg;wire[265:0]pr;
  ot_vms_bank_static #(.RG(1),.WG(1))mem(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd0),.rslot_v(vm_rq[b*17+16]),.rslot(1'b0),
   .wslot_v(wr[b*281+280]),.wslot(3'd0),.rq(vm_rq[b*17+:17]),.rr(vm_rr[b*257+:257]),.wq(wr[b*281+:281]),.wq_done(wd),
   .dq(281'd0),.dq_done(dqd),.kq(281'd0),.kq_done(kqd),.xq(276'd0),.xq_done(xd),.xq2(276'd0),.xq2_done(x2d),.eg(eg),.pq(285'd0),.pr(pr),.status(status[b*18+:18]));
 end
 reg[1023:0]x[0:128*MAXR-1];reg[511:0]weights[0:MAXR-1];reg[8792*N_Q-1:0]keys[0:170];
 reg[15:0]scores[0:MAXR*NKEYS-1];reg gold[0:MAXR*NKEYS-1],seen[0:MAXR*NKEYS-1];reg[255:0]data;
 reg[31:0]prog[0:2047];
 integer n=0,exp_key=-1,exp_tx=-1,fd;
 integer cycle=0,errors=0,checked=0,records=0,flits=0,firstscore=-1,lastscore=-1,firsttx=-1,lasttx=-1,firstkey=-1,doneedge=-1,tstart=0,faultedge=-1;
 integer rkey[0:15],rtx[0:15],rlasttx[0:15],rchecked[0:15],rrec[0:15],rerr[0:15];
 integer keybeats=0,livebeats=0;
 always @(posedge clk)cycle<=cycle+1;
 always @* begin
  key_lines=0;
  if(key_slot)key_lines=keys[key_index];
 end
 always @(negedge clk)begin
  if(key_slot)livebeats++;
  if(beat_any)begin
   if(firstkey<0)firstkey=cycle;
   if(keybeats%171==0&&keybeats/171<16)rkey[keybeats/171]=cycle-tstart;
   if(int'(beat_row)!=keybeats/171)begin errors++;if(errors<8)$display("BEATROW beat%0d row%0d",keybeats,beat_row);end
   keybeats++;
  end
  if(done&&doneedge<0)doneedge=cycle;
  if(fault===1'b1&&faultedge<0)faultedge=cycle;
  for(integer q=0;q<N_Q;q=q+1)if(score_observe[q*610])begin
   if(firstscore<0)firstscore=cycle;lastscore=cycle;
   $fwrite(fd,"S %0d %0d %h\n",cycle-tstart,q,score_observe[q*610+:610]);
   for(integer l=0;l<16;l=l+1)if(score_observe[q*610+18+l])begin
    integer id,ord,r;id=int'(score_observe[q*610+290+l*20+:20]);ord=(id/(8*TP))*8+id%8;r=checked/frame_nkeys;
    checked++;if(r<16)rchecked[r]++;
    if(r>=rows)begin errors++;if(errors<8)$display("EXTRASCORE row%0d",r);end
    else if((id%(8*TP))/8 != frame_rank)begin errors++;rerr[r]++;if(errors<8)$display("RANKBAD row%0d id%0d",r,id);end
    else if(ord>=frame_nkeys)begin errors++;rerr[r]++;end
    else if(score_observe[q*610+34+l*16+:16]!==scores[r*NKEYS+ord]||score_observe[q*610+2+l])begin errors++;rerr[r]++;
     if(errors<8)$display("SCOREBAD row%0d ord%0d expected%h got%h",r,ord,scores[r*NKEYS+ord],score_observe[q*610+34+l*16+:16]);end
   end
  end
  if(|tx_v)begin
   integer r;r=flits/64;
   $fwrite(fd,"T %0d %h\n",cycle-tstart,tx);
   if(firsttx<0)firsttx=cycle;
   if(flits%64==0&&r<16)rtx[r]=cycle-tstart;
   if(lasttx>=0&&flits%64!=0&&cycle-lasttx!=8)begin errors++;$display("SPACING row%0d edge%0d",r,cycle-tstart);end
   lasttx=cycle;if(r<16)rlasttx[r]=cycle-tstart;
   for(integer l=0;l<4;l=l+1)begin
    if(tx[l*545+512+:16]!==16'((frame_rank-GB)*64+flits%64))begin errors++;if(errors<8)$display("SEQBAD row%0d",r);end flits++;
    for(integer k=0;k<8;k=k+1)begin
     integer id,ord;id=int'(tx[l*545+256+k*32+:32]);ord=(id/(8*TP))*8+id%8;records++;if(r<16)rrec[r]++;
     if(r>=rows||(id%(8*TP))/8 != frame_rank||ord>=frame_nkeys)begin errors++;if(r<16)rerr[r]++;end
     else begin if(!gold[r*NKEYS+ord]||seen[r*NKEYS+ord]||tx[l*545+k*32+:32]!=={scores[r*NKEYS+ord],16'd0})begin errors++;rerr[r]++;
      if(errors<8)$display("TXBAD row%0d edge%0d ord%0d gold%0d seen%0d",r,cycle-tstart,ord,gold[r*NKEYS+ord],seen[r*NKEYS+ord]);end
      seen[r*NKEYS+ord]=1;end
    end
   end
  end
 end
 initial begin
  string dump;
  for(integer i=0;i<16;i=i+1)begin rkey[i]=-1;rtx[i]=-1;rlasttx[i]=-1;rchecked[i]=0;rrec[i]=0;rerr[i]=0;end
  if(!$value$plusargs("N=%d",n))$fatal(1,"need +N=row frame length");
  if($value$plusargs("ROWS=%d",rows))begin end
  if($value$plusargs("PITCH=%d",pitch))begin end
  if($value$plusargs("QSTR=%d",qstr))begin end
  if($value$plusargs("WSTR=%d",wstr))begin end
  if($value$plusargs("MUT=%d",mutation))begin end
  if($value$plusargs("EXP_KEY=%d",exp_key))begin end
  if($value$plusargs("EXP_TX=%d",exp_tx))begin end
  if(!$value$plusargs("DUMP=%s",dump))dump="tx_dump.txt";
  if(rows<1||rows>MAXR)$fatal(1,"rows 1..%0d",MAXR);
  fd=$fopen(dump,"w");
  $readmemh("query.hex",x);$readmemh("weights.hex",weights);$readmemh("keylines.hex",keys);$readmemh("scores.hex",scores);$readmemh("gold.hex",gold);
  for(integer i=0;i<2048;i=i+1)prog[i]=0;
  $readmemh("calendar_instructions.hex",prog);
  for(integer i=0;i<MAXR*NKEYS;i=i+1)seen[i]=0;
  repeat(4)@(negedge clk);rst_n=1;
  // VM: query row r at sectors 512 r .. 512 r + 511 (bank rows 64 r ..), head weights row r at sector WSEC + 8 r (bank row WSEC/8 + r)
  for(integer row=0;row<64*MAXR;row=row+1)begin
   for(integer b=0;b<8;b=b+1)begin
    data=x[(row*8+b)/4][((row*8+b)%4)*256+:256];
    wr[b*281+:281]={1'b1,1'b0,2'd0,10'(row),3'(b),data,8'hff};
   end
   @(negedge clk);
  end
  wr=0;
  for(integer r=0;r<MAXR;r=r+1)begin
   for(integer b=0;b<2;b=b+1)wr[b*281+:281]={1'b1,1'b0,2'd0,10'(WSEC/8+r),3'(b),weights[r][b*256+:256],8'hff};
   @(negedge clk);
  end
  wr=0;
  for(integer row=0;row<(n+7)/8;row=row+1)begin
   program_we=1;program_addr=8'(row);for(integer j=0;j<8;j=j+1)program_data[j*32+:32]=prog[row*8+j];@(negedge clk);
  end
  program_we=0;repeat(8)@(negedge clk);
  length=12'(n);start=1;tstart=cycle;@(negedge clk);start=0;
  repeat(n+(rows-1)*pitch+60)@(negedge clk);
  for(integer r=0;r<rows;r=r+1)for(integer i=0;i<frame_nkeys;i=i+1)if(gold[r*NKEYS+i]!==seen[r*NKEYS+i])begin errors++;rerr[r]++;end
  for(integer r=0;r<rows;r=r+1)begin
   $display("IDX_ROW r%0d firstkey%0d firsttx%0d lasttx%0d scores%0d records%0d errors%0d",r,rkey[r],rtx[r],rlasttx[r],rchecked[r],rrec[r],rerr[r]);
   if(exp_key>=0&&rkey[r]!=exp_key+r*pitch)begin errors++;$display("TIMELINE row%0d first key edge %0d != compiled %0d",r,rkey[r],exp_key+r*pitch);end
   if(exp_tx>=0&&rtx[r]!=exp_tx+r*pitch)begin errors++;$display("TIMELINE row%0d first TX edge %0d != compiled %0d",r,rtx[r],exp_tx+r*pitch);end
  end
  $fclose(fd);
  if(livebeats!=171)begin errors++;$display("KEYSTREAM live key-line deliveries %0d != 171 (one key stream)",livebeats);end
  $display("IDX_ROWS_CYCLES rows%0d pitch%0d frame%0d record_edges_last_tx%0d done%0d live_key_beats%0d scored_beats%0d",rows,pitch,n,lasttx-tstart+1,doneedge-tstart,livebeats,keybeats);
  $display("IDX_HNX_ROWS rows%0d mutation%0d scores%0d records%0d flits%0d errors%0d fault%0d faultedge%0d status%0d",
   rows,mutation,checked,records,flits,errors,fault,faultedge<0?-1:faultedge-tstart,|status);
  if(errors||fault||(|status)||checked!=rows*frame_nkeys||records!=rows*512||flits!=rows*64)$fatal(1,"IDX_HNX_ROWS FAIL: N-row one-key-stream INDEX mismatch");
  $display("IDX_HNX_ROWS PASS");$finish;
 end
endmodule
