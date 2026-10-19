`timescale 1ns/1ps
`ifndef Q4_MUT
`define Q4_MUT 0
`endif
module tb_q4;
  reg clk=0, run_clock=1, rst_n=0, iv=0;
  always #0.5 if (run_clock) clk=~clk;
  reg [511:0] x=0;
  wire br,bv,bf,bb,qr,qv,qf,qb;
  wire [511:0] by,qy;
  ot_hdc_sinkhorn_p #(.ITERS(20),.CONTROL_SAFE(1)) base
      (.clk(clk),.rst_n(rst_n),.in_valid(iv),.in_ready(br),.in_e(x),.out_valid(bv),.y(by),.fault(bf),.busy(bb));
  ot_hdc_sinkhorn_p #(.ITERS(20),.CONTROL_SAFE(1),.Q4(1),.MUT_Q4(`Q4_MUT)) cand
      (.clk(clk),.rst_n(rst_n),.in_valid(iv),.in_ready(qr),.in_e(x),.out_valid(qv),.y(qy),.fault(qf),.busy(qb));
  integer n=192, expected=642, cases=0, normal=0, faults=0, resets=0, cyc=0;
  reg [31:0] rng=32'h419105a7;
  reg [511:0] saved;
  reg saved_fault, got;
  function automatic [31:0] nx(input [31:0] a);
    reg [31:0] b; begin b=a^(a<<13); b=b^(b>>17); nx=b^(b<<5); end
  endfunction
  task automatic tick; begin @(posedge clk); #0.01; end endtask
  task automatic clear;
    begin
      @(negedge clk); rst_n=0; iv=0; #0.01;
      if(qv||bv||qb||bb||!qr||!br) $fatal(1,"Q4 FAIL reset ownership");
      repeat(3) tick(); @(negedge clk);rst_n=1;tick();
    end
  endtask
  task automatic launch;
    begin
      if(!qr||!br) $fatal(1,"Q4 FAIL launch ownership");
      @(negedge clk);iv=1;tick();@(negedge clk);iv=0;
    end
  endtask
  task automatic check_job(input integer cls);
    integer k,t; reg [31:0] w;
    begin
      for(k=0;k<16;k=k+1)begin
        rng=nx(rng);w=rng;
        case(cls)
          0:w={1'b0,8'(97+rng[28:24]%30),rng[22:0]};
          1:w={1'b0,8'(1+rng[30:24]%127),rng[22:0]};
          2:w=k/4==1?{9'd0,rng[22:0]>>rng[27:23]}:{1'b0,8'(100+rng[28:24]%27),rng[22:0]};
          3:w=k/4==2?0:{1'b0,8'(110+rng[28:24]%17),rng[22:0]};
          4:w=rng[31:29]==0?{1'b1,rng[30:0]}:rng[31:29]==1?32'h7f800000:rng[31:29]==2?32'h7fc00001:{1'b0,8'(115+rng[28:24]%12),rng[22:0]};
          5:w=rng;
          6:w=rng[3:0]==0?{9'd0,rng[22:0]}:{1'b0,8'(90+rng[28:24]%37),rng[22:0]};
          default:w=32'h3f800000>>(rng[1:0]);
        endcase
        x[32*k+:32]=w;
      end
      launch();got=0;
      for(t=1;t<=645;t=t+1)begin
        tick();
        if(bv)begin
          if(t!=602) $fatal(1,"Q4 FAIL baseline age got=%0d",t);
          got=1;saved=by;saved_fault=bf;
        end
        if(qv)begin
          if(t!=expected)$fatal(1,"Q4 FAIL candidate age got=%0d expected=%0d",t,expected);
          if(!got || saved!==qy || saved_fault!==qf)$fatal(1,"Q4 FAIL numerical case=%0d class=%0d baseline_fault=%0d candidate_fault=%0d",cases,cls,saved_fault,qf);
          if(qf)faults++;else normal++;
        end
        if(t==expected&&!qv)$fatal(1,"Q4 FAIL missing expected age=%0d",expected);
        // New request words and invalid/busy pulses cannot alter the job.
        if(t==70)begin @(negedge clk);x=~x;iv=1;end
        if(t==73)begin @(negedge clk);iv=0;end
      end
      cases++;
      if(!qr||!br||qv||bv)$fatal(1,"Q4 FAIL completion ownership");
    end
  endtask
  integer j,phase;
  initial begin
    if($value$plusargs("N=%d",n))begin end
    if($value$plusargs("expect_age=%d",expected))begin end
    clear();
    for(j=0;j<n;j=j+1)check_job(j%8);
    // Cancel in early, Q3/Q4, step-zero, steady, late and final stages.
    for(j=0;j<8;j=j+1)begin
      case(j)0:phase=1;1:phase=11;2:phase=14;3:phase=17;4:phase=18;5:phase=34;6:phase=320;default:phase=641;endcase
      x={16{32'h3f800000}};launch();repeat(phase)tick();clear();resets++;
      repeat(645)begin tick();if(qv||bv||qb||bb)$fatal(1,"Q4 FAIL cancelled transaction escaped");end
      check_job(0);
    end
    // Asynchronous assertion while the clock is stopped; 0.1ns pulse is
    // digital coverage only, never a native minimum-pulse guarantee.
    @(negedge clk);run_clock=0;rst_n=0;#0.1;
    if(qv||bv||qb||bb||!qr||!br)$fatal(1,"Q4 FAIL stopped-clock assertion");
    rst_n=1;#1;run_clock=1;repeat(3)tick();check_job(7);
    $display("Q4 PASS cases=%0d normal=%0d fault=%0d resets=%0d old_age=602 candidate_age=642 delta=40 source_predicate_ff=144",cases,normal,faults,resets);
    $finish;
  end
endmodule
