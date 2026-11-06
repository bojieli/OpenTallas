`timescale 1ns/1ps
module topk_fill_tb;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,clear=0,ingest_v=0,flush=0,emit_v=0;
 reg[2367:0] selected_line=0;reg[7:0]rank=0,gbase=0;
 wire[4167:0]bundle[0:3];
 for(genvar k=0;k<4;k=k+1)begin:dut
  wire f;wire[9:0]c;wire[7:0]we;wire[47:0]wa;wire[4095:0]wd;
  ot_hbm_idx_topk_ingest #(.FILL_GROUPS(k==0?0:8),.MUT(k==2?7:k==3?8:0)) u(
   .clk(clk),.rst_n(rst_n),.clear(clear),.ingest_v(ingest_v),.selected_line(selected_line),
   .flush(flush),.emit_v(emit_v),.rank(rank),.gbase(gbase),.fault(f),.selected_count(c),
   .wo_we(we),.wo_wa(wa),.wo_wd(wd));
  assign bundle[k]={5'd0,f,c,we,wa,wd};
 end
 integer seen7=0,seen8=0,seed=32'h643fd91,cycles=0;integer q,r;
 initial begin
  for(q=0;q<320;q=q+1)begin
   @(negedge clk);
   rst_n=(q>=3 && !(q>=171&&q<=173));
   clear=(q%41==7 || q==174);ingest_v=(q%5!=0);flush=(q%67==66);emit_v=(q%11==0);
   rank=q;gbase=q/2;
   for(r=0;r<64;r=r+1)begin
    selected_line[r*37+:37]={$random(seed),5'b0};
    selected_line[r*37]=(r<q%65) && ((q%3==0)||r%3!=0);
   end
   @(posedge clk);#1;
   if(q>12 && rst_n)begin
    if(bundle[0]!==bundle[1])$fatal(1,"same-edge replication mismatch cycle%0d",q);
    if(bundle[0]!==bundle[2] && !seen7)begin seen7=q;$display("MUT7 caught cycle%0d",q);end
    if(bundle[0]!==bundle[3] && !seen8)begin seen8=q;$display("MUT8 caught cycle%0d",q);end
    cycles=cycles+1;
   end
  end
  if(!seen7||!seen8)$fatal(1,"insensitive mutant7=%0d mutant8=%0d",seen7,seen8);
  $display("PASS real ingest RTL same-edge lockstep %0d cycles; bit-flip and stale-edge mutants caught",cycles);$finish;
 end
endmodule
