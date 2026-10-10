`timescale 1ns/1ps
module mtp_test_relay #(parameter integer W=1,HOPS=0)(
    input wire clk,rst_n,input wire [W-1:0] in_data,output wire [W-1:0] out_data);
    generate if (HOPS==0) begin assign out_data=in_data; end
    else begin
        reg [W-1:0] pipe [0:HOPS-1]; integer i;
        always @(posedge clk) begin
            if (!rst_n) for(i=0;i<HOPS;i=i+1) pipe[i]<='0;
            else begin pipe[0]<=in_data;for(i=1;i<HOPS;i=i+1)pipe[i]<=pipe[i-1];end
        end
        assign out_data=pipe[HOPS-1];
    end endgenerate
endmodule
module tb_mtp_link_rtt;
    parameter integer F=5,R=5,SEL=0,ENABLE=1,STRESS=1,DEPTH=0,OUTPUT_PIPE=0;
    localparam integer W=512,H=F+R+3,D=DEPTH>0?DEPTH:H+1,TOTAL=1200;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,sv=0,cr=0;
    wire sr,lv,lr,rv,rg,cv,tg;
    wire [W-1:0] sd,ld,rd,cd;
    reg prior_stall=0; reg [W-1:0] prior_data;
    integer cycle=0,sent=0,received=0,stalls=0,drain=0,max_outstanding=0,first_sent=-1,first_received=-1;
    function automatic [511:0] payload(input integer number);
        integer k;reg [31:0] word;
        begin
            for(k=0;k<16;k=k+1) begin
                word=(32'h9e3779b9*(number+1))^(32'h01010101*k)^32'hbad05eed;
                payload[k*32+:32]=word;
            end
        end
    endfunction
    assign sd=payload(sent);
    ot_dsrom_mtp_ltx #(.W(W)) tx(.clk(clk),.rst_n(rst_n),.c_valid(sv),.c_ready(sr),.c_data(sd),
        .l_valid(lv),.l_ready(tg),.l_data(ld));
    mtp_test_relay #(.W(W+1),.HOPS(F)) forward(.clk(clk),.rst_n(rst_n),.in_data({lv,ld}),.out_data({rv,rd}));
    mtp_test_relay #(.W(1),.HOPS(R)) reverse(.clk(clk),.rst_n(rst_n),.in_data(rg),.out_data(tg));
    ot_dsrom_mtp_lrx_rtt #(.W(W),.D(D),.SEL(SEL),.ENABLE_RTT(ENABLE),.OUTPUT_PIPE(OUTPUT_PIPE),.FORWARD_HOPS(F),.RETURN_HOPS(R)) rx(
        .clk(clk),.rst_n(rst_n),.l_valid(rv),.l_ready(rg),.l_data(rd),.c_valid(cv),.c_ready(cr),.c_data(cd));
    initial begin repeat(8) @(negedge clk);rst_n=1; end
    always @(negedge clk) if(rst_n) begin
        sv=(sent<TOTAL)&&(!STRESS||(cycle<300)||(cycle%13!=5 && cycle%13!=6));
        // A sudden long stall after steady traffic exposes forgotten grants.
        cr=!STRESS||(!(cycle>=40 && cycle<240) && !(cycle%400>=320) && (cycle%7!=0));
    end
    always @(posedge clk) if(rst_n) begin
        cycle<=cycle+1;
        if(OUTPUT_PIPE && prior_stall && (!cv || cd!==prior_data))
            $fatal(1,"ELASTIC_OUTPUT_CHANGED_DURING_STALL");
        prior_stall<=cv&&!cr; prior_data<=cd;
        if(!STRESS && first_sent>=0 && sent<TOTAL && !sr)$fatal(1,"FULL_RATE_GAP sent=%0d",sent);
        if(sv&&sr) begin sent<=sent+1;if(first_sent<0)first_sent<=cycle;end
        if(cv&&cr) begin
            if(received>=sent) $fatal(1,"UNEXPECTED_OR_DUPLICATE flit=%0d sent=%0d",received,sent);
            if(cd!==payload(received)) $fatal(1,"PAYLOAD_OR_ORDER_MISMATCH flit=%0d",received);
            received<=received+1;if(first_received<0)first_received<=cycle;
        end
        if(cv&&!cr)stalls<=stalls+1;
        if(sent-received>max_outstanding)max_outstanding<=sent-received;
        if(sent==TOTAL && received==TOTAL)begin
            if(cv) $fatal(1,"EXTRA_FLIT_AFTER_DRAIN");
            drain<=drain+1;
            if(drain>2*H+8)begin
                $display("PASS RTT_LINK W=%0d F=%0d R=%0d H=%0d D=%0d SEL=%0d ENABLE=%0d STRESS=%0d sent=%0d received=%0d cycles=%0d stalls=%0d max_outstanding=%0d first_latency=%0d",W,F,R,H,D,SEL,ENABLE,STRESS,sent,received,cycle,stalls,max_outstanding,first_received-first_sent);
                $finish;
            end
        end
        if(cycle>20000)$fatal(1,"LINK_DRAIN_TIMEOUT sent=%0d received=%0d",sent,received);
    end
endmodule
