`timescale 1ns/1ps
`default_nettype none
module tb_vms_hub_rd1_resp;
    parameter integer MUT=0;
    parameter integer RD1=1;        // rd1 bank body: +1 edge on every bank echo (read data and write ack)
    parameter integer EXPECT_TRIP=0; // 1: negative control, the sticky fault status[0] must trip
    parameter integer PERIOD=10;     // slot period: a slot is reused after PERIOD edges, >= response latency (9+RD1)
    parameter RESP_FILE="resp.mem";
    localparam NC=4,N=5,CW=3;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0; reg [1:0] sid=2;
    reg [N*338-1:0] cq=0;
    reg [N*2-1:0] client_seq=0;
    reg [7:0] bank_enable=0;
    reg [8*CW-1:0] bank_client=0;
    reg cw_enable=0,ccw_enable=0;
    reg [CW-1:0] cw_client=0,ccw_client=0;
    wire [N*274-1:0] cr;
    wire [8*285-1:0] pq;
    reg [8*266-1:0] pr=0;
    wire [289:0] cwi,cci;
    reg [263:0] cco0=0,cco1=0;
    wire [2:0] status;
    reg [N-1:0] response_enable=0;
    reg [N*2-1:0] response_seq=0;
    ot_vms_hub_static #(.NC(NC),.MUT(MUT)) dut(.*);
    reg [8*285-1:0] xpq=0,prev_xpq=0;
    reg [N*274-1:0] xcr=0;
    reg [N*274-1:0] return_pipe[0:11];
    reg [N*2-1:0] seq_pipe[0:11];
    reg [8*266-1:0] bank_pipe[0:7];
    reg [14:0] resp_cal[0:2047];
    integer trip_edge=-1;
    reg auto_bank=1,auto_check=1;
    integer checked=0,issued=0,edges=0;
    // Observable bank contents are address dependent, so wrong row/bank routing
    // cannot pass by returning one constant. Write acknowledgements carry zero.
    function automatic [255:0] read_value(input integer bank,input integer row);
        reg [31:0] word;
        begin word=32'had530000^(32'(bank)<<12)^32'(row); read_value={8{word}}; end
    endfunction
    always @(posedge clk) begin
        if(!rst_n) begin
            for(integer i=0;i<8;i=i+1) bank_pipe[i]<=0;
            pr<=0;
        end else if(auto_bank) begin
            for(integer b=0;b<8;b=b+1)
                bank_pipe[0][b*266+:266]<=
                    {pq[b*285+284],pq[b*285+283],pq[b*285+:8],
                     pq[b*285+283]?256'd0:read_value(b,int'(pq[b*285+272+:11]))};
            for(integer i=1;i<8;i=i+1) bank_pipe[i]<=bank_pipe[i-1];
            // pr is a wire-equivalent sampling of bank_pipe[5] here, so bank
            // input sampling -> pr presentation is six subsequent edges.
            pr<=bank_pipe[5+RD1];
        end
    end
    // Scoreboard predicts cq input -> pq in one subsequent edge and cr in ten.
    always @(posedge clk) begin
        if(rst_n&&auto_check) begin
            #1;
            if(pq!==prev_xpq) $fatal(1,"packet route mismatch edge %0d got %h expected %h",edges,pq,prev_xpq);
            if(status[0]&&trip_edge<0) trip_edge=edges;
            if(!EXPECT_TRIP) begin
                if(cr!==return_pipe[9+RD1]) $fatal(1,"response/tag/latency mismatch edge %0d",edges);
                if(status!==0) $fatal(1,"unexpected status %b edge %0d",status,edges);
            end
            for(integer c=0;c<N;c=c+1) if(cr[c*274+273]) checked=checked+1;
            for(integer i=11;i>0;i=i-1) begin return_pipe[i]=return_pipe[i-1];seq_pipe[i]=seq_pipe[i-1];end
            return_pipe[0]=xcr;seq_pipe[0]=client_seq;
            prev_xpq=xpq; edges=edges+1;
        end
    end
    task clear_inputs;
        begin response_enable=0;response_seq=0;cq=0;client_seq=0;bank_enable=0;bank_client=0;cw_enable=0;ccw_enable=0;cco0=0;cco1=0;xpq=0;xcr=0; end
    endtask
    task reset;
        begin
            @(negedge clk);rst_n=0;clear_inputs();
            for(integer i=0;i<12;i=i+1)begin return_pipe[i]=0;seq_pipe[i]=0;end
            prev_xpq=0; repeat(3)@(negedge clk);rst_n=1;
        end
    endtask
    task pulse_response(input integer client,input integer seq,input bit wr,input [255:0] data,input integer source);
        begin
            @(negedge clk);pr=0;cco0=0;cco1=0;
            if(source<8)pr[source*266+:266]={1'b1,wr,4'(client),2'b00,2'(seq),data};
            else if(source==8)cco0={1'b1,4'(client),2'(seq),wr,data};
            else cco1={1'b1,4'(client),2'(seq),wr,data};
        end
    endtask
    initial begin : bench
        integer b,row,seq;
        reg wr; reg [31:0] addr; reg [255:0] data;
        reg [15:0] tag;
        $readmemh(RESP_FILE,resp_cal);
        for(integer i=0;i<12;i=i+1)begin return_pipe[i]=0;seq_pipe[i]=0;end
        reset();
        // Same traffic as tb_vms_hub_static (5 clients, 4 slots, 10 edge slot period), but the response_enable /
        // response_seq inputs are the COMPILER calendar from gen_resp_cal.py (shift_response), not derived from the
        // expected data pipe.  Pass requires bank echo and calendar to agree: calendar = request + 9 + RD1.
        for(integer t=0;t<1000+24;t=t+1) begin
            clear_inputs();
            sid=2'(t/250>3?3:t/250);
            response_enable=resp_cal[t][4:0];
            response_seq=resp_cal[t][14:5];
            if(t<1000 && t%PERIOD<4) for(integer c=0;c<N;c=c+1) begin
                b=(c+t)%8;row=(t*17+c*37)%1024;seq=t%PERIOD;wr=(t+c)%3==0;
                addr=(32'(sid)<<18)|(32'(row)<<8)|(32'(b)<<5);
                data={8{32'h12340000^32'(t*31+c)}};tag=16'(t*5+c+100);
                cq[c*338+:338]={1'b1,wr,addr,data,32'hffffffff,tag};
                client_seq[c*2+:2]=2'(seq);
                bank_enable[b]=1;bank_client[b*CW+:CW]=CW'(c);
                xpq[b*285+:285]={1'b1,wr,1'b0,10'(row),data,8'hff,4'(c),2'b00,2'(seq)};
                xcr[c*274+:274]={1'b1,tag,wr,wr?256'd0:read_value(b,row)};
                issued=issued+1;
            end
            @(negedge clk);
        end
        if(EXPECT_TRIP) begin
            if(trip_edge<0) $fatal(1,"RD1_BENCH no sticky fault: the wrong response calendar was not caught");
            $display("RD1_BENCH TRIP status[0] sticky fault at edge %0d (expected for the negative control) checked=%0d",trip_edge,checked);
        end else begin
            if(checked!=issued||issued<1500)$fatal(1,"throughput missing issued=%0d checked=%0d",issued,checked);
            $display("RD1_BENCH PASS reads+writes=%0d of %0d issued, sticky fault 0, cr latency %0d",checked,issued,10+RD1);
        end
        $finish;
    end
endmodule
`default_nettype wire
