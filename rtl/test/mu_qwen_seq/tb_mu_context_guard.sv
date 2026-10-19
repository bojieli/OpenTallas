`timescale 1ns/1ps
module tb_mu_context_guard;
    parameter integer MUT = 0;
    reg ck=0; always #5 ck=~ck;
    reg rst_n=0, load=0, consume=0, result_write=0;
    reg [2:0] mask=0; reg [1:0] cu=0,ru=0;
    wire fault;
    qfd_mu_context_guard #(.NU(4),.MUT(MUT)) dut(.ck(ck),.rst_n(rst_n),.load(load),.load_mask(mask),
        .consume(consume),.consume_user(cu),.result_write(result_write),.result_user(ru),.fault(fault));
    task tick; begin @(posedge ck); #1; @(negedge ck); end endtask
    integer errors=0;
    initial begin
        tick; rst_n=1; tick;
        load=1; mask=3'b101; tick; load=0;
        // Independent users: consume user1, then its result is legal; user3 remains pending.
        consume=1; cu=1; tick; consume=0;
        result_write=1; ru=1; tick; result_write=0;
        if(fault) errors=errors+1;
        // User0 and a never-loaded filler are outside the fresh-context invariant.
        result_write=1; ru=0; tick; ru=2; tick; result_write=0;
        if(fault) errors=errors+1;
        // Known-boundary retire/re-admit user1; omitted INIT overwrites pending context.
        load=1; mask=3'b001; tick; load=0;
        result_write=1; ru=1; tick; result_write=0;
        if(!fault) errors=errors+1;
        repeat(3) tick;
        if(!fault) errors=errors+1;
        rst_n=0; tick; rst_n=1; tick;
        if(fault) errors=errors+1;
        // A same-edge first consume/result is rejected, independent of NBA order.
        load=1; mask=3'b100; tick; load=0;
        consume=1; cu=3; result_write=1; ru=3; tick; consume=0; result_write=0;
        if(!fault) errors=errors+1;
        if(errors) $display("MU_CONTEXT_GUARD FAIL errors=%0d",errors);
        else $display("MU_CONTEXT_GUARD PASS");
        $finish;
    end
endmodule
