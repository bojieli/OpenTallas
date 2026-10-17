`timescale 1ns/1ps
`default_nettype none
// SFU-PS-FUND 2026-10-17: store-level lockstep of ot_hgi_sfu_programme_store_r10 (11 one-stripe spine leaves) against
// the closed r7c store (ot_hgi_sfu_programme_store_r7c, CLOSED TT+30.58/FF+7.18). Same pins, same stimulus, EVERY
// output compared on EVERY edge (io_word, compiler_control, active/done/ordinal for both calendars, fault).
// +MODE=0 clean (random programmes on both calendars incl. simultaneous IO/programme writes, IO loops re-triggering the
//          arithmetic calendar, a second load + run); the run must not fault and must emit >= 200 programme / 300 IO active words.
// +MODE=1 bad word magic in programme stripe 5; +MODE=2 programme stripe 7 bits 188+ nonzero (narrow-W);
// +MODE=3 IO stripe 2 bits 27+ nonzero; +MODE=4 configuration write while busy + start while busy.
// Modes 1-4 must fault, identically. NOTE: an illegal mid-run configuration write to a chain-depth-k stripe faults k
// edges later than r7c (configuration path delay, as r9's +1); mode 4 writes a depth-0 stripe so the edge is exact. Host contract (r10): start >= 4 edges after the last configuration write.
module tb_sfu_store_r10_lockstep;
 localparam integer AW=11, PCLO=234-AW, CHUNK=222;
 reg clk=0; always #0.5 clk=~clk;
 reg rst_n=0;
 reg cfg_we=0,io_cfg_we=0,io_start_v=0;
 reg [2:0] cfg_stripe=0; reg [1:0] io_cfg_stripe=0;
 reg [AW-1:0] cfg_addr=0,io_cfg_addr=0,start_base=0,io_start_base=0;
 reg [255:0] cfg_data=0,io_cfg_data=0;
 reg [AW:0] start_limit=1,io_start_limit=1;
 reg [15:0] start_loops=1,io_start_loops=1;
 wire [470:0] r_io,c_io; wire [1741:0] r_ctl,c_ctl;
 wire r_pa,r_pd,r_ia,r_id,r_f,c_pa,c_pd,c_ia,c_id,c_f;
 wire [31:0] r_po,r_io_o,c_po,c_io_o;
 ot_hgi_sfu_programme_store_r7c #(.PAGE_AW(1)) ref_store(.clk(clk),.rst_n(rst_n),
  .cfg_we(cfg_we),.cfg_stripe(cfg_stripe),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
  .programme_active(r_pa),.programme_done(r_pd),.programme_ordinal(r_po),
  .io_cfg_we(io_cfg_we),.io_cfg_stripe(io_cfg_stripe),.io_cfg_addr(io_cfg_addr),.io_cfg_data(io_cfg_data),
  .io_start_v(io_start_v),.io_start_base(io_start_base),.io_start_limit(io_start_limit),.io_start_loops(io_start_loops),
  .io_active(r_ia),.io_done(r_id),.io_ordinal(r_io_o),.io_word(r_io),.compiler_control(r_ctl),.fault(r_f));
 ot_hgi_sfu_programme_store_r10 #(.PAGE_AW(1)) cut_store(.clk(clk),.rst_n(rst_n),
  .cfg_we(cfg_we),.cfg_stripe(cfg_stripe),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
  .programme_active(c_pa),.programme_done(c_pd),.programme_ordinal(c_po),
  .io_cfg_we(io_cfg_we),.io_cfg_stripe(io_cfg_stripe),.io_cfg_addr(io_cfg_addr),.io_cfg_data(io_cfg_data),
  .io_start_v(io_start_v),.io_start_base(io_start_base),.io_start_limit(io_start_limit),.io_start_loops(io_start_loops),
  .io_active(c_ia),.io_done(c_id),.io_ordinal(c_io_o),.io_word(c_io),.compiler_control(c_ctl),.fault(c_f));
 integer edges=0,mism=0,active_ctl=0,active_io=0,faulted=0,mode=0,seed=1;
 reg checking=0;
 always @(negedge clk)if(checking)begin
  edges++;
  if(|r_ctl)active_ctl++;
  if(|r_io)active_io++;
  if(r_f)faulted++;
  if({r_io,r_ctl,r_pa,r_pd,r_po,r_ia,r_id,r_io_o,r_f}!=={c_io,c_ctl,c_pa,c_pd,c_po,c_ia,c_id,c_io_o,c_f})begin
   mism++;
   if(mism<=6)$display("SFU_STORE_R10_MISMATCH edge=%0d io=%0d ctl=%0d pstat=%0d iostat=%0d fault=%0d/%0d",edges,
    r_io!==c_io,r_ctl!==c_ctl,{r_pa,r_pd,r_po}!=={c_pa,c_pd,c_po},{r_ia,r_id,r_io_o}!=={c_ia,c_id,c_io_o},r_f,c_f);
  end
 end
 function automatic [255:0] rnd256();
  rnd256={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
 endfunction
 // one programme-calendar row p of stripe st (r7c word format: payload | c7a1<<240 | p<<PCLO)
 function automatic [255:0] prow(input integer p,input integer st,input integer m);
  reg [255:0] d; integer w;
  w=(st==7)?188:CHUNK;
  d=rnd256()&((256'd1<<w)-1);
  if(m==2 && st==7 && p==5)d[200]=1'b1;          // narrow-W violation (bits 188..221 of stripe 7)
  d=d|(256'hc7a1<<240)|(256'(p)<<PCLO);
  if(m==1 && st==5 && p==7)d[245]=~d[245];        // bad magic
  prow=d;
 endfunction
 function automatic [255:0] iorow(input integer p,input integer st,input integer arith,input integer m);
  reg [255:0] d; integer w;
  w=(st==2)?27:CHUNK;
  d=rnd256()&((256'd1<<w)-1);
  if(st==2)d[26]=(p==arith);                      // io_word[470] = arithmetic start
  if(m==3 && st==2 && p==3)d[100]=1'b1;          // narrow-W violation (bits 27..221 of IO stripe 2)
  iorow=d|(256'hc7a1<<240)|(256'(p)<<PCLO);
 endfunction
 task automatic load(input integer np,input integer nio,input integer arith);
  integer kp,ki;
  kp=0;ki=0;
  // programme rows on the programme port every edge, IO rows on the IO port on ~3/4 of the edges (often the same edge)
  while(kp<np*8 || ki<nio*3)begin
   cfg_we=0;io_cfg_we=0;
   if(kp<np*8)begin cfg_we=1;cfg_stripe=3'(kp%8);cfg_addr=11'(kp/8);cfg_data=prow(kp/8,kp%8,mode);kp++;end
   if(ki<nio*3 && $urandom%4!=0)begin
    io_cfg_we=1;io_cfg_stripe=2'(ki%3);io_cfg_addr=11'(ki/3);io_cfg_data=iorow(ki/3,ki%3,arith,mode);ki++;
   end
   @(negedge clk);
  end
  cfg_we=0;io_cfg_we=0;cfg_data=rnd256();io_cfg_data=rnd256();
 endtask
 task automatic run(input integer np,input integer nio,input integer ioloops,input integer ploops);
  integer w;
  start_base=0;start_limit=12'(np);start_loops=16'(ploops);
  io_start_base=0;io_start_limit=12'(nio);io_start_loops=16'(ioloops);
  repeat(4)@(negedge clk);                       // r10 host contract: start >= 4 edges after the last write
  io_start_v=1;@(negedge clk);io_start_v=0;
  w=nio*ioloops+np*ploops+40;
  if(mode==4)begin
   repeat(6)@(negedge clk);
   io_cfg_we=1;io_cfg_stripe=2'd0;io_cfg_addr=11'd1;io_cfg_data=iorow(1,0,99,0);@(negedge clk);io_cfg_we=0;   // IO write while IO busy (IO0: chain depth 0)
   repeat(nio/2)@(negedge clk);
   io_start_v=1;@(negedge clk);io_start_v=0;                                                 // start while busy
  end
  repeat(w)@(negedge clk);
 endtask
 integer np,nio,arith;
 initial begin
  if(!$value$plusargs("MODE=%d",mode))mode=0;
  if($value$plusargs("SEED=%d",seed))void'($urandom(seed));
  repeat(6)@(negedge clk);
  checking=1;
  rst_n=0;repeat(8)@(negedge clk);rst_n=1;
  repeat(4)@(negedge clk);                       // r7 host contract: first configuration write 4 edges after release
  // round 1: programme 120..300 rows, IO 30..120 rows, arithmetic start at IO row 2..9, IO loops 1..2
  np=120+$urandom%181;nio=np+30+$urandom%60;arith=2+$urandom%8;
  load(np,nio,arith);
  run(np,nio,1+$urandom%2,1);
  // round 2: reload (different sizes), programme loops 2 (IO long enough to cover them)
  np=60+$urandom%81;nio=2*np+20+$urandom%40;arith=1+$urandom%4;
  load(np,nio,arith);
  run(np,nio,1,2);
  checking=0;
  $display("SFU_STORE_R10_LOCKSTEP mode=%0d seed=%0d edges=%0d mismatching=%0d active_ctl=%0d active_io=%0d fault_edges=%0d",
   mode,seed,edges,mism,active_ctl,active_io,faulted);
  if(mism!=0)$fatal(1,"SFU_STORE_R10_LOCKSTEP FAIL mismatching_edges=%0d",mism);
  if(mode==0 && (faulted!=0 || active_ctl<200 || active_io<300))$fatal(1,"SFU_STORE_R10_LOCKSTEP FAIL clean run faulted=%0d active_ctl=%0d active_io=%0d",faulted,active_ctl,active_io);
  if(mode!=0 && faulted==0)$fatal(1,"SFU_STORE_R10_LOCKSTEP FAIL fault mode %0d never faulted",mode);
  $display("SFU_STORE_R10_LOCKSTEP PASS mode=%0d",mode);
  $finish;
 end
endmodule
`default_nettype wire
