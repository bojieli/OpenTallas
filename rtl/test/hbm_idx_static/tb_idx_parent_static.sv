`timescale 1ns/1ps
module tb_idx_parent_static;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,weight_slot=0,query_slot=0;reg[6:0]query_index=0;
 reg[15:0]weight_sector=512,query_sector=0;
 wire[135:0]vm_rq;wire[2055:0]vm_rr;wire block_v;wire[4:0]block_head;wire[1:0]block_number;
 wire[1023:0]block_data;wire[15:0]head_weight;wire operand_fault;
 reg[2247:0]wr=0;wire[143:0]status;
 reg frame_start=0,query_emit=0;reg[4:0]query_emit_head=0;
 reg beat_v=0;reg[7:0]beat_index=0;reg[35167:0]key_lines=0;
 reg[3:0]sel_op=0;reg[1:0]sel_pass=0;reg[7:0]sel_addr=0;
 reg link_flush=0,link_emit=0;reg[3:0]link_group=0;
 wire[3:0]tx_v;wire[2179:0]tx;wire[2439:0]score_observe;wire fault;
 ot_hbm_idx_parent_static dut(.clk_operand(clk),.clk_query(clk),.clk_quant(clk),.clk_quant_delay(clk),.clk_query_bank({4{clk}}),
 .clk_score({4{clk}}),.clk_engine({16{clk}}),.clk_meta({16{clk}}),.clk_tail({16{clk}}),.clk_chunk({64{clk}}),.clk_hslice({2048{clk}}),
 .clk_sel(clk),.clk_sel_q({4{clk}}),.clk_sel_mem({12{clk}}),.clk_link(clk),.clk_link_mem({8{clk}}),.rst_n(rst_n),.sid(2'd0),
 .frame_start(frame_start),.weight_slot(weight_slot),.query_slot(query_slot),.query_index(query_index),.weight_sector(weight_sector),.query_sector(query_sector),
 .vm_rq(vm_rq),.vm_rr(vm_rr),.query_emit(query_emit),.query_emit_head(query_emit_head),.rank(7'd3),.gbase(8'd1),.nkeys(14'd10928),.keep_en(1'b0),.keep_bitmap(1368'd0),
 .beat_v(beat_v),.beat_index(beat_index),.key_lines(key_lines),.sel_op(sel_op),.sel_pass(sel_pass),.sel_addr(sel_addr),
 .link_flush(link_flush),.link_emit(link_emit),.link_group(link_group),.tx_v(tx_v),.tx(tx),.score_observe(score_observe),.fault(fault));
 for(genvar b=0;b<8;b=b+1)begin:bank
  wire done,dqd,kqd,xd,x2d;wire[275:0]eg;wire[265:0]pr;
  ot_vms_bank_static #(.RG(1),.WG(1))mem(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd0),.rslot_v(vm_rq[b*17+16]),.rslot(1'b0),
   .wslot_v(wr[b*281+280]),.wslot(3'd0),.rq(vm_rq[b*17+:17]),.rr(vm_rr[b*257+:257]),.wq(wr[b*281+:281]),.wq_done(done),
   .dq(281'd0),.dq_done(dqd),.kq(281'd0),.kq_done(kqd),.xq(276'd0),.xq_done(xd),.xq2(276'd0),.xq2_done(x2d),.eg(eg),.pq(285'd0),.pr(pr),.status(status[b*18+:18]));
 end
 reg[1023:0]x[0:127];reg[511:0]weights[0:0];reg[35167:0]keys[0:170];reg[15:0]scores[0:10927];reg gold[0:10927],seen[0:10927];reg[255:0]data;
 integer cycle=0,errors=0,checked=0,records=0,flits=0,firstscore=-1,lastscore=-1,firsttx=-1,lasttx=-1,scanstart;
 always @(posedge clk)cycle<=cycle+1;
 always @(negedge clk)begin
  for(integer q=0;q<4;q=q+1)if(score_observe[q*610])begin
   if(firstscore<0)firstscore=cycle;lastscore=cycle;
   for(integer l=0;l<16;l=l+1)if(score_observe[q*610+18+l])begin
    integer id,ord;id=int'(score_observe[q*610+290+l*20+:20]);ord=(id/768)*8+id%8;
    checked++;
    if(ord>=10928)errors++;
    else if(score_observe[q*610+34+l*16+:16]!==scores[ord]||score_observe[q*610+2+l])begin errors++;if(errors<8)$display("SCOREBAD ord%0d expected%h got%h",ord,scores[ord],score_observe[q*610+34+l*16+:16]);end
   end
  end
  if(|tx_v)begin
   if(firsttx<0)firsttx=cycle;
   if(lasttx>=0&&cycle-lasttx!=8)errors++;
   lasttx=cycle;
   for(integer l=0;l<4;l=l+1)begin
    if(tx[l*545+512+:16]!==16'(128+flits))errors++;flits++;
    for(integer r=0;r<8;r=r+1)begin
     integer id,ord;id=int'(tx[l*545+256+r*32+:32]);ord=(id/768)*8+id%8;records++;
     if(ord>=10928)errors++;
     else begin if(!gold[ord]||seen[ord]||tx[l*545+r*32+:32]!=={scores[ord],16'd0})errors++;seen[ord]=1;end
    end
   end
  end
 end
 task automatic tick(input integer o,input integer a,input integer p);
  begin @(negedge clk);sel_op=4'(o);sel_addr=8'(a);sel_pass=2'(p);end
 endtask
 initial begin
  $readmemh("query.hex",x);$readmemh("weights.hex",weights);$readmemh("keylines.hex",keys);$readmemh("scores.hex",scores);$readmemh("gold.hex",gold);
  for(integer i=0;i<10928;i=i+1)seen[i]=0;
  repeat(4)@(negedge clk);rst_n=1;frame_start=1;sel_op=1;
  @(negedge clk);frame_start=0;sel_op=0;
  for(integer row=0;row<64;row=row+1)begin
   for(integer b=0;b<8;b=b+1)begin
    data=x[(row*8+b)/4][((row*8+b)%4)*256+:256];
    wr[b*281+:281]={1'b1,1'b0,2'd0,10'(row),3'(b),data,8'hff};
   end
   @(negedge clk);
  end
  wr=0;
  for(integer b=0;b<2;b=b+1)wr[b*281+:281]={1'b1,1'b0,2'd0,10'd64,3'(b),weights[0][b*256+:256],8'hff};
  @(negedge clk);wr=0;repeat(8)@(negedge clk);
  weight_slot=1;@(negedge clk);weight_slot=0;repeat(16)@(negedge clk);
  for(integer q=0;q<128;q=q+1)begin query_slot=1;query_index=7'(q);@(negedge clk);end
  query_slot=0;repeat(28)@(negedge clk);
  for(integer h=0;h<32;h=h+1)begin query_emit=1;query_emit_head=5'(h);@(negedge clk);end
  query_emit=0;repeat(100)@(negedge clk);
  sel_op=3;@(negedge clk);sel_op=0;scanstart=cycle;
  for(integer t=0;t<294;t=t+1)begin
   beat_v=t<171;beat_index=8'(t);if(t<171)key_lines=keys[t];
   sel_op=(t>=123)?2:0;sel_addr=8'(t-123);
   @(negedge clk);
  end
  beat_v=0;sel_op=0;tick(0,0,0);tick(0,0,0);
  for(integer b=31;b>=0;b=b-1)tick(5,b,0);
  tick(0,0,0);
  for(integer p=1;p<3;p=p+1)begin
   tick(3,0,p);for(integer a=0;a<171;a=a+1)tick(4,a,p);
   tick(0,0,p);tick(0,0,p);
   for(integer b=(p==2?63:31);b>=0;b=b-1)tick(5,b,p);
   tick(0,0,p);
  end
  for(integer a=0;a<171;a=a+1)tick(6,a,2);
  tick(0,0,2);tick(0,0,2);link_flush=1;tick(0,0,2);link_flush=0;
  for(integer a=0;a<16;a=a+1)begin link_emit=1;link_group=4'(a);tick(0,0,2);link_emit=0;repeat(7)tick(0,0,2);end
  repeat(4)tick(0,0,2);
  for(integer i=0;i<10928;i=i+1)if(gold[i]!==seen[i])errors++;
  $display("IDX_PARENT_STATIC scores%0d records%0d flits%0d errors%0d fault%0d scoreedges%0d..%0d TXedges%0d..%0d",checked,records,flits,errors,fault,firstscore-scanstart,lastscore-scanstart,firsttx-scanstart,lasttx-scanstart);
  if(errors||fault||checked!=10928||records!=512||flits!=64)$fatal(1,"fullshape real static INDEX parent mismatch");$finish;
 end
endmodule
