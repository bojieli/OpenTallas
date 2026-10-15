`timescale 1ns/1ps
module tb_qfd_x3_mux_native;
    parameter integer MUT=0;
    reg ck=0, rst_n=0;
    always #5 ck=!ck;
    reg [523:0] q=0;
    reg kvn_v=0; reg [511:0] kvn_d=0; reg [10:0] kvn_tag=0;
    reg slot_v=0,slot_q=0;
    wire x3_v,fault; wire [511:0] x3_d; wire [10:0] x3_tag;
    ot_qfd_x3_mux_native #(.MUT(MUT)) dut(.*);
    integer qs=0,ks=0,qe=0,ke=0,cycles=0,epoch=0,phase=0;
    reg expect_v=0,expect_q=0,prior_v=0,prior_q=0;
    reg fault_phase=0;
    reg release_phase=0;
    localparam integer N=1024;
    function [511:0] data(input integer isq,input integer seq,input integer ep);
        integer i;
        begin
            for(i=0;i<16;i=i+1) data[32*i+:32]=(32'h93450000 ^ (ep<<20) ^ (isq<<19) ^ seq ^ (i<<12));
        end
    endfunction
    always @(posedge ck) begin
        if(!rst_n) begin qs=0;ks=0;qe=0;ke=0;cycles=0;expect_v=0;expect_q=0;prior_v=0;prior_q=0; end
        else if(release_phase) begin
            if(x3_v || fault)$fatal(1,"activity on the reset release edge");
        end else begin
            cycles=cycles+1;
            if(q[523])qs=qs+1;
            if(kvn_v)ks=ks+1;
            if(!fault_phase && x3_v!==expect_v)$fatal(1,"changed compiled dispatch timeline at cycle%0d",cycles);
            if(x3_v) begin
                if(expect_q) begin
                    if(qe>=qs || x3_d!==data(1,qe,epoch) || x3_tag!=={3'b001,2'b00,1'b0,5'(qe%32)})
                        $fatal(1,"Q data/tag/order mismatch epoch%0d word%0d",epoch,qe);
                    qe=qe+1;
                end else begin
                    if(ke>=ks || x3_d!==data(0,ke,epoch) || x3_tag!=={3'b010,2'b01,6'(ke%64)})
                        $fatal(1,"KVN data/tag/order mismatch epoch%0d word%0d",epoch,ke);
                    ke=ke+1;
                end
            end
            expect_v=prior_v;expect_q=prior_q;prior_v=slot_v;prior_q=slot_q;
            if(!fault_phase && fault)$fatal(1,"unexpected scheduled mux fault");
            if(cycles>10000)$fatal(1,"schedule deadline missed");
        end
    end
    task run_epoch;
        begin
            @(negedge ck);rst_n=0;q=0;kvn_v=0;slot_v=0;
            repeat(3)@(negedge ck);rst_n=1;
            // Reset release edge (pin register, +1 edge): a valid Q and KVN word presented on the first edge after
            // rst_n rises must be ignored. A design that captures it (reset bypass) emits a stale word / faults.
            release_phase=1;
            q={1'b1,3'b001,2'b00,1'b0,5'd31,~data(1,0,epoch)};
            kvn_v=1;kvn_tag={3'b010,2'b01,6'd63};kvn_d=~data(0,0,epoch);
            @(negedge ck);release_phase=0;
            // Fixed eight-cycle calendar: Q arrives 0,2; KVN arrives 1,3;
            // Q dispatches 2,4; KVN dispatches 3,5. Output captured two edges later (explicit pin input station).
            for(phase=0;phase<4096;phase=phase+1) begin
                q=0;kvn_v=0;slot_v=0;slot_q=0;
                if(phase%8==0 || phase%8==2)
                    q={1'b1,3'b001,2'b00,1'b0,5'(qs%32),data(1,qs,epoch)};
                if(phase%8==1 || phase%8==3) begin
                    kvn_v=1;kvn_tag={3'b010,2'b01,6'(ks%64)};kvn_d=data(0,ks,epoch);
                end
                slot_v=phase%8>=2 && phase%8<=5;
                slot_q=phase%8==2 || phase%8==4;
                @(negedge ck);
            end
            q=0;kvn_v=0;slot_v=0;
            repeat(3)@(negedge ck);
            if(qe!=N || ke!=N)$fatal(1,"missing scheduled output Q%0d KVN%0d",qe,ke);
            $display("EPOCH %0d PASS Q%0d KVN%0d calendar4096 cycles%0d",epoch,qe,ke,cycles);
        end
    endtask
    initial begin
        run_epoch();epoch=1;run_epoch();
        // Fault injection verifies a missed slot terminates, with no delayed retry.
        @(negedge ck);fault_phase=1;slot_v=1;slot_q=1;
        @(negedge ck);slot_v=0;
        @(negedge ck);
        @(negedge ck);
        if(!fault || x3_v)$fatal(1,"empty reserved slot did not fault without rescheduling");
        $display("PASS native static Q/KVN slots, full512b data, two epochs, underflow fault");$finish;
    end
endmodule
