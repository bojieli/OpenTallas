`timescale 1ns/1ps
module tb;
 reg clk=0;always #0.4165 clk=~clk;reg rst_n=0,start=0;wire start_ready;
 reg[16:0] d_i=21946;reg[31:0] transaction=32'h12345;reg[255:0] xa=0,xb=0;
 wire head_go,done,best_valid,fault;wire[16:0] best_row;wire[31:0] best_bits;
 ot_dsrom_markov_head_full340 #(.ENABLE(1),.NB(4),.ROW_BASE(10368),.DIE_ROWS(405),.FIRST_BUNDLE(81),
  .PINREG(1),.CACHE_PINREG(0),.A_INPUT_STAGES(4),.MUTANT(0),.MUTANT_BUNDLE(0)) dut(
  .clk(clk),.rst_n(rst_n),.start(start),.start_ready(start_ready),.d_i(d_i),.transaction(transaction),
  .ext_embed_valid(1'b0),.ext_embed_data(256'b0),.ext_embed_beat(4'b0),.ext_embed_id(32'b0),.ext_embed_last(1'b0),.ext_embed_fault(1'b0),
  .head_go(head_go),.xa(xa),.xb(xb),.done(done),.best_valid(best_valid),.best_row(best_row),.best_bits(best_bits),.fault(fault));
 reg[255:0] am[0:255],bm[0:63];reg[31:0] jg[0:511];reg vmask[0:511];reg seen[0:511];
 integer cyc=0,g0=-1,r,i,njoin=0,t0=-1,nv=0;reg[8*1024-1:0] dir;
 always @(posedge clk) cyc<=cyc+1;
 always @(negedge clk) if(rst_n) begin
  if(head_go&&g0<0) g0=cyc;
  if(g0>=0&&cyc-g0>=5) begin xa=am[(cyc-g0-5)%256];xb=bm[(cyc-g0-5)%64];end
  if(fault) $fatal(1,"die fault cycle %0d",cyc);
 if(dut.g_b[0].u.g_a[0].markov.joined_valid)begin r=dut.g_b[0].u.g_a[0].markov.joined_row-10368;if(r<0||r>=32||!vmask[r]||dut.g_b[0].u.g_a[0].markov.joined_bits!==jg[r])$fatal(1,"joined b0 q0 row %0d",r);seen[r]=1;njoin=njoin+1;end
 if(dut.g_b[0].u.g_a[1].markov.joined_valid)begin r=dut.g_b[0].u.g_a[1].markov.joined_row-10368;if(r<32||r>=64||!vmask[r]||dut.g_b[0].u.g_a[1].markov.joined_bits!==jg[r])$fatal(1,"joined b0 q1 row %0d",r);seen[r]=1;njoin=njoin+1;end
 if(dut.g_b[0].u.g_a[2].markov.joined_valid)begin r=dut.g_b[0].u.g_a[2].markov.joined_row-10368;if(r<64||r>=96||!vmask[r]||dut.g_b[0].u.g_a[2].markov.joined_bits!==jg[r])$fatal(1,"joined b0 q2 row %0d",r);seen[r]=1;njoin=njoin+1;end
 if(dut.g_b[0].u.g_a[3].markov.joined_valid)begin r=dut.g_b[0].u.g_a[3].markov.joined_row-10368;if(r<96||r>=128||!vmask[r]||dut.g_b[0].u.g_a[3].markov.joined_bits!==jg[r])$fatal(1,"joined b0 q3 row %0d",r);seen[r]=1;njoin=njoin+1;end
 if(dut.g_b[1].u.g_a[0].markov.joined_valid)begin r=dut.g_b[1].u.g_a[0].markov.joined_row-10368;if(r<128||r>=160||!vmask[r]||dut.g_b[1].u.g_a[0].markov.joined_bits!==jg[r])$fatal(1,"joined b1 q0 row %0d",r);seen[r]=1;njoin=njoin+1;end
 if(dut.g_b[1].u.g_a[1].markov.joined_valid)begin r=dut.g_b[1].u.g_a[1].markov.joined_row-10368;if(r<160||r>=192||!vmask[r]||dut.g_b[1].u.g_a[1].markov.joined_bits!==jg[r])$fatal(1,"joined b1 q1 row %0d",r);seen[r]=1;njoin=njoin+1;end
 if(dut.g_b[1].u.g_a[2].markov.joined_valid)begin r=dut.g_b[1].u.g_a[2].markov.joined_row-10368;if(r<192||r>=224||!vmask[r]||dut.g_b[1].u.g_a[2].markov.joined_bits!==jg[r])$fatal(1,"joined b1 q2 row %0d",r);seen[r]=1;njoin=njoin+1;end
 if(dut.g_b[1].u.g_a[3].markov.joined_valid)begin r=dut.g_b[1].u.g_a[3].markov.joined_row-10368;if(r<224||r>=256||!vmask[r]||dut.g_b[1].u.g_a[3].markov.joined_bits!==jg[r])$fatal(1,"joined b1 q3 row %0d",r);seen[r]=1;njoin=njoin+1;end
 if(dut.g_b[2].u.g_a[0].markov.joined_valid)begin r=dut.g_b[2].u.g_a[0].markov.joined_row-10368;if(r<256||r>=288||!vmask[r]||dut.g_b[2].u.g_a[0].markov.joined_bits!==jg[r])$fatal(1,"joined b2 q0 row %0d",r);seen[r]=1;njoin=njoin+1;end
 if(dut.g_b[2].u.g_a[1].markov.joined_valid)begin r=dut.g_b[2].u.g_a[1].markov.joined_row-10368;if(r<288||r>=320||!vmask[r]||dut.g_b[2].u.g_a[1].markov.joined_bits!==jg[r])$fatal(1,"joined b2 q1 row %0d",r);seen[r]=1;njoin=njoin+1;end
 if(dut.g_b[2].u.g_a[2].markov.joined_valid)begin r=dut.g_b[2].u.g_a[2].markov.joined_row-10368;if(r<320||r>=352||!vmask[r]||dut.g_b[2].u.g_a[2].markov.joined_bits!==jg[r])$fatal(1,"joined b2 q2 row %0d",r);seen[r]=1;njoin=njoin+1;end
 if(dut.g_b[2].u.g_a[3].markov.joined_valid)begin r=dut.g_b[2].u.g_a[3].markov.joined_row-10368;if(r<352||r>=384||!vmask[r]||dut.g_b[2].u.g_a[3].markov.joined_bits!==jg[r])$fatal(1,"joined b2 q3 row %0d",r);seen[r]=1;njoin=njoin+1;end
 if(dut.g_b[3].u.g_a[0].markov.joined_valid)begin r=dut.g_b[3].u.g_a[0].markov.joined_row-10368;if(r<384||r>=416||!vmask[r]||dut.g_b[3].u.g_a[0].markov.joined_bits!==jg[r])$fatal(1,"joined b3 q0 row %0d",r);seen[r]=1;njoin=njoin+1;end
 if(dut.g_b[3].u.g_a[1].markov.joined_valid)begin r=dut.g_b[3].u.g_a[1].markov.joined_row-10368;if(r<416||r>=448||!vmask[r]||dut.g_b[3].u.g_a[1].markov.joined_bits!==jg[r])$fatal(1,"joined b3 q1 row %0d",r);seen[r]=1;njoin=njoin+1;end
 if(dut.g_b[3].u.g_a[2].markov.joined_valid)begin r=dut.g_b[3].u.g_a[2].markov.joined_row-10368;if(r<448||r>=480||!vmask[r]||dut.g_b[3].u.g_a[2].markov.joined_bits!==jg[r])$fatal(1,"joined b3 q2 row %0d",r);seen[r]=1;njoin=njoin+1;end
 if(dut.g_b[3].u.g_a[3].markov.joined_valid)begin r=dut.g_b[3].u.g_a[3].markov.joined_row-10368;if(r<480||r>=512||!vmask[r]||dut.g_b[3].u.g_a[3].markov.joined_bits!==jg[r])$fatal(1,"joined b3 q3 row %0d",r);seen[r]=1;njoin=njoin+1;end
  if(done) begin
   for(i=0;i<512;i=i+1) if(vmask[i]&&!seen[i]) $fatal(1,"valid row %0d never joined",i+10368);
   if(njoin!=nv) $fatal(1,"join count %0d != %0d",njoin,nv);
   if(!best_valid||best_row!=10371||best_bits!==32'h40a382e6) $fatal(1,"die argmax row %0d bits %08x (golden 10371 40a382e6)",best_row,best_bits);
   $display("DIEMETRICS nb=4 rows=%0d start=%0d head_go=%0d done=%0d start_to_done=%0d head_go_to_done=%0d",nv,t0,g0,cyc,cyc-t0,cyc-g0);
   $display("PASS full340 nb=4 sharedlookup joined=%0d argmax row=%0d",njoin,best_row);$finish;
  end
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir)) $fatal(1,"DIR");
  $readmemh({dir,"/xa.hex"},am);$readmemh({dir,"/xb.hex"},bm);$readmemh({dir,"/joined.hex"},jg);
  for(i=0;i<512;i=i+1) begin vmask[i]=(i<405);seen[i]=0;if(i<405) nv=nv+1;end
  repeat(5)@(negedge clk);rst_n=1;repeat(3)@(negedge clk);while(!start_ready)@(negedge clk);start=1;t0=cyc;@(negedge clk);start=0;
 end
 initial begin #60000;$fatal(1,"timeout");end
endmodule
