`timescale 1ns/1ps
// Full-shape production bench of the pin-registered IDX tiles (H-NETLIST/idxreg 2026-10-16): the real compiler
// program (tools/hbm_idx_static_calendar.py) is loaded into the calendar SRAM of ot_hbm_idx_scheduled_static and
// drives the parent (vm_query / query / 4 scorers / selector / topk link) with no testbench sequencing. Eight real
// VM banks answer the operand face; key lines are delivered on the calendar's key_slot edge. Checks: every one of
// the 10,928 scores bit-exact, the 512 selected records exactly the golden set, 64 flits in sequence, emit beats at
// 8-edge intervals, and the EXACT compiled timeline (first key edge and first TX edge equal the compiler's
// prediction). Mutants (MUT): 1 query index 63->62, 2 one key bit flipped, 3 link flush one edge early.
// A program compiled with '--pins none' (historical unregistered timeline) must fail on the registered tiles.
module tb_idx_scheduled_static;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,program_we=0,start=0;reg[7:0]program_addr=0;reg[255:0]program_data=0;reg[11:0]length=0;
 wire[135:0]vm_rq;wire[2055:0]vm_rr;
 reg[2247:0]wr=0;wire[143:0]status;
 wire key_slot;wire[7:0]key_index;reg[35167:0]key_lines;
 wire[3:0]tx_v;wire[2179:0]tx;wire[2439:0]score_observe;wire done,fault;
 ot_hbm_idx_scheduled_static dut(.clk_program(clk),.clk_program_mem(clk),.program_we(program_we),.program_addr(program_addr),
 .program_data(program_data),.start(start),.length(length),
 .clk_operand(clk),.clk_query(clk),.clk_quant(clk),.clk_quant_delay(clk),.clk_query_bank({4{clk}}),
 .clk_score({4{clk}}),.clk_engine({16{clk}}),.clk_meta({16{clk}}),.clk_tail({16{clk}}),.clk_chunk({64{clk}}),.clk_hslice({2048{clk}}),
 .clk_sel(clk),.clk_sel_q({4{clk}}),.clk_sel_mem({12{clk}}),.clk_link(clk),.clk_link_mem({8{clk}}),.rst_n(rst_n),.sid(2'd0),
 .weight_sector(16'd512),.query_sector(16'd0),.vm_rq(vm_rq),.vm_rr(vm_rr),.rank(7'd3),.gbase(8'd1),.nkeys(14'd10928),
 .keep_en(1'b0),.keep_bitmap(1368'd0),.key_slot(key_slot),.key_index(key_index),.key_lines(key_lines),
 .tx_v(tx_v),.tx(tx),.score_observe(score_observe),.done(done),.fault(fault));
 for(genvar b=0;b<8;b=b+1)begin:bank
  wire wd,dqd,kqd,xd,x2d;wire[275:0]eg;wire[265:0]pr;
  ot_vms_bank_static #(.RG(1),.WG(1))mem(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd0),.rslot_v(vm_rq[b*17+16]),.rslot(1'b0),
   .wslot_v(wr[b*281+280]),.wslot(3'd0),.rq(vm_rq[b*17+:17]),.rr(vm_rr[b*257+:257]),.wq(wr[b*281+:281]),.wq_done(wd),
   .dq(281'd0),.dq_done(dqd),.kq(281'd0),.kq_done(kqd),.xq(276'd0),.xq_done(xd),.xq2(276'd0),.xq2_done(x2d),.eg(eg),.pq(285'd0),.pr(pr),.status(status[b*18+:18]));
 end
 reg[1023:0]x[0:127];reg[511:0]weights[0:0];reg[35167:0]keys[0:170];reg[15:0]scores[0:10927];reg gold[0:10927],seen[0:10927];reg[255:0]data;
 reg[31:0]prog[0:2047];
 integer mutation=0,n=0,exp_key=-1,exp_tx=-1;
 integer cycle=0,errors=0,checked=0,records=0,flits=0,firstscore=-1,lastscore=-1,firsttx=-1,lasttx=-1,firstkey=-1,doneedge=-1,tstart=0;
 always @(posedge clk)cycle<=cycle+1;
 always @* begin
  key_lines=0;
  if(key_slot)begin key_lines=keys[key_index];if(mutation==2&&key_index==128)key_lines[11]=~key_lines[11];end
 end
 always @(negedge clk)begin
  if(key_slot&&firstkey<0)firstkey=cycle;
  if(done&&doneedge<0)doneedge=cycle;
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
 initial begin
  if(!$value$plusargs("N=%d",n))$fatal(1,"need +N=program length");
  if($value$plusargs("MUT=%d",mutation))begin end
  if($value$plusargs("EXP_KEY=%d",exp_key))begin end
  if($value$plusargs("EXP_TX=%d",exp_tx))begin end
  $readmemh("query.hex",x);$readmemh("weights.hex",weights);$readmemh("keylines.hex",keys);$readmemh("scores.hex",scores);$readmemh("gold.hex",gold);
  for(integer i=0;i<2048;i=i+1)prog[i]=0;
  $readmemh("calendar_instructions.hex",prog);
  if(mutation==1)for(integer i=0;i<n;i=i+1)if(prog[i][30]&&prog[i][26:20]==7'd63)prog[i][26:20]=7'd62;
  if(mutation==3)begin:m3
   integer f;f=-1;for(integer i=0;i<n;i=i+1)if(prog[i][5])f=i;
   prog[f][5]=1'b0;prog[f-1][5]=1'b1;
  end
  for(integer i=0;i<10928;i=i+1)seen[i]=0;
  repeat(4)@(negedge clk);rst_n=1;
  // explicit initialization: query/weight operands into the real VM banks, programme rows into the calendar SRAM
  for(integer row=0;row<64;row=row+1)begin
   for(integer b=0;b<8;b=b+1)begin
    data=x[(row*8+b)/4][((row*8+b)%4)*256+:256];
    wr[b*281+:281]={1'b1,1'b0,2'd0,10'(row),3'(b),data,8'hff};
   end
   program_we=row<(n+7)/8;program_addr=8'(row);
   for(integer j=0;j<8;j=j+1)program_data[j*32+:32]=prog[row*8+j];
   @(negedge clk);
  end
  program_we=0;wr=0;
  for(integer row=64;row<(n+7)/8;row=row+1)begin
   program_we=1;program_addr=8'(row);for(integer j=0;j<8;j=j+1)program_data[j*32+:32]=prog[row*8+j];@(negedge clk);
  end
  program_we=0;
  for(integer b=0;b<2;b=b+1)wr[b*281+:281]={1'b1,1'b0,2'd0,10'd64,3'(b),weights[0][b*256+:256],8'hff};
  @(negedge clk);wr=0;repeat(8)@(negedge clk);
  length=12'(n);start=1;tstart=cycle;@(negedge clk);start=0;
  repeat(n+40)@(negedge clk);
  for(integer i=0;i<10928;i=i+1)if(gold[i]!==seen[i])errors++;
  $display("IDX_SCHEDULED_STATIC N%0d mutation%0d scores%0d records%0d flits%0d errors%0d fault%0d status%0d firstkey%0d firstscore%0d lastscore%0d firsttx%0d lasttx%0d done%0d (edges from start; expected key%0d tx%0d)",
   n,mutation,checked,records,flits,errors,fault,|status,firstkey-tstart,firstscore-tstart,lastscore-tstart,firsttx-tstart,lasttx-tstart,doneedge-tstart,exp_key,exp_tx);
  if(exp_key>=0&&firstkey-tstart!=exp_key)begin errors++;$display("TIMELINE first key edge %0d != compiled %0d",firstkey-tstart,exp_key);end
  if(exp_tx>=0&&firsttx-tstart!=exp_tx)begin errors++;$display("TIMELINE first TX edge %0d != compiled %0d",firsttx-tstart,exp_tx);end
  if(errors||fault||(|status)||checked!=10928||records!=512||flits!=64)$fatal(1,"fullshape scheduled INDEX (pin-registered tiles) mismatch");
  $display("IDX_SCHEDULED_STATIC PASS");$finish;
 end
endmodule
