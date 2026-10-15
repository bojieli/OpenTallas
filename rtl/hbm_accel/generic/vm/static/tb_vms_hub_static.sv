`timescale 1ns/1ps
`default_nettype none
module tb_vms_hub_static;
    parameter integer MUT=0;
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
    reg [N*274-1:0] return_pipe[0:9];
    reg [N*2-1:0] seq_pipe[0:9];
    reg [8*266-1:0] bank_pipe[0:6];
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
            for(integer i=0;i<7;i=i+1) bank_pipe[i]<=0;
            pr<=0;
        end else if(auto_bank) begin
            for(integer b=0;b<8;b=b+1)
                bank_pipe[0][b*266+:266]<=
                    {pq[b*285+284],pq[b*285+283],pq[b*285+:8],
                     pq[b*285+283]?256'd0:read_value(b,int'(pq[b*285+272+:11]))};
            for(integer i=1;i<7;i=i+1) bank_pipe[i]<=bank_pipe[i-1];
            // pr is a wire-equivalent sampling of bank_pipe[5] here, so bank
            // input sampling -> pr presentation is six subsequent edges.
            pr<=bank_pipe[5];
        end
    end
    // Scoreboard predicts cq input -> pq in one subsequent edge and cr in ten.
    always @(posedge clk) begin
        if(rst_n&&auto_check) begin
            #1;
            if(pq!==prev_xpq) $fatal(1,"packet route mismatch edge %0d got %h expected %h",edges,pq,prev_xpq);
            if(cr!==return_pipe[9]) $fatal(1,"response/tag/latency mismatch edge %0d",edges);
            if(status!==0) $fatal(1,"unexpected status %b edge %0d",status,edges);
            for(integer c=0;c<N;c=c+1) if(cr[c*274+273]) checked=checked+1;
            for(integer i=9;i>0;i=i-1) begin return_pipe[i]=return_pipe[i-1];seq_pipe[i]=seq_pipe[i-1];end
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
            for(integer i=0;i<10;i=i+1)begin return_pipe[i]=0;seq_pipe[i]=0;end
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
        reg [289:0] expect_cw,expect_ccw;
        for(integer i=0;i<10;i=i+1)begin return_pipe[i]=0;seq_pipe[i]=0;end
        reset();
        // 4 packet slots / 10 edge roundtrip = 0.4 packet/client/cycle.
        // Five clients run together, distinct banks, and repeated slot reuse.
        // 1000 cycles at production NC=4 plus replay = 2000 exact responses.
        for(integer t=0;t<1000;t=t+1) begin
            clear_inputs();
            sid=2'(t/250);
            response_seq=seq_pipe[8];
            for(integer c=0;c<N;c=c+1)response_enable[c]=return_pipe[8][c*274+273];
            if(t%10<4) for(integer c=0;c<N;c=c+1) begin
                b=(c+t)%8;row=(t*17+c*37)%1024;seq=t%10;wr=(t+c)%3==0;
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
        for(integer drain=0;drain<16;drain=drain+1) begin
            clear_inputs();response_seq=seq_pipe[8];
            for(integer c=0;c<N;c=c+1)response_enable[c]=return_pipe[8][c*274+273];
            @(negedge clk);
        end
        if(checked!=issued||checked!=2000)$fatal(1,"throughput missing issued=%0d checked=%0d",issued,checked);
        $display("LOCAL_THROUGHPUT PASS responses=%0d issue_cycles=1000 packets_per_cycle=2.000 roundtrip_edges=10",checked);
        auto_check=0;auto_bank=0;sid=2;reset();pr=0;
        // Physical SID 2 is NW; CW dest 0+1, CCW dest3.
        // A mirror write requires all four visibility acknowledgements.
        addr=(32'd1<<20)|(32'd31<<8)|(32'd6<<5);data={8{32'hfedcba98}};
        cq[1*338+:338]={1'b1,1'b1,addr,data,32'hffffffff,16'hb123};client_seq[1*2+:2]=2;
        bank_enable=8'h40;bank_client[6*CW+:CW]=1;
        cw_enable=1;cw_client=1;ccw_enable=1;ccw_client=1;
        expect_cw={1'b1,4'b0011,4'd1,2'd2,1'b1,3'd6,1'b1,10'd31,8'hff,data};
        expect_ccw={1'b1,4'b1000,4'd1,2'd2,1'b1,3'd6,1'b1,10'd31,8'hff,data};
        @(negedge clk);clear_inputs();@(negedge clk);
        if(cwi!==expect_cw||cci!==expect_ccw||!pq[6*285+284])$fatal(1,"mirror routing mismatch");
        pulse_response(1,2,1,0,6);pulse_response(1,2,1,0,8);pulse_response(1,2,1,0,9);
        @(negedge clk);pr=0;cco0=0;cco1=0;
        repeat(3) begin @(negedge clk);if(cr!=0)$fatal(1,"mirror acknowledged before global visibility");end
        pulse_response(1,2,1,0,8);response_enable[1]=1;response_seq[2+:2]=2;
        @(negedge clk);clear_inputs();@(negedge clk);
        if(cr[274+:274]!=={1'b1,16'hb123,1'b1,256'd0})$fatal(1,"mirror final ack/tag mismatch");
        if(status!=0)$fatal(1,"mirror status %b",status);
        // Remote read to physical predecessor SID3 must use CCW only.
        @(negedge clk);clear_inputs();addr=(32'd3<<18)|(32'd9<<8)|(32'd2<<5);
        cq[338*2+:338]={1'b1,1'b0,addr,256'd0,32'd0,16'hca57};
        client_seq[4+:2]=1;ccw_enable=1;ccw_client=2;
        expect_ccw={1'b1,4'b1000,4'd2,2'd1,1'b0,3'd2,1'b0,10'd9,8'd0,256'd0};
        @(negedge clk);clear_inputs();@(negedge clk);
        if(cci!==expect_ccw||cwi!=0||pq!=0)$fatal(1,"remote unicast routing mismatch");
        pulse_response(2,1,0,256'h9876543210,9);response_enable[2]=1;response_seq[4+:2]=1;
        @(negedge clk);clear_inputs();@(negedge clk);
        if(cr[2*274+:274]!=={1'b1,16'hca57,1'b0,256'h9876543210})$fatal(1,"remote read data/tag mismatch");
        if(status!=0)$fatal(1,"remote status %b",status);
        // Compiler response edge is binding even when an acknowledgement is
        // absent. A later ack diagnoses identity misuse and never replays cr.
        @(negedge clk);clear_inputs();addr=(32'd2<<18);
        cq[0+:338]={1'b1,1'b0,addr,256'd0,32'd0,16'h1357};bank_enable=1;
        @(negedge clk);clear_inputs();repeat(3)@(negedge clk);
        response_enable[0]=1;response_seq[0+:2]=0;
        @(negedge clk);clear_inputs();@(negedge clk);
        if(!cr[273]||cr[272:257]!=16'h1357||!status[0])$fatal(1,"calendar mismatch: missing ack stalled return");
        pulse_response(0,0,0,256'h7654,0);@(negedge clk);clear_inputs();
        repeat(4) begin @(negedge clk);if(cr!=0)$fatal(1,"late ack replayed response");end
        reset();pr=0;
        // Missing compiler slot MUST fault rather than hold and dispatch later.
        @(negedge clk);clear_inputs();addr=(32'd2<<18);
        cq[0+:338]={1'b1,1'b0,addr,256'd0,32'd0,16'h1000};
        @(negedge clk);clear_inputs();repeat(2)@(negedge clk);
        if(!status[0]||pq!=0)$fatal(1,"unscheduled request did not fault");
        // Overwriting an active identity also faults and never stalls output.
        reset();pr=0;
        cq[0+:338]={1'b1,1'b0,addr,256'd0,32'd0,16'h1001};bank_enable=1;
        @(negedge clk);cq[0+:338]={1'b1,1'b0,addr,256'd0,32'd0,16'h1002};
        @(negedge clk);clear_inputs();@(negedge clk);
        if(!status[0]||!pq[284])$fatal(1,"active slot overwrite was not diagnosed/issued");
        $display("VMS_HUB_STATIC_BENCH PASS local=%0d mirror/calendar remote/read missing_ack/no_replay schedule_fault slot_overwrite",checked);
        $finish;
    end
endmodule
`default_nettype wire

// Real replay-only hub shape used by slices without local packet clients.
module tb_vms_hub_static_nc0;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0;
    reg [1:0] sid=3;
    reg [337:0] cq=0;
    reg [1:0] client_seq=0;
    reg [7:0] bank_enable=0,bank_client=0;
    reg cw_enable=0,ccw_enable=0,cw_client=0,ccw_client=0;
    wire [273:0] cr;
    wire [8*285-1:0] pq;
    reg [8*266-1:0] pr=0;
    wire [289:0] cwi,cci;
    reg [263:0] cco0=0,cco1=0;
    reg response_enable=0;
    reg [1:0] response_seq=0;
    wire [2:0] status;
    ot_vms_hub_static #(.NC(0)) dut(.*);
    initial begin
        repeat(3)@(negedge clk);rst_n=1;
        // A replay mirror write only touches this bank, never recirculates.
        cq={1'b1,1'b1,32'h001007a0,256'habcdef,32'hffffffff,16'hf1a9};
        bank_enable=8'h20;client_seq=3;
        @(negedge clk);cq=0;bank_enable=0;@(negedge clk);
        if(pq[5*285+:285]!=={1'b1,1'b1,1'b1,10'd7,256'habcdef,8'hff,4'd0,2'b00,2'd3})$fatal(1,"NC0 replay packet mismatch");
        if(cwi!=0||cci!=0)$fatal(1,"NC0 replay rebroadcast mirror");
        pr[5*266+:266]={1'b1,1'b1,4'd0,2'd0,2'd3,256'd0};
        @(negedge clk);pr=0;
        repeat(2)@(negedge clk);
        if(cr!=0)$fatal(1,"NC0 response ignored fixed calendar");
        response_enable=1;response_seq=3;
        @(negedge clk);response_enable=0;@(negedge clk);
        if(cr!=={1'b1,16'hf1a9,1'b1,256'd0}||status!=0)$fatal(1,"NC0 return mismatch");
        $display("VMS_HUB_STATIC_NC0 PASS replay_mirror_no_broadcast fixed_calendar");$finish;
    end
endmodule
