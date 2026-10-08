`timescale 1ns/1ps
// Bench of the native SM -> SU result edge: SM result emitter (one-way rv/rrow/rdata/fault, rows of an op in a
// random order, random gaps, <= 1 row a cycle, never started before its reservation) -> pin station, NST relays,
// pin station -> SU ingress (credit reservation, count-gated release) -> consumer with random back-pressure.
// Checks every drained row bit-exactly against the golden payload of (op, row), every op's rows exactly once and
// in op order, no row released before its op's last row reached the ingress (SMSU_EARLY_RELEASE), op_done order
// and counts, credits back to 64 at the end, no fault (SMSU_FAULT), progress (SMSU_TIMEOUT).
// Negatives (defines): NEG_NO_RESERVATION (an op started without a grant), NEG_EXTRA_ROW (a repeated row),
// NEG_SM_FAULT (SM fault pin) -> the ingress must raise fault.
module tb_sm_su_result_edge;
 parameter integer NST=4, OPS=200, SEED=11, PIN=0, OCR=4;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0;
 reg rv=0;reg [11:0] rrow=0;reg [255:0] rdata=0;reg sm_fault=0;
 reg op_v=0;reg [6:0] op_rows=0;wire op_ack;
 wire out_v;reg out_r=0;wire [11:0] out_row;wire [255:0] out_data;wire op_done;wire [6:0] op_done_rows;wire fault;wire [6:0] free_o;
 ot_hbm_sm_su_result_edge #(.NST(NST),.PIN(PIN),.OCR(OCR)) dut(.*);
 function automatic [255:0] golden(input integer op,input integer row);
  for(integer i=0;i<8;i=i+1)golden[i*32+:32]=(op*32'h9e3779b1)^(row*32'h85ebca6b)^(i*32'hc2b2ae35)^32'h27d4eb2f;
 endfunction
 integer rows[0:4095];integer cyc=0;
 always @(posedge clk)cyc<=cyc+1;
 // ---------------- SU command path: reserve op k, then the SM may start op k
 integer n_res=0,n_start=0,seed;
 reg skip_now=0;
 always @(negedge clk)begin
  op_v=0;skip_now=0;
  if(rst_n&&n_res<OPS&&n_res<n_start+4)begin
`ifdef NEG_NO_RESERVATION
   if(n_res==5)skip_now=1; else
`endif
   // present the next op (held until op_ack; may also be withdrawn and re-presented before it is taken)
   // PIN=1: a registered SU drops op_v one cycle after it sees op_ack (the shell's ack mask must absorb it)
   if(op_ack)begin if(PIN!=0)begin op_v=1;op_rows=rows[n_res];end end else if($urandom%4!=0)begin op_v=1;op_rows=rows[n_res];end
  end
 end
 always @(posedge clk)if(rst_n&&(op_ack||skip_now))n_res<=n_res+1;
 // ---------------- SM: executes reserved ops in order, rows in a random permutation, one-way face
 integer perm[0:63];integer emitted=0,cur=-1,tmp,a,b;
 initial begin
  seed=$urandom(SEED);
  for(integer i=0;i<OPS;i=i+1)begin
   rows[i]=1+($urandom%43);
   if(i%17==3)rows[i]=64;
   if(i%23==7)rows[i]=1;
  end
 end
 always @(negedge clk)begin
  rv=0;sm_fault=0;
  if(rst_n)begin
   if(cur<0&&n_start<OPS&&(n_start<n_res
`ifdef NEG_NO_RESERVATION
     ||(n_start==5)
`endif
   ))begin
    cur=n_start;n_start=n_start+1;emitted=0;
    for(integer i=0;i<rows[cur];i=i+1)perm[i]=i;
    for(integer i=rows[cur]-1;i>0;i=i-1)begin a=$urandom%(i+1);tmp=perm[i];perm[i]=perm[a];perm[a]=tmp;end
   end else if(cur>=0&&($urandom%5!=0))begin
    rv=1;rrow=perm[emitted];rdata=golden(cur,perm[emitted]);
`ifdef NEG_SM_FAULT
    if(cur==2&&emitted==1)sm_fault=1;
`endif
    emitted=emitted+1;
`ifdef NEG_EXTRA_ROW
    if(cur==3&&emitted==rows[cur])begin emitted=emitted-1;perm[emitted]=perm[0];end
