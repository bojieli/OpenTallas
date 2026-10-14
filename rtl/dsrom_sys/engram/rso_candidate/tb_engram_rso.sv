`timescale 1ns/1ps
module tb_engram_rso;
    reg clk=0, rst_n=0, ticking=0;
    always #5 if (ticking) clk=~clk; else clk=0;
    wire rso; wire [1:0] c_st;
    dsfd_engram_c_rso dut(.ck(clk),.rst(rst_n),.c_cmd(85'd0),.f_cfg(3'd0),
        .f_win(73'd0),.f_agc(1'b0),.f_ai(1124'd0),.f_vm(16'd0),.f_hr(265'd0),
        .c_st(c_st),.rso(rso));
    task step(input integer n);
        repeat(n) begin @(posedge clk); #1; end
    endtask
    initial begin
        #12;
        if (rso !== 0) $fatal(1,"ACK FAIL: asserted during reset");
        rst_n=1;
        #100;
        if (rso !== 0) $fatal(1,"ACK FAIL: release without running clocks");
        ticking=1; step(24);
        if (rso !== 1) $fatal(1,"ACK FAIL: no release with all domains running");
        rst_n=0; #1;
        if (rso !== 0) $fatal(1,"ACK FAIL: reset assertion did not revoke ACK");
        // Fault: final PB2 release state cannot leave reset. Its parent
        // conditioner and IO online witness are still allowed to become high.
        force dut.u_pb2.u_b.rs_q = 2'b00;
        rst_n=1; step(24);
        if (!dut.rst_pb2_n || !c_st[1]) $fatal(1,"ACK FAIL: fault did not isolate final child release");
        if (rso !== 0) $fatal(1,"ACK FAIL: high with PB2 final release held low");
        release dut.u_pb2.u_b.rs_q;
        step(24);
        if (rso !== 1) $fatal(1,"ACK FAIL: did not recover after final release restored");
        force dut.u_io.u_ep.u_ad.u_cmd.u_fifo.rd_domain_rst_n = 1'b0;
        step(4);
        if (!dut.u_io.rn || !c_st[1]) $fatal(1,"ACK FAIL: fault did not isolate nested FIFO release");
        if (rso !== 0) $fatal(1,"ACK FAIL: high with IO FIFO final release held low");
        release dut.u_io.u_ep.u_ad.u_cmd.u_fifo.rd_domain_rst_n;
        step(24);
        if (rso !== 1) $fatal(1,"ACK FAIL: did not recover after FIFO release restored");
        rst_n=0; #1;
        if (rso !== 0) $fatal(1,"ACK FAIL: repeated reset assertion did not revoke ACK");
        ticking=0; #10; rst_n=1; #100;
        if (rso !== 0) $fatal(1,"ACK FAIL: repeated release without clocks");
        ticking=1; step(24);
        if (rso !== 1) $fatal(1,"ACK FAIL: repeated epoch not acknowledged");
        $display("ENGRAM_RSO_ACK PASS: stopped clock, held final child, held nested FIFO, asynchronous assertion, repeated epoch");
        $finish;
    end
    initial begin #10000; $fatal(1,"ACK FAIL: timeout"); end
endmodule
