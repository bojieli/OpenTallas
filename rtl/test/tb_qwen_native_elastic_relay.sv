`timescale 1ns/1ps
module tb_qwen_native_elastic_relay;
    parameter integer W=546, NF=2, N=256, NEG=0, STALL=1;
    reg clk=0,rst_n=0,go=0;
    always #0.555556 clk=~clk;
    integer issued=0,sent=0,received=0,bad=0,cycle=0,first=-1,last=-1,firstcr=-1,credit_count=0;
    reg src_v=0;
    reg [W-1:0] offered=0;
    wire ready;
    wire [W-1:0] data[0:NF]; wire valid[0:NF],cr[0:NF]; wire faults[NF-1:0];
    ot_link_credit_tx #(.W(W),.CRED(4)) source(
        .clk(clk),.rst_n(rst_n),.i_valid(src_v),.i_ready(ready),.i_data(offered),
        .l_valid(valid[0]),.l_data(data[0]),.l_credit(cr[0]));
    genvar j;
    generate for(j=0;j<NF;j=j+1) begin:g_relay
        ot_qwen_native_elastic_relay #(.W(W),.DEPTH(8),.OCRED(j==NF-1?4:8),.ENABLE(1)) u(
            .clk(clk),.rst_n(rst_n),.i_v(valid[j]),.i_d(data[j]),.i_cr(cr[j]),
            .o_v(valid[j+1]),.o_d(data[j+1]),.o_cr(cr[j+1]),.fault(faults[j]));
    end endgenerate
    wire ov,sinkfault;wire [W-1:0] od;
    // Deterministic stalls exercise finite occupancy without a whole die.
    reg take=0;
    wire realcr;
    assign cr[NF]=NEG==2 ? 1'b1 : realcr;
    ot_link_credit_rx #(.W(W),.DEPTH(4),.WFREE(1)) sink(
        .clk(clk),.rst_n(rst_n),.l_valid(valid[NF]),.l_data(data[NF]),.l_credit(realcr),
        .o_valid(ov),.o_ready(take),.o_data(od),.fault(sinkfault));
    reg [W-1:0] expected[0:N-1];integer k;
    always @(negedge clk) begin
        take=!STALL || (cycle%31)>10;
        src_v=go && issued<N;
        for(k=0;k<W;k=k+1) offered[k]=((issued*13+k*7)>>(k%16))&1;
    end
    always @(posedge clk) begin
        cycle=cycle+1;
        if(go) begin
            if(src_v && ready) issued=issued+1;
            if(valid[0]) begin
                expected[sent]=data[0]; sent=sent+1;
                if(first<0) first=cycle;
                last=cycle;
            end
            if(cr[0]) begin credit_count=credit_count+1; if(firstcr<0)firstcr=cycle;end
            if(ov && take) begin
                if(received>=sent || od!==expected[received])begin
                    if(bad<3)$display("MISMATCH at=%0d expected=%h actual=%h",received,expected[received][31:0],od[31:0]);
                    bad=bad+1;
                end
                received=received+1;
            end
        end
        if(cycle>100+N*50) $fatal(1,"elastic deadlock sent=%0d received=%0d",sent,received);
    end
    initial begin
        repeat(10) @(negedge clk);rst_n=1;repeat(10) @(negedge clk);go=1;
        if(NEG)wait(sinkfault || faults[0] || faults[NF-1]);
        else wait(received>=N);
        repeat(30) @(negedge clk);
        if(NEG) begin
            if(sinkfault || bad || (|{faults[0],faults[NF-1]}))
                $display("NEG_DETECTED elastic width=%0d negative=%0d bad=%0d",W,NEG,bad);
            else $fatal(1,"negative missed");
        end else begin
            if(sent!=N || received!=N || bad || sinkfault || faults[0] || faults[NF-1])
                $fatal(1,"elastic mismatch sent=%0d received=%0d bad=%0d",sent,received,bad);
            $display("PASS elastic width=%0d relays=%0d words=%0d first_credit_cycles=%0d launch_window=%0d",W,NF,N,firstcr-first,last-first+1);
        end
        $finish;
    end
endmodule
