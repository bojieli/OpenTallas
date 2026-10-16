`timescale 1ns/1ps
// Q-ATTN-RATE bench of ot_qwen_tp8_pv_wide_pair (= 32 x ot_qwen_tp8_pv_col + ot_qwen_tp8_pv_wide_ctl): one command at
// context T. V/e rows are boundary stimuli presented on the requesting port exactly RL edges after the request is
// visible (the service's V_EXT 16 + ER3 3); gold.hex (tools/qwen_attention_native/rate_1015/pv_pair_ref.py) is
// compare-only. Checks: output pulse at the pair's static out_age, 512 words bit-exact, fault 0.
// Plusargs: +VEC=dir +CTX=T +MODE=steady|v_late|v_swap ; parameter MUT=1 = wrong join order (negative control).
module tb_qwen_tp8_pv_wide_pair;
 parameter integer PAIR=0,MUT=0,RL=19;
 reg clk=0,rst_n=0;always #1 clk=~clk;
 reg start=0;integer CTX;string vec,mode;
 reg [7:0] in_valid=0;reg [8191:0] in_v=0;reg [511:0] in_e=0;reg [111:0] in_t=0;reg [127:0] in_epoch=0;
 wire [7:0] req_valid;wire [111:0] req_t;wire out_valid,fault,busy;wire [16383:0] out_leaf;wire [15:0] out_epoch,out_age;
 ot_qwen_tp8_pv_wide_pair #(.PAIR(PAIR),.FIRST_INPUT_AGE(RL+1),.MUT(MUT)) u(.clk(clk),.rst_n(rst_n),.start(start),
  .col_clk({33{clk}}),.context_len(14'(CTX)),.epoch(16'd23),.in_valid(in_valid),.in_v(in_v),.in_e(in_e),.in_t(in_t),
  .in_epoch(in_epoch),.req_valid(req_valid),.req_t(req_t),.out_valid(out_valid),.out_leaf(out_leaf),.out_epoch(out_epoch),
  .fault(fault),.busy(busy),.out_age(out_age));
 reg [1023:0] vr[0:8191];reg [63:0] er[0:8191];reg [31:0] gold[0:511];
 integer due[0:7][0:63],tt[0:7][0:63],wp[0:7],rp[0:7];
 integer cyc=0,scyc=-1,ocyc=-1,errors=0,words=0,nreq=0,i,k,n;
 always @(posedge clk)cyc<=cyc+1;
 initial begin
  if(!$value$plusargs("VEC=%s",vec))$fatal(1,"+VEC");
  if(!$value$plusargs("CTX=%d",CTX))$fatal(1,"+CTX");
  if(!$value$plusargs("MODE=%s",mode))mode="steady";
  $readmemh({vec,"/v.hex"},vr);$readmemh({vec,"/e.hex"},er);$readmemh({vec,"/gold.hex"},gold);
  for(k=0;k<8;k=k+1)begin wp[k]=0;rp[k]=0;end
  repeat(5)@(negedge clk);rst_n=1;repeat(3)@(negedge clk);
  start=1;scyc=cyc;@(negedge clk);start=0;
 end
 // boundary: a request visible in cycle X is presented in cycle X+RL on the same port
 always @(negedge clk)if(rst_n)begin
  in_valid=0;
  for(k=0;k<8;k=k+1)if(rp[k]!=wp[k]&&due[k][rp[k]%64]==cyc)begin
   n=tt[k][rp[k]%64];rp[k]=rp[k]+1;
   in_valid[k]=1;in_t[14*k+:14]=14'(n);in_epoch[16*k+:16]=16'd23;in_v[1024*k+:1024]=vr[n];in_e[64*k+:64]=er[n];
   if(mode=="v_swap"&&nreq==200&&k==2)in_v[1024*k+:1024]=vr[(n+1)%CTX];
  end
  #0.5;
  for(k=0;k<8;k=k+1)if(req_valid[k])begin
   due[k][wp[k]%64]=cyc+RL+((mode=="v_late"&&nreq==150&&k==5)?1:0);tt[k][wp[k]%64]=req_t[14*k+:14];wp[k]=wp[k]+1;nreq=nreq+1;
  end
 end
 always @(posedge clk)if(rst_n&&out_valid)begin
  ocyc=cyc;
  for(i=0;i<512;i=i+1)begin
   if(out_leaf[32*i+:32]!==gold[i])begin if(errors<6)$display("MISMATCH %0d got %08h want %08h",i,out_leaf[32*i+:32],gold[i]);errors=errors+1;end
   words=words+1;
  end
 end
 initial begin
  #4000;
  $display("PV_PAIR %s T=%0d pair=%0d mode=%s words=%0d errors=%0d fault=%0d out_age=%0d got_age=%0d rows=%0d",
   (errors==0&&words==512&&!fault&&ocyc-scyc==out_age)?"PASS":"FAIL",CTX,PAIR,mode,words,errors,fault,out_age,ocyc-scyc,nreq);
  $finish;
 end
endmodule
