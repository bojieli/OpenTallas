`timescale 1ns/1ps
`default_nettype none
// TOK-HBM-3: provider ot_hnx_idxn_kb_ctl + ot_hnx_idxn_keybuf NP=4 RS=0 (the instance inside ot_hnx_idxn_quarter_with_keybuf).
// Calendar classes are driven as the IDXQ calendar issues them (frame_start, KEY beats with row, PRE one edge ahead of every
// row >= 1 KEY beat) and as the d4g qctl issues them (+D4G: key_row 0, no PRE). Checks on EVERY edge: key_out = key_in on
// row-0 / d4g beats; key_out = {captured line, tag (pbase+p)*128+b, 1} on replay beats; fault stays 0. +BAD appends a replay
// of a beat not captured in the record (must FAULT; a provider that never clears would miss it).
module tb_idxn_kb_ctl;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,half=0;
 reg fs=0,kv=0,pv=0;reg[7:0]ki=0,pi=0;reg[4:0]kr=0;reg[4395:0]kin=0;
 wire clear,lv,prv,rv;wire[7:0]li,pri,ri;wire[4395:0]kout;wire fault;
 ot_hnx_idxn_kb_ctl dut(.frame_start(fs),.key_v(kv),.key_index(ki),.key_row(kr),.pre_v_in(pv),.pre_index_in(pi),
  .clear(clear),.live_v(lv),.live_index(li),.pre_v(prv),.pre_index(pri),.replay_v(rv),.replay_index(ri));
 ot_hnx_idxn_keybuf #(.NP(4),.RS(0)) kb(.clk(clk),.rst_n(rst_n),.clear(clear),.pbase({half,2'b00}),
  .live_v(lv),.live_index(li),.key_in(kin),.pre_v(prv),.pre_index(pri),.replay_v(rv),.replay_index(ri),.key_out(kout),.fault(fault));
 reg[1087:0]mem[0:3][0:170];
 integer errs=0,checks=0,replays=0,lives=0,seed=1;
 function automatic [4395:0] rnd_lines();
  for(integer w=0;w<4396;w+=32)rnd_lines[w+:32]=$urandom;
 endfunction
 task automatic edge_check(input bit is_replay,input [7:0]b);
  reg[4395:0]exp;
  #4;
  if(is_replay)begin
   for(integer p=0;p<4;p++)exp[p*1099+:1099]={mem[p][b],10'(((half?4:0)+p)*128+b),1'b1};
   replays++;
  end else exp=kin;
  checks++;
  if(kout!==exp)begin errs++;if(errs<5)$display("MISMATCH t=%0t replay=%0d b=%0d",$time,is_replay,b);end
  @(negedge clk);
 endtask
 task automatic idle(input integer n);
  repeat(n)begin fs=0;kv=0;pv=0;kr=0;kin=rnd_lines();edge_check(0,0);end
 endtask
 // one record: N rows, B beats each, row-0 beat gap from gap0 (1 or random 1..3); rows >= 1 back to back (PRE one edge ahead)
 task automatic record(input integer N,input integer B,input bit rgap,input bit d4g,input bit bad);
  fs=1;kv=0;pv=0;kin=rnd_lines();edge_check(0,0);fs=0;
  for(integer b=0;b<B;b++)begin
   kv=1;kr=0;ki=8'(b);kin=rnd_lines();
   for(integer p=0;p<4;p++)mem[p][b]=kin[p*1099+11+:1088];
   lives++;edge_check(0,0);kv=0;
   if(rgap)repeat($urandom%3)begin kin=rnd_lines();edge_check(0,0);end
  end
  if(d4g)return;
  for(integer r=1;r<N;r++)begin
   // edge t: PRE of beat 0; edges t+1..t+B: replay b with PRE of b+1 on the same edge
   kv=0;pv=1;pi=0;kin=rnd_lines();edge_check(0,0);
   for(integer b=0;b<B;b++)begin
    kv=1;kr=5'(r);ki=8'(b);kin=rnd_lines();
    pv=(b+1<B);pi=8'(b+1);
    edge_check(1,8'(b));
   end
   kv=0;pv=0;idle(1+$urandom%4);
  end
  if(bad)begin kv=0;pv=1;pi=8'(B+5);kin=rnd_lines();edge_check(0,0);kv=1;kr=1;ki=8'(B+5);pv=0;#4;@(negedge clk);kv=0;end
 endtask
 initial begin
  bit d4g,bad;integer total_rows=0;
  d4g=$test$plusargs("D4G");bad=$test$plusargs("BAD");
  if($value$plusargs("SEED=%d",seed))void'($urandom(seed));
  if($test$plusargs("HALF"))half=1;
  @(negedge clk);idle(3);rst_n=1;idle(4);
  record(1,171,0,d4g,0);idle(5);
  record(3,171,0,d4g,0);idle(7);
  for(integer n=1;n<=6;n++)begin record(n,37+7*n,n%2,d4g,0);idle(3);total_rows+=n;end
  record(6,171,1,d4g,0);idle(4);
  record(2,37,0,d4g,bad);idle(4);
  $display("KB_CTL mode=%s half=%0d bad=%0d checks=%0d lives=%0d replays=%0d mismatches=%0d fault=%0d",
           d4g?"D4G":"IDXQ",half,bad,checks,lives,replays,errs,fault);
  if(bad) begin if(fault===1'b1&&errs==0)$display("KB_CTL PASS (bad schedule faulted)");else $display("KB_CTL FAIL"); end
  else begin if(errs==0&&fault===1'b0&&(d4g||replays>0))$display("KB_CTL PASS");else $display("KB_CTL FAIL"); end
  $finish;
 end
endmodule
`default_nettype wire
