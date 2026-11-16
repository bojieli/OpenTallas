`timescale 1ps/1fs
// Smallest mechanism: real HOLD64 authority, common three-stage release,
// native two-edge synchronizer. No codec/FIFO or whole-column simulation.
module tb_s81_boot_release;
    parameter integer MUT_SHORT = 0;
    reg rck=0, run_rck=0, rst_n=1, lock=1;
    always #416.5 if (run_rck) rck=~rck; else rck=0;
    wire authority_n, hold_ready, default_n, local_n;
    ot_pdie_pma_reset_hold #(.HOLD_EDGES(64)) hold64
        (.rst_n(rst_n),.pma_lock(lock),.pma_rck(rck),.core_rst_n(authority_n),.hold_ready(hold_ready));
    ot_pdie_pma_release_chain #(.STAGES(0)) dflt
        (.rst_n(authority_n),.pma_rck(rck),.released_n(default_n));
    ot_pdie_pma_release_chain #(.STAGES(MUT_SHORT ? 2 : 3)) selected
        (.rst_n(authority_n),.pma_rck(rck),.released_n(local_n));
    reg [1:0] native_rs;
    always @(posedge rck or negedge local_n)
        if (!local_n) native_rs<=0; else native_rs<={native_rs[0],1'b1};
    integer epoch=0,n,checks=0;
    always @(authority_n or default_n) begin
        #0.001;
        if (default_n !== authority_n) $fatal(1,"default-off identity");
    end
    task held;
      begin
        #0.01;
        if ({authority_n,local_n,native_rs} !== 4'b0)
            $fatal(1,"asynchronous assertion failed epoch%0d values%b%b%b",epoch,authority_n,local_n,native_rs);
      end
    endtask
    task resume;
      begin
        run_rck=1;
        for(n=1;n<=71;n=n+1)begin
          @(posedge rck); #0.1;
          if (authority_n !== (n>=66)) $fatal(1,"authority calendar epoch%0d edge%0d",epoch,n);
          if (local_n !== (n>=69)) $fatal(1,"common release calendar epoch%0d edge%0d",epoch,n);
          if (native_rs[1] !== (n>=71)) $fatal(1,"native release calendar epoch%0d edge%0d",epoch,n);
          checks=checks+1;
        end
        $display("BOOT_RELEASE epoch%0d authority66 common69 native71",epoch);
      end
    endtask
    initial begin
      #1 rst_n=0;held();#2 rst_n=1;
      #1600;held();resume();repeat(8)@(posedge rck);
      // Warm reset while stopped, assertion and deassertion have no RCK edge.
      @(negedge rck);run_rck=0;#1000;epoch=1;rst_n=0;held();rst_n=1;#1800;held();resume();
      // Warm reset with recovered clock running.
      @(negedge rck);epoch=2;#5 rst_n=0;held();@(negedge rck);#5 rst_n=1;resume();
      // Lock loss running, then relock.
      @(negedge rck);epoch=3;#5 lock=0;held();repeat(3)@(negedge rck);#5 lock=1;resume();
      // Clock stops, lock lost while stopped, restarts unlocked, then relocks.
      @(negedge rck);run_rck=0;epoch=4;#1000;lock=0;held();#1500;run_rck=1;
      repeat(6)begin @(posedge rck);held();end
      @(negedge rck);#5 lock=1;resume();
      $display("PASS S81 boot release3 checks%0d epochs5 default identity async clock-stop assertion",checks);
      $finish;
    end
    initial begin #2000000;$fatal(1,"bench stalled");end
endmodule
