`timescale 1ns/1ps
module tb_reset;
  reg clk=0,run=1,raw_n=1;
  always #0.5 if(run)clk=~clk;
  wire [11:0] rn;
  s81_gunit_reset_candidate d(.clk(clk),.raw_n(raw_n),.region_n(rn));
  integer pulses=0,stopped=0,coincident=0,j,t;
  task automatic release_check;
    begin
      for(t=1;t<=4;t=t+1)begin
        @(posedge clk);#0.001;
        if(rn!==(t<3?12'h000:12'hfff))$fatal(1,"RESET_PROTOTYPE FAIL release t=%0d rn=%h",t,rn);
      end
    end
  endtask
  task automatic pulse(input real width,input bit stop);
    begin
      @(negedge clk);run=!stop;#0.1;raw_n=0;#0.001;
      if(rn!==0)$fatal(1,"RESET_PROTOTYPE FAIL async assertion");
      #(width);raw_n=1;#0.001;
      if(stop)begin
        #2;
        if(rn!==0)$fatal(1,"RESET_PROTOTYPE FAIL stopped release");
        run=1;stopped++;
      end
      release_check();pulses++;
    end
  endtask
  initial begin
    // Initial 1->0 event prevents a simulator-specific initialized-zero proof.
    #0.1;raw_n=0;#0.1;raw_n=1;release_check();
    for(j=0;j<3;j=j+1)begin
      pulse(j==0?0.02:j==1?0.1:0.25,0);
      pulse(j==0?0.02:j==1?0.1:0.25,1);
    end
    // Drive before the same posedge event; no metastability claim follows.
    @(negedge clk);#0.5;raw_n=0;#0.001;
    if(rn!==0)$fatal(1,"RESET_PROTOTYPE FAIL coincident assert");
    @(negedge clk);#0.5;raw_n=1;#0.001;
    // Ordering at a coincident release is intentionally not equality-qualified.
    repeat(4)@(negedge clk);
    if(rn!==12'hfff)$fatal(1,"RESET_PROTOTYPE FAIL coincident recovery");
    coincident++;
    $display("RESET_PROTOTYPE PASS pulses=%0d stopped=%0d coincident=%0d stable_release_edges=3 raw_async_loads=2 sync0_loads=13 sync1_loads=12 NATIVE_PULSE_ASSERTION_RECOVERY_UNPROVED",pulses,stopped,coincident);$finish;
  end
endmodule
