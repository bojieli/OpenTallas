`timescale 1ps/1fs
module tb_index_fp32_sram_adapter;
 reg clk=0;always #416.666 clk=~clk;
 reg por_n=0,bind_v=0,wr_v=0,wr_ACK_ready=0,start=0,block_r=0;
 reg [31:0] wr_addr=0;reg [1023:0] wr_data=0;
 wire bind_ready,owner_held,wr_ready,wr_ACK_v,publication_ACK,drained,fault;
 wire [31:0] wr_ACK_addr,wr_ACK_job;wire [3:0] wr_ACK_gen;wire [19:0] wr_ACK_pos;wire [6:0] wr_ACK_rank;
 wire read_v,read_r,rsp_v,rsp_r,caller_rsp_r,start_ready,block_v,source_fault,done;
 wire [31:0] read_addr,read_job,rsp_job;wire [5:0] read_words;wire [7:0] read_tag,rsp_tag;
 wire [3:0] read_gen,rsp_gen;wire [19:0] read_pos,rsp_pos;wire [6:0] read_rank,rsp_rank;
 reg permit_rsp=0;
 wire [1023:0] rsp_data,block_data;wire [4:0] block_head;wire [1:0] block_number;wire [15:0] head_weight;
 localparam [31:0] BASE=32'h0020_0000,JOB=32'hbeef_cafe;
 localparam [3:0] GEN=4'hb;localparam [19:0] POS=20'h801ab;localparam [6:0] RANK=7'd65;
 ot_hbm_index_fp32_sram_adapter #(.ENABLE(1)) dut(
  .clk(clk),.por_n(por_n),.bind_v(bind_v),.bind_ready(bind_ready),
  .bind_base_word(BASE),.bind_span_words(32'd8224),.bind_job(JOB),.bind_gen(GEN),.bind_pos(POS),.bind_rank(RANK),.owner_held(owner_held),
  .wr_v(wr_v),.wr_ready(wr_ready),.wr_addr(wr_addr),.wr_data(wr_data),.wr_job(JOB),.wr_gen(GEN),.wr_pos(POS),.wr_rank(RANK),
  .wr_ACK_v(wr_ACK_v),.wr_ACK_ready(wr_ACK_ready),.wr_ACK_addr(wr_ACK_addr),.wr_ACK_job(wr_ACK_job),.wr_ACK_gen(wr_ACK_gen),.wr_ACK_pos(wr_ACK_pos),.wr_ACK_rank(wr_ACK_rank),.positive_publication_ACK(publication_ACK),
  .read_v(read_v),.read_r(read_r),.read_addr(read_addr),.read_words(read_words),.read_tag(read_tag),.read_job(read_job),.read_gen(read_gen),.read_pos(read_pos),.read_rank(read_rank),
  .rsp_v(rsp_v),.rsp_r(rsp_r),.rsp_data(rsp_data),.rsp_tag(rsp_tag),.rsp_job(rsp_job),.rsp_gen(rsp_gen),.rsp_pos(rsp_pos),.rsp_rank(rsp_rank),.drained(drained),.fault(fault));
 ot_hbm_accel_index_query_source #(.ENABLE(1)) caller(
  .clk(clk),.por_n(por_n),.start(start),.start_ready(start_ready),.source_job(JOB),.source_gen(GEN),.source_pos(POS),.source_rank(RANK),
  .original_q_base(BASE),.rotated_q_base(BASE+32'd4096),.scaled_weight_base(BASE+32'd8192),.source_tail_words(8'd64),
  .read_v(read_v),.read_r(read_r),.read_addr(read_addr),.read_tag(read_tag),.read_words(read_words),.read_job(read_job),.read_gen(read_gen),.read_pos(read_pos),.read_rank(read_rank),
  .rsp_v(rsp_v&&permit_rsp),.rsp_r(caller_rsp_r),.rsp_data(rsp_data),.rsp_tag(rsp_tag),.rsp_job(rsp_job),.rsp_gen(rsp_gen),.rsp_pos(rsp_pos),.rsp_rank(rsp_rank),
  .block_v(block_v),.block_r(block_r),.block_head(block_head),.block_number(block_number),.block_data(block_data),.head_weight(head_weight),.fault(source_fault),.done(done));
 assign rsp_r=caller_rsp_r&&permit_rsp;
 function automatic [31:0] payload(input integer word_index);
  if(word_index>=8192)payload=(32'h3f00+32'(word_index-8192))<<16;
  else payload=32'h3e800000+32'(word_index*17);
 endfunction
 integer writes=0,published=0,reads=0,blocks=0,words=0;
 reg [7:0] pending_tag;reg [31:0] pending_addr;
 reg outstanding=0;reg negative=0;reg [1023:0] held_data;reg [7:0] held_tag;
 initial forever begin
  wait(rsp_v);held_tag=rsp_tag;
  begin:hold_provider_response
   reg [1094:0] snapshot;snapshot={rsp_tag,rsp_job,rsp_gen,rsp_pos,rsp_rank,rsp_data};
   repeat(3)begin @(negedge clk);if(!rsp_v||{rsp_tag,rsp_job,rsp_gen,rsp_pos,rsp_rank,rsp_data}!==snapshot)$fatal(1,"held protected provider response changed");end
  end
  permit_rsp=1;wait(rsp_r);@(posedge clk);@(negedge clk);permit_rsp=0;
 end
 always @(posedge clk)if(por_n)begin
  if(publication_ACK)begin
   if(wr_ACK_addr!==BASE+32'(published*32)||{wr_ACK_job,wr_ACK_gen,wr_ACK_pos,wr_ACK_rank}!=={JOB,GEN,POS,RANK})$fatal(1,"publication ACK address/owner mismatch");
   published=published+1;
  end
  if(read_v&&read_r)begin
   if(outstanding)$fatal(1,"overlapping read debt");
   pending_tag=read_tag;pending_addr=read_addr;outstanding=1;reads=reads+1;
  end
  if(rsp_v&&rsp_r)begin
   if(negative)$fatal(1,"NEGATIVE_UNCHECKED_PUBLICATION");
   if(!outstanding||rsp_tag!==pending_tag||{rsp_job,rsp_gen,rsp_pos,rsp_rank}!=={JOB,GEN,POS,RANK})$fatal(1,"response identity mismatch");
   for(integer j=0;j<32;j=j+1)begin
    if(rsp_data[j*32+:32]!==payload(int'(pending_addr-BASE)+j))$fatal(1,"FP32 SRAM response mismatch");
    words=words+1;
   end
   outstanding=0;
  end
  if(block_v&&block_r)begin
   if(block_head!==5'(blocks/4)||block_number!==2'(blocks%4)||head_weight!==(16'h3f00+16'(blocks/4)))$fatal(1,"actual index caller output mismatch");
   for(integer j=0;j<32;j=j+1)begin
    integer a;a=(blocks%4>=2?4096:0)+(blocks/4)*128+(blocks%4)*32+j;
    if(block_data[j*32+:32]!==payload(a))$fatal(1,"actual index caller data mismatch");
   end
   blocks=blocks+1;
  end
 end
 initial begin
  negative=$test$plusargs("SRAM_UE");
  repeat(3)@(negedge clk);por_n=1;
  @(negedge clk);bind_v=1;@(posedge clk);if(!bind_ready)$fatal(1,"real bind refused");
  @(negedge clk);bind_v=0;
  for(integer b=0;b<257;b=b+1)begin
   wr_addr=BASE+32'(b*32);for(integer j=0;j<32;j=j+1)wr_data[j*32+:32]=payload(b*32+j);
   wr_v=1;do @(posedge clk);while(!wr_ready);
   @(negedge clk);wr_v=0;
   wait(wr_ACK_v);held_data=wr_data;
   repeat(3)begin @(negedge clk);if(!wr_ACK_v||publication_ACK||wr_ACK_addr!==wr_addr)$fatal(1,"unpaid/unstable publication ACK");end
   wr_ACK_ready=1;@(posedge clk);@(negedge clk);wr_ACK_ready=0;writes=writes+1;
  end
  if(published!=257)$fatal(1,"wrong publication count");
  if(negative)begin
   // First read is weight row256: logical row256 => physical row64,
   // mux column0. Corrupt two actual SRAM bits in the same SECDED word.
   dut.on.macros[0].u_sram.arr[64][0]=~dut.on.macros[0].u_sram.arr[64][0];
   dut.on.macros[0].u_sram.arr[64][4]=~dut.on.macros[0].u_sram.arr[64][4];
  end
  start=1;@(posedge clk);if(!start_ready)$fatal(1,"actual source start refused");
  @(negedge clk);start=0;
  if(negative)begin
   wait(fault);if(rsp_v||published!=257)$fatal(1,"UE publication gate failed");
   $display("PASS_REAL_SRAM_UE_REFUSED_INDEX_PUBLICATION");$finish;
  end
  for(integer b=0;b<128;b=b+1)begin
   wait(block_v);held_data=block_data;
   repeat(3+(b%4))begin @(negedge clk);if(!block_v||block_data!==held_data)$fatal(1,"held caller block changed");end
   block_r=1;@(posedge clk);@(negedge clk);block_r=0;
  end
  wait(done);@(negedge clk);
  if(fault||source_fault||writes!=257||published!=257||reads!=129||blocks!=128||words!=4128||!drained)$fatal(1,"fullshape counts/debt failed");
  $display("PASS_INDEX_FP32_REAL_SRAM writes=%0d publicationACK=%0d reads=%0d blocks=%0d FP32=%0d",writes,published,reads,blocks,words);$finish;
 end
endmodule
