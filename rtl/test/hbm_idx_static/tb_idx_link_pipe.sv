`timescale 1ns/1ps
// HBM-IDXPIPE 2026-10-18: pipelined topk link die master ot_hbm_idx_topk_link_static_p vs the historical die master
// ot_hbm_idx_topk_link_static (both pin-registered shells, same input stream). PASS = every output of the
// pipelined tile (tx_v, tx when valid, fault, selected_count) equals the historical output EXACTLY 5 edges earlier on
// every edge (fixed-latency miter), and every emitted record/sequence equals the frame's gold order.
// Frames: 0 all lanes chosen, 1..3 sparse/irregular, 4 the max-pack corner (fill 7 + 64), 5 emit right after flush,
// 6 a short frame flushed early (fault path; must match the historical fault edge +5).
module tb_idx_link_pipe;
 parameter integer MUT=0;
 parameter integer SAFE_RING=0;
 parameter integer SAFE_CARRY=0;
 localparam integer LAT=5;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,clear=0,ingest_v=0,flush=0,emit_v=0;
 reg[3:0]emit_group=0;reg[2367:0]selected_line=0;
 wire[3:0]av,bv;wire[2179:0]atx,btx;wire af,bf;wire[9:0]ac,bc;
 ot_hbm_idx_topk_link_static refdut(.clk(clk),.clk_mem({8{clk}}),.rst_n(rst_n),.clear(clear),.ingest_v(ingest_v),
 .selected_line(selected_line),.flush(flush),.emit_v(emit_v),.emit_group(emit_group),.rank(8'd3),.gbase(8'd1),.tx_v(av),.tx(atx),.fault(af),.selected_count(ac));
 ot_hbm_idx_topk_link_static_p #(.MUT(MUT),.SAFE_RING(SAFE_RING),.SAFE_CARRY(SAFE_CARRY)) dut(.clk(clk),.clk_mem({8{clk}}),.rst_n(rst_n),.clear(clear),.ingest_v(ingest_v),
 .selected_line(selected_line),.flush(flush),.emit_v(emit_v),.emit_group(emit_group),.rank(8'd3),.gbase(8'd1),.tx_v(bv),.tx(btx),.fault(bf),.selected_count(bc));
 integer cycle=0,errors=0,miter=0,records=0,flits=0,total_records=0,frame=0,issued=0,rstc=-1;
 reg[63:0]gold[0:511];
 reg[3:0]hv[0:7];reg[2179:0]htx[0:7];reg hf[0:7];reg[9:0]hc[0:7];
 reg[7:0]fill_seen=0;integer max_pack=0,first_a=-1,first_b=-1,fault_a=-1,fault_b=-1;
 always @(posedge clk)if(rst_n&&refdut.core.ingest_v)begin
  integer take;take=0;for(integer j=0;j<64;j=j+1)take+=int'(refdut.core.selected_line[j*37]);
  fill_seen[refdut.core.fill]=1;if(int'(refdut.core.fill)+take>max_pack)max_pack=int'(refdut.core.fill)+take;
 end
 always @(posedge clk)cycle<=cycle+1;
 always @(negedge clk)begin
  hv[cycle%8]=av;htx[cycle%8]=atx;hf[cycle%8]=af;hc[cycle%8]=ac;
  if(rst_n&&rstc<0)rstc=cycle;
  if(rst_n&&cycle>=rstc+LAT+4)begin
   integer o;o=(cycle-LAT)%8;miter++;
   if({bv,bf,bc}!=={hv[o],hf[o],hc[o]}||((|bv)&&btx!==htx[o]))begin errors++;
    if(errors<6)$display("PIPE_MITER cycle%0d dut v%h f%0d c%0d | ref@-%0d v%h f%0d c%0d",cycle,bv,bf,bc,LAT,hv[o],hf[o],hc[o]);end
  end
  if((|av)&&first_a<0)first_a=cycle;if((|bv)&&first_b<0)first_b=cycle;
  if(af&&fault_a<0)fault_a=cycle;if(bf&&fault_b<0)fault_b=cycle;
  if((|bv)&&frame<6)for(integer l=0;l<4;l=l+1)begin
   if(btx[l*545+512+:16]!==16'(128+flits))errors++;flits++;
   for(integer r=0;r<8;r=r+1)begin
    reg[63:0]rec;rec={btx[l*545+256+r*32+:32],btx[l*545+r*32+:32]};
    if(records>=512||rec!==gold[records])begin errors++;if(errors<6)$display("PIPE_RECORD frame%0d record%0d expected%h got%h",frame,records,gold[records],rec);end
    records++;total_records++;
   end
  end
 end
 task automatic beat(input integer fr,input integer bt);
  selected_line=0;ingest_v=1;
  for(integer j=0;j<64;j=j+1)begin
   reg chosen;reg[15:0]score;integer id;
   chosen=fr==4?(bt==0?j<7:(bt<8?1'b1:j<57)):
          fr==5?(((bt*29+j*7)%11)<3):
          fr==6?(j<2):
          (fr==0)||(fr==2?(bt%2==0?j==0:j<63):((bt*17+j*13+fr*11)%23)<(fr+1));
   if(chosen&&issued<512)begin
    id=fr*1024+issued;score=fr==0?16'hffff:16'(16'h3f00+((issued*17)%127));
    selected_line[j*37+:37]={20'(id),score,1'b1};gold[issued]={32'(id),score,16'd0};issued++;
   end
  end
  @(negedge clk);
 endtask
 initial begin
  repeat(4)@(negedge clk);rst_n=1;repeat(3)@(negedge clk);
  for(frame=0;frame<7;frame=frame+1)begin
   clear=1;@(negedge clk);clear=0;issued=0;records=0;flits=0;
   for(integer bt=0;bt<(frame==6?50:171);bt=bt+1)beat(frame,bt);
   ingest_v=0;selected_line=0;flush=1;@(negedge clk);flush=0;
   if(frame!=5)repeat(3)@(negedge clk);
   if(frame!=6)for(integer g=0;g<16;g=g+1)begin
    emit_v=1;emit_group=4'(g);@(negedge clk);emit_v=0;repeat(7)@(negedge clk);
   end
   repeat(12)@(negedge clk);
   if(frame<6&&(issued!=512||records!=512||flits!=64||af||bf||bc!=512))errors++;
   if(frame==6&&!(af&&bf&&fault_b==fault_a+LAT))errors++;
   $display("IDX_LINK_PIPE frame%0d MUT%0d records%0d flits%0d errors%0d fault%0d/%0d",frame,MUT,records,flits,errors,af,bf);
  end
  if(fill_seen!=8'hff||max_pack!=71)errors++;
  if(first_b!=first_a+LAT)errors++;
  $display("IDX_LINK_PIPE_TOTAL MUT%0d records%0d miter%0d errors%0d fills%h maxpack%0d first_tx ref%0d dut%0d fault ref%0d dut%0d",
   MUT,total_records,miter,errors,fill_seen,max_pack,first_a,first_b,fault_a,fault_b);
  if(errors)$fatal(1,"pipelined link exact/miter/latency mismatch");
  $display("IDX_LINK_PIPE PASS");$finish;
 end
endmodule
