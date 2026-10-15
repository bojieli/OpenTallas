`timescale 1ns/1ps
module tb_link_sentinel_static;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,clear=0,ingest_v=0,flush=0,emit_v=0;
 reg[3:0]emit_group=0;reg[2367:0]selected_line=0;
 wire[3:0]tx_v;wire[2179:0]tx;wire fault;wire[9:0]selected_count;
 integer errors=0,records=0,flits=0;reg[511:0]seen=0;
 ot_hbm_idx_topk_link_static #(.MUT(MUT))dut(.clk(clk),.clk_mem({8{clk}}),.rst_n(rst_n),.clear(clear),.ingest_v(ingest_v),.selected_line(selected_line),.flush(flush),.emit_v(emit_v),.emit_group(emit_group),.rank(8'd3),.gbase(8'd1),.tx_v(tx_v),.tx(tx),.fault(fault),.selected_count(selected_count));
 always @(negedge clk)if(|tx_v)begin
  for(integer l=0;l<4;l=l+1)begin
   if(!tx_v[l]||tx[l*545+512+:16]!==16'(128+flits))errors++;
   flits++;
   for(integer r=0;r<8;r=r+1)begin
    integer id;reg[31:0]v;
    id=int'(tx[l*545+256+r*32+:32]);v=tx[l*545+r*32+:32];records++;
    if(v!==32'hffff0000||v===32'hffffffff)errors++;
    if(id<0||id>511)errors++;else begin if(seen[id])errors++;seen[id]=1;end
   end
  end
 end
 initial begin
  repeat(4)@(negedge clk);rst_n=1;clear=1;
  @(negedge clk);clear=0;
  for(integer f=0;f<8;f=f+1)begin
   ingest_v=1;
   for(integer q=0;q<4;q=q+1)for(integer l=0;l<16;l=l+1)
    selected_line[q*592+l*37+:37]={20'(f*64+q*16+l),16'hffff,1'b1};
   @(negedge clk);
  end
  ingest_v=0;flush=1;@(negedge clk);flush=0;
  repeat(3)@(negedge clk);
  for(integer f=0;f<16;f=f+1)begin
   emit_v=1;emit_group=4'(f);@(negedge clk);emit_v=0;
   repeat(7)@(negedge clk);
  end
  repeat(4)@(negedge clk);
  if(records!=512||flits!=64||seen!={512{1'b1}}||selected_count!=512||fault)errors++;
  $display("IDX_LINK_SENTINEL MUT%0d records%0d flits%0d errors%0d fault%0d",MUT,records,flits,errors,fault);
  if(errors)$fatal(1,"producer sentinel encoding mismatch");$finish;
 end
endmodule