`endif
    if(emitted==rows[cur])cur=-1;
   end
  end
 end
 // ---------------- arrival bookkeeping at the ingress input (after the SU pin station)
 integer last_in_cyc[0:4095];integer arr_cnt[0:4095];integer ain=0;integer sm_rv_cyc,lat_edge=-1;
 initial for(integer i=0;i<4096;i=i+1)begin last_in_cyc[i]=-1;arr_cnt[i]=0;end
 always @(posedge clk)if(rst_n&&dut.u_in.in_v)begin
  arr_cnt[ain]=arr_cnt[ain]+1;
  if(arr_cnt[ain]==rows[ain])begin last_in_cyc[ain]=cyc;ain=ain+1;end
 end
 // one-way latency: the first row leaves the SM pins at sm_rv_cyc and reaches the ingress write port
 integer first_rv=-1,first_in=-1;
 always @(posedge clk)if(rst_n)begin
  if(rv&&first_rv<0)first_rv=cyc;
  if(dut.u_in.in_v&&first_in<0)first_in=cyc;
  if(first_in>=0&&lat_edge<0)lat_edge=first_in-first_rv;
 end
 // ---------------- consumer
 integer dop=0,dcnt=0,ndone=0,lat_done_max=0,lat_done_sum=0;reg [63:0] dseen=0;
 // PIN=0: same-cycle ready (take = out_v && out_r).  PIN=1: credit flow: every out_v is a delivered row into
 // the consumer's OCR-row buffer; out_r is a credit-return pulse per freed slot (same random drain pattern).
 integer bcnt=0;wire take_tb=(PIN!=0)?out_v:(out_v&&out_r);
 always @(negedge clk)out_r=($urandom%7)!=0&&!((cyc/300)%5==4)&&((PIN==0)||bcnt>0);
 always @(posedge clk)if(rst_n&&PIN!=0)begin
  bcnt=bcnt+(out_v?1:0)-(out_r?1:0);
  if(bcnt>OCR)$fatal(1,"SMSU_OUT_OVERFLOW consumer buffer %0d > OCR=%0d",bcnt,OCR);
 end
 always @(posedge clk)if(rst_n)begin
  if(fault)$fatal(1,"SMSU_FAULT ingress fault raised (free=%0d op=%0d)",free_o,dop);
  if(op_done)begin
   if(op_done_rows!=rows[ndone])$fatal(1,"SMSU_DONE op %0d rows %0d expected %0d",ndone,op_done_rows,rows[ndone]);
   if(last_in_cyc[ndone]<0)$fatal(1,"SMSU_EARLY_RELEASE op_done before the last row of op %0d",ndone);
   lat_done_sum=lat_done_sum+(cyc-last_in_cyc[ndone]);if(cyc-last_in_cyc[ndone]>lat_done_max)lat_done_max=cyc-last_in_cyc[ndone];
   ndone=ndone+1;
  end
  if(take_tb)begin
   if(last_in_cyc[dop]<0)$fatal(1,"SMSU_EARLY_RELEASE row of op %0d released before its last row arrived",dop);
   if(out_row>=rows[dop]||dseen[out_row[5:0]])$fatal(1,"SMSU_DATA op %0d bad/repeated row %0d",dop,out_row);
   if(out_data!==golden(dop,out_row))$fatal(1,"SMSU_DATA op %0d row %0d payload mismatch",dop,out_row);
   dseen[out_row[5:0]]=1;dcnt=dcnt+1;
   if(dcnt==rows[dop])begin dop=dop+1;dcnt=0;dseen=0;end
  end
 end
 integer last_progress=0,prev_dop=0;
 always @(posedge clk)begin
  if(dop!=prev_dop)begin prev_dop=dop;last_progress=cyc;end
  if(rst_n&&cyc-last_progress>20000)$fatal(1,"SMSU_TIMEOUT no op drained for 20000 cycles (dop=%0d n_res=%0d free=%0d)",dop,n_res,free_o);
 end
 initial begin
  repeat(4)@(negedge clk);rst_n=1;
  wait(dop==OPS);repeat(10)@(negedge clk);
  if(free_o!=64)$fatal(1,"SMSU_CREDIT credits not returned: free=%0d",free_o);
  if(ndone!=OPS)$fatal(1,"SMSU_DONE %0d op_done pulses for %0d ops",ndone,OPS);
  $display("PASS_SMSU ops=%0d stations=%0d edge_latency_cycles=%0d lastrow_to_op_done_max=%0d avg_x100=%0d cycles=%0d",
   OPS,NST,lat_edge,lat_done_max,lat_done_sum*100/OPS,cyc);
  $finish;
 end
endmodule
