`timescale 1ns/1ps
module tb_dsfd_be_fault_local_reset;
    localparam N=10;
    reg ck=0, running=1, raw_rst=0;
    reg forwarded_rn0=1; // deliberately stale/high throughout the raw pulse
    reg [15:0] i=16'ha55a;
    always #5 if(running) ck=~ck;
    // Explicit TEST_ONLY independent controller clock/reset. Parent unbound.
    reg ack_ck=0, ack_rn=0;
    always #7 ack_ck=~ack_ck;
    wire [15:0] o; wire[N-1:0] acks, collected;
    wire all_acked;
    dsfd_be_fault_path #(.STAGES(N),.LOCAL_RN(1)) u (
        .ck(ck),.rn(forwarded_rn0),.raw_rst(raw_rst),.i(i),.o(o),.conditioner_ack(acks));
    dsfd_be_fault_ack_collect #(.N(N)) u_collect (
        .ck(ack_ck),.rn(ack_rn),.i(acks),.o(collected),.all_acked(all_acked));
    reg[N-1:0] probe_i=0;
    wire[N-1:0] probe_o; wire probe_all;
    dsfd_be_fault_ack_collect #(.N(N)) u_probe (
        .ck(ack_ck),.rn(ack_rn),.i(probe_i),.o(probe_o),.all_acked(probe_all));
    wire [16*N-1:0] consumers;
    genvar s;
    generate for(s=0;s<N;s=s+1) begin:g_watch
        assign consumers[16*s+:16] = u.g_stage[s].u_r.o;
    end endgenerate
    reg[N-1:0] m0=0,m1=0,p0=0,p1=0;
    integer errors=0,checks=0,k=0;
    always @(negedge ack_ck) begin
        probe_i = (10'b1 << (k%10)) | (10'h3ff >> (k%10)); k=k+1;
    end
    always @(posedge ack_ck) begin
        m1=ack_rn?m0:0; m0=ack_rn?acks:0;
        p1=ack_rn?p0:0; p0=ack_rn?probe_i:0;
        #1;
        if(collected!==m1 || probe_o!==p1 || all_acked!==(&m1) || probe_all!==(&p1)) begin
            $display("FAIL individual ordinary2FF ACK collection k=%0d got=%h/%h expected=%h/%h",k,collected,probe_o,m1,p1);errors=errors+1;
        end
        checks=checks+1;
    end
    task fail(input [255:0] reason);
        begin $display("FAIL %s",reason);errors=errors+1;end
    endtask
    initial begin
        repeat(4) @(negedge ck);
        raw_rst=1;ack_rn=1;
        repeat(N+8) @(negedge ck);
        #1;
        if(o!==16'ha55a || consumers!=={N{16'ha55a}} || acks!=={N{1'b1}})fail("warm pipeline did not fill");
        @(negedge ck); running=0;
        #2;raw_rst=0;
        #1;
        if(acks!==0)fail("raw pulse did not clear local ACK while clock stopped");
        if(forwarded_rn0!==1)fail("forwarded RN fixture not held high");
        #28;raw_rst=1;
        #1;
        if(acks!==0)fail("local ACK rose without two clock edges");
        if(consumers!=={N{16'ha55a}})fail("sync consumers changed without a clock");
        running=1;
        @(posedge ck);#1;
        if(consumers!==0)fail("consumers not zero before ACK rise");
        if(acks!==0)fail("local ACK rose at first edge");
        @(posedge ck);#1;
        if(consumers!==0 || acks!=={N{1'b1}})fail("second-edge reset-release waveform wrong");
        @(negedge ck);i=0;
        repeat(6) @(negedge ack_ck);
        #1;
        if(!all_acked || collected!=={N{1'b1}})fail("individual ACKs not captured twice");
        $display("RESULT local_stages=10 data_FF=160 conditioner_FF=20 controller_request_FF=20 checks=%0d errors=%0d raw_clock_stopped=1 forwarded_rn0_held_high=1 controller_clock=TEST_ONLY_independent",checks,errors);
        if(errors) $fatal(1,"FAIL");
        $display("PASS LOCAL_RAW_RESET_AND_INDIVIDUAL_ACK");$finish;
    end
endmodule
