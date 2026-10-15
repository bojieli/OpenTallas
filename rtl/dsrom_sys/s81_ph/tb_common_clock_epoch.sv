`timescale 1ps/1ps
module tb_common_clock_epoch;
    reg master=0, rst_n=0, lock=0;
    wire cs,cv,valid,window,toggle,fault,running;
    wire [3:0] phase;
    ot_s81_common_clock_epoch dut(master,rst_n,lock,cs,cv,valid,window,toggle,fault,phase,running);
    // Integer 100ps test master: ratios and pulse lengths are exact, not MHz evidence.
    always #50 master=~master;
    integer seen=0, valid_seen=0, reset_phase;
    time s_edge=0,v_edge=0;
    always @(cs) if ($time>100) begin
        if(s_edge && $time-s_edge<100) $fatal(1,"stream runt");
        s_edge=$time;
    end
    always @(cv) if ($time>100) begin
        if(v_edge && $time-v_edge<100) $fatal(1,"serial runt");
        v_edge=$time;
    end
    always @(negedge master) if(running) begin
        seen=seen+1;
        if(phase>11) $fatal(1,"phase bounds");
        if(cs !== ((phase%3)==0)) $fatal(1,"stream phase");
        if(cv !== ((phase%4)<2)) $fatal(1,"serial phase");
        if(window !== (valid && dut.window_armed && (phase==11 || phase==0))) $fatal(1,"epoch window");
        if(valid) valid_seen=valid_seen+1;
    end
    initial begin
        repeat(3) @(negedge master); rst_n=1;lock=1;
        repeat(40) @(negedge master);
        if(!valid || !valid_seen) $fatal(1,"never armed");
        // A sub-master-period lock glitch must asynchronously invalidate and
        // persist through lock_sync long enough to force a full restart.
        #13 lock=0; #1;
        if(valid) $fatal(1,"lock loss did not immediately invalidate");
        #9 lock=1;
        repeat(30) @(negedge master);
        if(!fault || !valid) $fatal(1,"relock/fault failed");
        // Reset each possible master phase, including during serial high.
        for(reset_phase=0;reset_phase<12;reset_phase=reset_phase+1) begin
            #13 rst_n=0; #1;
            if(valid) $fatal(1,"reset valid");
            repeat(2) @(negedge master); rst_n=1;
            repeat(19+reset_phase) @(negedge master);
            if(!valid || fault) $fatal(1,"reset/rearm failed");
        end
        if(seen<150) $fatal(1,"coverage");
        $display("PASS common clock epoch seen=%0d valid=%0d",seen,valid_seen);$finish;
    end
endmodule
