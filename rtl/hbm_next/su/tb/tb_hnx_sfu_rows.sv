`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HBM-NEXT-UNITS-SUDMA2 2026-10-19: SFU CHAIN ROW STEP bench. Lockstep of two d4g SFU programme stores
// (ot_hgi_sfu_programme_store_r10, unchanged; the die's store) feeding the stream SFU core's input boundary:
//   A (row-relative): IO image = prologue P0 words + ONE row body of P words (row 0's VM sectors); launches: prologue
//     [0, P0) x 1, then the body [P0, P0 + P) x N (start_loops = N); ot_hnx_sfu_rowstep (period P, strides s_rd, s_wr)
//     adds row x stride to every valid prefetch / drain VM sector;
//   B (unrolled d4g image): prologue + N bodies with absolute sectors (row r: + r s); launches [0, P0) x 1, then
//     [P0, P0 + N P) x 1; ot_hnx_sfu_rowstep with period 0 / strides 0 (= a pin register, d4g words unchanged).
// Both stores hold the same arithmetic programme (Pc words), started once a row by the body's arith-start bit (IO2 bit
// 26 = io_word[470]). EVERY edge: A's (io_word, compiler_control) out of its row step == B's; no store / row-step fault
// (mode 0). The SFU core consumes only these two buses (its VM responses are a function of the sectors it requests),
// so equality here is the core's behaviour bit for bit. Measured: the edges between successive row arith starts in A's
// output (= P: the loop wrap adds no bubble) and the programme restart spacing (+DP: P = Pc + DP; the store faults a
// programme start while busy -> the minimum legal P - Pc).
// Two rounds (reload, different N / P / images) prove the row index restarts at ordinal 0.
// +SEED, +DP (default 4), +EXPECT_FAULT=1 (DP sweep: the run may fault; the bench prints the outcome, never PASS).
// RTL mutants (-GMUT, ot_hnx_sfu_rowstep in A only, must FAIL): 1 drain stride, 2 prefetch stride, 3 wrap one word
// early, 4 row not cleared at ordinal 0. +BADSTRIDE=1: s_rd[2:0] != 0 (row step must FAULT -> FAIL).
// ---------------------------------------------------------------------------------------------------------------------
module tb_hnx_sfu_rows;
 parameter integer MUT=0;
 localparam integer AW=11, PCLO=234-AW, CHUNK=222;
 reg clk=0; always #0.5 clk=~clk;
 reg rst_n=0;
 reg cfg_we=0; reg [2:0] cfg_stripe=0; reg [AW-1:0] cfg_addr=0; reg [255:0] cfg_data=0;
 reg [AW-1:0] start_base=0; reg [AW:0] start_limit=1; reg [15:0] start_loops=1;
 reg a_io_we=0,b_io_we=0; reg [1:0] io_stripe=0; reg [AW-1:0] io_addr=0; reg [255:0] io_data=0;
 reg a_sv=0,b_sv=0; reg [AW-1:0] a_base=0,b_base=0; reg [AW:0] a_lim=1,b_lim=1; reg [15:0] a_loops=1,b_loops=1;
 wire [470:0] a_io,b_io; wire [1741:0] a_ctl,b_ctl; wire [31:0] a_ord,b_ord,a_po,b_po;
 wire a_f,b_f,a_pa,a_pd,a_ia,a_id,b_pa,b_pd,b_ia,b_id;
 ot_hgi_sfu_programme_store_r10 #(.PAGE_AW(1)) a_store(.clk(clk),.rst_n(rst_n),
  .cfg_we(cfg_we),.cfg_stripe(cfg_stripe),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
  .programme_active(a_pa),.programme_done(a_pd),.programme_ordinal(a_po),
  .io_cfg_we(a_io_we),.io_cfg_stripe(io_stripe),.io_cfg_addr(io_addr),.io_cfg_data(io_data),
  .io_start_v(a_sv),.io_start_base(a_base),.io_start_limit(a_lim),.io_start_loops(a_loops),
  .io_active(a_ia),.io_done(a_id),.io_ordinal(a_ord),.io_word(a_io),.compiler_control(a_ctl),.fault(a_f));
 ot_hgi_sfu_programme_store_r10 #(.PAGE_AW(1)) b_store(.clk(clk),.rst_n(rst_n),
  .cfg_we(cfg_we),.cfg_stripe(cfg_stripe),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
  .programme_active(b_pa),.programme_done(b_pd),.programme_ordinal(b_po),
  .io_cfg_we(b_io_we),.io_cfg_stripe(io_stripe),.io_cfg_addr(io_addr),.io_cfg_data(io_data),
  .io_start_v(b_sv),.io_start_base(b_base),.io_start_limit(b_lim),.io_start_loops(b_loops),
  .io_active(b_ia),.io_done(b_id),.io_ordinal(b_ord),.io_word(b_io),.compiler_control(b_ctl),.fault(b_f));
 reg [11:0] period=0; reg [15:0] s_rd=0,s_wr=0;
 wire [470:0] ao,bo; wire [1741:0] ac,bc; wire [15:0] arow,brow; wire af,bf;
 ot_hnx_sfu_rowstep #(.REG(1),.MUT(MUT)) a_rs(.clk(clk),.rst_n(rst_n),.io_in(a_io),.ctl_in(a_ctl),.ordinal(a_ord),
  .period(period),.s_rd(s_rd),.s_wr(s_wr),.io_out(ao),.ctl_out(ac),.row_out(arow),.fault(af));
 ot_hnx_sfu_rowstep #(.REG(1),.MUT(0)) b_rs(.clk(clk),.rst_n(rst_n),.io_in(b_io),.ctl_in(b_ctl),.ordinal(b_ord),
  .period(12'd0),.s_rd(16'd0),.s_wr(16'd0),.io_out(bo),.ctl_out(bc),.row_out(brow),.fault(bf));
 integer edges=0,mism=0,active_io=0,active_ctl=0,faults=0,checking=0,last_st=-1,ii_min=1<<30,ii_max=0,starts=0,ecnt=0;
 integer expect_fault=0,cur_p=0,ii_bad=0;
 always @(negedge clk)if(checking)begin
  edges++;
  if(|ao)active_io++;
  if(|ac)active_ctl++;
  if(a_f||b_f||af||bf)faults++;
  if({ao,ac}!=={bo,bc})begin
   mism++;
   if(mism<=6)$display("SFU_ROWS MISMATCH edge=%0d io=%0d ctl=%0d row=%0d",edges,ao!==bo,ac!==bc,arow);
  end
  if(ao[470])begin
   starts++;
   if(last_st>=0&&checking==2)begin
    if(edges-last_st<ii_min)ii_min=edges-last_st; if(edges-last_st>ii_max)ii_max=edges-last_st;
    if(edges-last_st!=cur_p)ii_bad++;
   end
   last_st=edges;
  end
 end
 function automatic [255:0] rnd256();
  rnd256={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
 endfunction
 // one IO word: prefetch (prob ~1/2 a port), drains (~1/4), sectors keep the port id in [2:0]; arith start at word ar
 function automatic [470:0] ioword(input integer p,input integer ar,input integer base);
  reg [470:0] w; integer b;
  w={rnd256(),rnd256()}; w[470]=(p==ar);
  for(b=0;b<8;b=b+1)begin w[b]=($urandom%2==0); w[16+16*b+:16]={1'b0,12'(base+$urandom%256),3'(b)}; end
  for(b=0;b<2;b=b+1)begin w[404+b]=($urandom%4==0); w[436+16*b+:16]={1'b0,12'(base+2048+$urandom%256),3'(b)}; end
  ioword=w;
 endfunction
 function automatic [470:0] stepw(input [470:0] w,input integer r,input integer srd,input integer swr);
  integer b; stepw=w;
  for(b=0;b<8;b=b+1)if(w[b])stepw[16+16*b+:16]=w[16+16*b+:16]+16'(r*srd);
  for(b=0;b<2;b=b+1)if(w[404+b])stepw[436+16*b+:16]=w[436+16*b+:16]+16'(r*swr);
 endfunction
 task automatic io_write(input integer which,input integer addr,input [470:0] w);   // which 1 A, 2 B, 3 both
  integer s; reg [255:0] d;
  for(s=0;s<3;s=s+1)begin
   d=0;
   if(s<2)d[CHUNK-1:0]=w[s*CHUNK+:CHUNK]; else d[26:0]=w[470:444];
   d=d|(256'hc7a1<<240)|(256'(addr)<<PCLO);
   a_io_we=which[0]; b_io_we=which[1]; io_stripe=2'(s); io_addr=11'(addr); io_data=d;
   @(negedge clk);
  end
  a_io_we=0; b_io_we=0;
 endtask
 task automatic prog_load(input integer np);
  integer kp; reg [255:0] d; integer w;
  for(kp=0;kp<np*8;kp=kp+1)begin
   w=(kp%8==7)?188:CHUNK;
   d=rnd256()&((256'd1<<w)-1);
   cfg_we=1; cfg_stripe=3'(kp%8); cfg_addr=11'(kp/8); cfg_data=d|(256'hc7a1<<240)|(256'(kp/8)<<PCLO);
   @(negedge clk);
  end
  cfg_we=0;
 endtask
 task automatic round(input integer n,input integer pc,input integer dp,input integer p0,input integer badstride);
  integer p,r,ar,i; reg [470:0] w; integer srd,swr,base;
  p=pc+dp; ar=1+$urandom%3; base=8*($urandom%512);
  srd=8*(1+$urandom%64)+((badstride!=0)?3:0); swr=8*(1+$urandom%64);
  prog_load(pc);
  for(i=0;i<p0;i=i+1)io_write(3,i,ioword(i,-1,4000));                  // prologue (broadcast operands): both stores
  for(i=0;i<p;i=i+1)begin
   w=ioword(i,ar,base);
   io_write(1,p0+i,w);                                                   // A: row 0 only
   for(r=0;r<n;r=r+1)io_write(2,p0+r*p+i,stepw(w,r,srd,swr));           // B: unrolled, absolute sectors
  end
  period=12'(p); s_rd=16'(srd); s_wr=16'(swr); cur_p=p;
  start_base=0; start_limit=12'(pc); start_loops=1;
  repeat(6)@(negedge clk);
  a_base=0; a_lim=12'(p0); a_loops=1; b_base=0; b_lim=12'(p0); b_loops=1;
  a_sv=1; b_sv=1; @(negedge clk); a_sv=0; b_sv=0;
  repeat(p0+12)@(negedge clk);
  a_base=11'(p0); a_lim=12'(p0+p); a_loops=16'(n); b_base=11'(p0); b_lim=12'(p0+n*p); b_loops=1;
  checking=2; last_st=-1;
  a_sv=1; b_sv=1; @(negedge clk); a_sv=0; b_sv=0;
  repeat(n*p+pc+40)@(negedge clk);
  checking=1;
  $display("SFU_ROWS round n=%0d P=%0d Pc=%0d DP=%0d P0=%0d s_rd=%0d s_wr=%0d arith_starts=%0d",n,p,pc,dp,p0,srd,swr,starts);
 endtask
 integer seed=1,dp=4,bad=0,s1;
 initial begin
  if($value$plusargs("SEED=%d",seed))void'($urandom(seed));
  if(!$value$plusargs("DP=%d",dp))dp=4;
  if(!$value$plusargs("EXPECT_FAULT=%d",expect_fault))expect_fault=0;
  if(!$value$plusargs("BADSTRIDE=%d",bad))bad=0;
  repeat(6)@(negedge clk); rst_n=1; repeat(4)@(negedge clk);
  checking=1;
  round(6,40+$urandom%30,dp,8+$urandom%8,bad);
  s1=starts;
  round(3+$urandom%3,30+$urandom%40,dp,4+$urandom%8,bad);
  checking=0;
  $display("SFU_ROWS_II row_arith_start_spacing min=%0d max=%0d (= P of each round; off-P spacings %0d) starts=%0d",ii_min,ii_max,ii_bad,starts);
  $display("SFU_ROWS edges=%0d mismatching=%0d active_io=%0d active_ctl=%0d fault_edges=%0d MUT=%0d DP=%0d",
   edges,mism,active_io,active_ctl,faults,MUT,dp);
  if(expect_fault)begin $display("SFU_ROWS RESTART DP=%0d faulted=%0d",dp,faults!=0); $finish; end
  if(mism!=0||faults!=0||ii_bad!=0||active_io<200||active_ctl<200||s1<6)
   $fatal(1,"SFU_ROWS FAIL mismatching=%0d faults=%0d active_io=%0d active_ctl=%0d MUT=%0d",mism,faults,active_io,active_ctl,MUT);
  $display("SFU_ROWS PASS MUT=%0d",MUT);
  $finish;
 end
endmodule
`default_nettype wire
