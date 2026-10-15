`timescale 1ns/1ps
// Actual physical job tile, actual compact output-pin taps. Fixed output
// calendar includes 16-beat PV and other concurrent sources with known gaps.
module tb_svc_payload_done;
    parameter integer MUT=0;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0;reg[32:0]j=0;reg[514:0]q=0;
    reg[25:0]a0=0,a1=0,x=0,od=0;
    wire[1:0]jd;wire[514:0]qo;
    dsfd_svcio_job #(.MUT(MUT))u(clk,rst_n,j,jd,q,qo,a0,a1,x,od);
    integer cyc=0,done_count=0,errors=0,expected_done=-1,r,sent;
    reg all_payload=0;
    function automatic[25:0]header(input[7:0]tag,input[2:0]src,input[11:0]len);
        header={len,1'b1,1'b0,src,tag,1'b1};
    endfunction
    function automatic[514:0]query(input[7:0]tag);
        reg[511:0]d;begin d=0;d[511:508]=1;d[502:495]=tag;query={2'b01,d,1'b1};end
    endfunction
    always @(posedge clk)begin
        cyc=cyc+1;#1;
        if(rst_n&&jd[0])begin
            done_count=done_count+1;
            if(!all_payload||cyc!=expected_done)begin errors=errors+1;$display("EARLY_OR_LATE_DONE cycle=%0d expected=%0d all_payload=%0d",cyc,expected_done,all_payload);end
        end
    end
    task tick;begin @(posedge clk);#2;end endtask
    task idle(input integer n);
        integer k;begin for(k=0;k<n;k=k+1)begin @(negedge clk);j=0;q=0;a0=0;a1=0;x=0;od=0;tick();end end
    endtask
    initial begin
        tick();@(negedge clk);rst_n=1;idle(8);
        @(negedge clk);j={1'b1,9'd0,8'd1,2'd0,5'b10011,8'h5a};tick();idle(8);
        @(negedge clk);q=query(8'h5a);tick();idle(8);
        // All three sources show END headers together. Their actual final
        // payloads are separated by the compiler's declared output slots.
        @(negedge clk);a0=header(8'h5a,0,16);a1=header(8'h5a,1,2);x=header(8'h5a,4,5);tick();
        sent=0;
        for(r=0;r<22;r=r+1)begin
            @(negedge clk);a0=0;a1=0;x=0;
            if(r<2)a1=26'd1;
            if(r<5)x=26'd1;
            if(r%4!=0&&sent<16)begin
                a0=26'd1;sent=sent+1;
                if(sent==16)begin all_payload=1;expected_done=cyc+3;end
            end
            tick();
        end
        idle(8);if(done_count!=1||jd[1])errors=errors+1;
        // A zero-body END completes at its header; there is no fictitious
        // payload delay and no dependence on another stream being valid.
        all_payload=0;expected_done=-1;
        @(negedge clk);j={1'b1,9'd0,8'd1,2'd0,5'b00001,8'h21};tick();idle(8);
        @(negedge clk);q=query(8'h21);tick();idle(8);
        @(negedge clk);a0=header(8'h21,0,0);all_payload=1;expected_done=cyc+3;tick();idle(8);
        if(done_count!=2||jd[1])errors=errors+1;
        $display("SVC_PAYLOAD_DONE jobs=%0d errors=%0d verdict=%s",done_count,errors,errors==0?"PASS":"FAIL");
        if(errors)$fatal(1,"service completion precedes actual payload");$finish;
    end
endmodule
