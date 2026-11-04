`timescale 1ns/1ps
module tb;
 parameter integer MUT=0;
 localparam integer AW=11, PCLO=223;
 reg clk=0;always #0.4165 clk=~clk;
 reg rst_n=0,cfg_we=0,io_cfg_we=0,io_start_v=0;
 reg[2:0]cfg_stripe=0;reg[1:0]io_cfg_stripe=0;
 reg[10:0]cfg_addr=0,io_cfg_addr=0,start_base=0,io_start_base=0;
 reg[255:0]cfg_data=0,io_cfg_data=0;
 reg[11:0]start_limit=16,io_start_limit=28;reg[15:0]start_loops=1,io_start_loops=1;
 wire[2281:0]a,b;wire bf_raw;reg bf_delayed;
 always@(posedge clk)bf_delayed<=bf_raw;
 assign b[0]=MUT?bf_delayed:bf_raw;
 old_ot_hgi_sfu_programme_store_r10 #(.PAGE_AW(1)) gold(
 .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_stripe(cfg_stripe),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
 .io_cfg_we(io_cfg_we),.io_cfg_stripe(io_cfg_stripe),.io_cfg_addr(io_cfg_addr),.io_cfg_data(io_cfg_data),.io_start_v(io_start_v),.io_start_base(io_start_base),.io_start_limit(io_start_limit),.io_start_loops(io_start_loops),
 .programme_active(a[2281]),.programme_done(a[2280]),.programme_ordinal(a[2279:2248]),.io_active(a[2247]),.io_done(a[2246]),.io_ordinal(a[2245:2214]),.io_word(a[2213:1743]),.compiler_control(a[1742:1]),.fault(a[0]));
 ot_hgi_sfu_programme_store_r10 #(.PAGE_AW(1),.NATIVE_FAULT_PIN(1)) dut(
 .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_stripe(cfg_stripe),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
 .io_cfg_we(io_cfg_we),.io_cfg_stripe(io_cfg_stripe),.io_cfg_addr(io_cfg_addr),.io_cfg_data(io_cfg_data),.io_start_v(io_start_v),.io_start_base(io_start_base),.io_start_limit(io_start_limit),.io_start_loops(io_start_loops),
 .programme_active(b[2281]),.programme_done(b[2280]),.programme_ordinal(b[2279:2248]),.io_active(b[2247]),.io_done(b[2246]),.io_ordinal(b[2245:2214]),.io_word(b[2213:1743]),.compiler_control(b[1742:1]),.fault(bf_raw));
 integer cycles=0,bad=0,known=0,unknown=0,ctl=0,iow=0,frise=0,fclear=0,hold_cycles=0,transition_bad=0,writes=0,starts=0,warm=0,j;
 reg prev_fault;
 always@(posedge clk)begin
  #0.001;cycles=cycles+1;
  for(j=0;j<2282;j=j+1)begin
   if(a[j]===1'b0 || a[j]===1'b1)begin known=known+1;if(a[j]!==b[j])begin bad=bad+1;if(bad<9)$display("MISMATCH cycle=%0d bit=%0d ref=%b cand=%b",cycles,j,a[j],b[j]);end end
   else unknown=unknown+1;
  end
  if((|a[1742:1])===1'b1)ctl=ctl+1;
  if((|a[2213:1743])===1'b1)iow=iow+1;
  if(prev_fault===0 && a[0]===1)begin frise=frise+1;if(a[0]!==b[0])transition_bad=transition_bad+1;end
  if(prev_fault===1 && a[0]===0)begin fclear=fclear+1;if(a[0]!==b[0])transition_bad=transition_bad+1;end
  if(prev_fault===1 && a[0]===1)hold_cycles=hold_cycles+1;
  prev_fault=a[0];writes=writes+cfg_we+io_cfg_we;starts=starts+io_start_v;
 end
 function automatic[255:0]random_word;begin random_word={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};end endfunction
 function automatic[255:0]prow(input integer p,st,mode);
 reg[255:0]d;integer w;begin w=(st==7)?188:222;d=random_word()&((256'd1<<w)-1);d=d|(256'hc7a1<<240)|(256'(p)<<PCLO);if(mode==1 && st==5 && p==7)d[245]=~d[245];prow=d;end endfunction
 function automatic[255:0]irow(input integer p,st,mode);
 reg[255:0]d;integer w;begin w=(st==2)?27:222;d=random_word()&((256'd1<<w)-1);if(st==2)d[26]=(p==2);if(mode==3 && st==2 && p==3)d[100]=1;d=d|(256'hc7a1<<240)|(256'(p)<<PCLO);irow=d;end endfunction
 task load_and_run(input integer mode);
 integer kp,ki;begin
  kp=0;ki=0;
  while(kp<16*8 || ki<28*3)begin
   @(negedge clk);cfg_we=0;io_cfg_we=0;
   if(kp<16*8)begin cfg_we=1;cfg_stripe=kp%8;cfg_addr=kp/8;cfg_data=prow(kp/8,kp%8,mode);kp=kp+1;end
   if(ki<28*3)begin io_cfg_we=1;io_cfg_stripe=ki%3;io_cfg_addr=ki/3;io_cfg_data=irow(ki/3,ki%3,mode);ki=ki+1;end
  end
  @(negedge clk);cfg_we=0;io_cfg_we=0;
  repeat(8)@(negedge clk);
  io_start_v=1;@(negedge clk);io_start_v=0;
  repeat(100)@(negedge clk);
 end endtask
 task warm_reset(input integer short_half);
 begin
  @(negedge clk);cfg_we=0;io_cfg_we=0;io_start_v=0;#0.05;rst_n=0;warm=warm+1;
  if(short_half)#0.4165;else #0.833;
  rst_n=1;
  // First legal write on the release edge is also presented, then normal warmup.
  cfg_we=1;cfg_stripe=0;cfg_addr=2047;cfg_data=0;
  @(negedge clk);cfg_we=0;repeat(14)@(negedge clk);
 end endtask
 initial begin
  repeat(6)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
  load_and_run(0);load_and_run(1);repeat(50)@(negedge clk);
  warm_reset(0);load_and_run(3);repeat(50)@(negedge clk);
  warm_reset(1);load_and_run(0);repeat(40)@(negedge clk);
  $display("RESULT MUT=%0d cycles=%0d mismatches=%0d known=%0d unknown=%0d ctl=%0d io=%0d fault_rise=%0d fault_clear=%0d hold=%0d transition_bad=%0d writes=%0d starts=%0d warm=%0d",MUT,cycles,bad,known,unknown,ctl,iow,frise,fclear,hold_cycles,transition_bad,writes,starts,warm);
  if(bad==0 && ctl>=16 && iow>=20 && frise>=2 && fclear>=2 && hold_cycles>=50 && warm==2)$display("PASS");else $display("FAIL");$finish;
 end
endmodule
