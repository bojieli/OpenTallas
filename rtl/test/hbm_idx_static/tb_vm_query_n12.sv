`timescale 1ns/1ps
// HBM-IDXAM3 2026-10-18: bench of the uniform n+12 operand-reader MASTER ot_hbm_idx_vm_query_static_n12 (the
// pin-registered die tile, not the core) on the actual VM banks (ot_vms_bank_static) with the die's two fixed
// edges outside the tile: one relay stage on vm_rq and one on vm_rr (= the registered share's index_rq / vm_rr
// pin flops on SW, the H-D4G relays on SE/NW/NE). Downstream: the unchanged query/quant core.
// MUT 0 pass; 1 weight word, 2 query word, 3 query index (data mutants of tb_vm_query_static);
// 4 vm_rr relay removed (n+11), 5 extra vm_rr relay (n+13), 6 the n+10 master on the n+12 path, 7 vm_rq relay removed.
module tb_vm_query_n12;
 parameter integer MUT=0, PERIOD=1;
 localparam integer RQ_RLY=(MUT==7)?0:1, RR_RLY=(MUT==4)?0:(MUT==5)?2:1;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,weight_slot=0,query_slot=0;reg[6:0]query_index=0;
 reg[15:0]weight_sector=512,query_sector=0;
 wire[135:0]vm_rq;wire[2055:0]vm_rr;wire block_v;wire[4:0]block_head;wire[1:0]block_number;
 wire[1023:0]block_data;wire[15:0]head_weight;wire operand_fault;
 wire[135:0]bank_rq;wire[2055:0]bank_rr;
 reg[2247:0]wr=0;wire[143:0]status;
 generate if(MUT==6)begin:g_old
  ot_hbm_idx_vm_query_static operand(.clk(clk),.rst_n(rst_n),.sid(2'd0),.weight_slot(weight_slot),.query_slot(query_slot),.query_index(query_index),
   .weight_sector(weight_sector),.query_sector(query_sector),.vm_rq(vm_rq),.vm_rr(vm_rr),.block_v(block_v),.block_head(block_head),.block_number(block_number),
   .block_data(block_data),.head_weight(head_weight),.fault(operand_fault));
 end else begin:g_n12
  ot_hbm_idx_vm_query_static_n12 operand(.clk(clk),.rst_n(rst_n),.sid(2'd0),.weight_slot(weight_slot),.query_slot(query_slot),.query_index(query_index),
   .weight_sector(weight_sector),.query_sector(query_sector),.vm_rq(vm_rq),.vm_rr(vm_rr),.block_v(block_v),.block_head(block_head),.block_number(block_number),
   .block_data(block_data),.head_weight(head_weight),.fault(operand_fault));
 end endgenerate
 // fixed relay stages outside the tile (no reset, as die relays)
 reg[135:0]rq_p[0:2];reg[2055:0]rr_p[0:2];
 always @(posedge clk)begin
  rq_p[0]<=vm_rq;rq_p[1]<=rq_p[0];rq_p[2]<=rq_p[1];
  rr_p[0]<=bank_rr;rr_p[1]<=rr_p[0];rr_p[2]<=rr_p[1];
 end
 assign bank_rq=(RQ_RLY==0)?vm_rq:rq_p[RQ_RLY-1];
 // relay contents are X before the first edge: hold the request side at 0 during reset so the banks see no slot
 wire[135:0]bank_rq_q=rst_n?bank_rq:136'd0;
 assign vm_rr=(RR_RLY==0)?bank_rr:rr_p[RR_RLY-1];
 reg frame_start=0,emit_v=0;reg[4:0]emit_head=0;
 wire ql_v;wire[7:0]ql_head;wire[511:0]ql_codes;wire[31:0]ql_sc;wire[15:0]ql_w;wire query_fault;
 ot_hbm_idx_query_static_core quant(.clk(clk),.clk_quant(clk),.clk_quant_delay(clk),.clk_bank({4{clk}}),.rst_n(rst_n),.frame_start(frame_start),
  .block_v(block_v),.block_head(block_head),.block_number(block_number),.block_data(block_data),.head_weight(head_weight),
  .emit_v(emit_v),.emit_head(emit_head),.ql_v(ql_v),.ql_head(ql_head),.ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),.fault(query_fault));
 for(genvar b=0;b<8;b=b+1)begin:bank
  wire done,dqd,kqd,xd,x2d;wire[275:0]eg;wire[265:0]pr;
  ot_vms_bank_static #(.RG(1),.WG(1))mem(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd0),.rslot_v(bank_rq_q[b*17+16]),.rslot(1'b0),
   .wslot_v(wr[b*281+280]),.wslot(3'd0),.rq(bank_rq_q[b*17+:17]),.rr(bank_rr[b*257+:257]),.wq(wr[b*281+:281]),.wq_done(done),
   .dq(281'd0),.dq_done(dqd),.kq(281'd0),.kq_done(kqd),.xq(276'd0),.xq_done(xd),.xq2(276'd0),.xq2_done(x2d),.eg(eg),.pq(285'd0),.pr(pr),.status(status[b*18+:18]));
 end
 reg[1023:0]x[0:127];reg[559:0]gold[0:31];reg[255:0]data;
 integer blocks=0,checked=0,errors=0,reads=0,commits=0;
 integer cycle=0,start=-1,firstblock=-1,lastblock=-1,firstquant=-1;
 integer req_phase=-1,rr_phase=-1,phase_errors=0;
 always @(posedge clk)cycle<=cycle+1;
 always @(negedge clk)begin
  for(integer b=0;b<8;b=b+1)begin if(bank_rq_q[b*17+16])reads++;if(wr[b*281+280])commits++;end
  if(PERIOD==2 && rst_n)begin
   for(integer b=0;b<8;b=b+1)begin
    if(vm_rq[b*17+16]===1'b1)begin if(req_phase<0)req_phase=cycle%2;else if(req_phase!=cycle%2)phase_errors++;end
    if(vm_rr[b*257+256]===1'b1)begin if(rr_phase<0)rr_phase=cycle%2;else if(rr_phase!=cycle%2)phase_errors++;end
   end
  end
  if(rst_n&&block_v===1'b1)begin
   blocks++;if(firstblock<0)firstblock=cycle;lastblock=cycle;
   if(block_data!==x[{block_head,block_number}]||head_weight!==16'h3f00+16'(block_head))errors++;
  end
  if(ql_v)begin
   checked++;if(firstquant<0)firstquant=cycle;
   if({ql_w,ql_sc,ql_codes}!==gold[ql_head])errors++;
  end
 end
 initial begin
  $readmemh("query.hex",x);$readmemh("gold.hex",gold);
  repeat(4)@(negedge clk);rst_n=1;frame_start=1;
  @(negedge clk);frame_start=0;
  for(integer row=0;row<64;row=row+1)begin
   for(integer b=0;b<8;b=b+1)begin
    data=x[(row*8+b)/4][((row*8+b)%4)*256+:256];
    if(MUT==2&&row*8+b==99)data=0;
    wr[b*281+:281]={1'b1,1'b0,2'd0,10'(row),3'(b),data,8'hff};
   end
   @(negedge clk);
  end
  wr=0;
  for(integer b=0;b<2;b=b+1)begin
   for(integer w=0;w<16;w=w+1)data[w*16+:16]=16'h3f00+16'(16*b+w);
   if(MUT==1&&b==0)data[15:0]=data[15:0]^16'd1;
   wr[b*281+:281]={1'b1,1'b0,2'd0,10'd64,3'(b),data,8'hff};
  end
  @(negedge clk);wr=0;repeat(8)@(negedge clk);
  weight_slot=1;start=cycle;@(negedge clk);weight_slot=0;repeat(16)@(negedge clk);
  if(PERIOD==2&&MUT!=8)@(negedge clk);
  for(integer q=0;q<128;q=q+1)begin
   query_slot=1;query_index=7'((MUT==3&&q==63)?62:q);@(negedge clk);
   if(PERIOD==2)begin query_slot=0;@(negedge clk);end
  end
  query_slot=0;repeat(40)@(negedge clk);
  for(integer h=0;h<32;h=h+1)begin emit_v=1;emit_head=5'(h);@(negedge clk);end
  emit_v=0;repeat(4)@(negedge clk);
  $display("IDX_VM_QUERY_N12 MUT%0d rq_rly%0d rr_rly%0d commits%0d reads%0d blocks%0d quant%0d errors%0d fault%0d firstblock%0d lastblock%0d firstquant%0d",MUT,RQ_RLY,RR_RLY,commits,reads,blocks,checked,errors,(operand_fault===1'b1)||query_fault||(|status),firstblock-start,lastblock-start,firstquant-start);
  $display("L74_IDX_PERIOD period=%0d req_phase=%0d rr_phase=%0d phase_errors=%0d",PERIOD,req_phase,rr_phase,phase_errors);
  if(phase_errors || (PERIOD==2&&req_phase!=rr_phase))$fatal(1,"L74 request/response parity mismatch");
  if(errors||(operand_fault!==1'b0)||query_fault||(|status)||blocks!=128||checked!=32||reads!=514||commits!=514)$fatal(1,"n+12 operand reader query/weight/quant/latency mismatch");
  $finish;
 end
endmodule
