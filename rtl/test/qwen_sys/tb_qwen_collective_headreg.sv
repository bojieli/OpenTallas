`timescale 1ns/1ps
// New differential gate: independently stalled producers, depth/wrap/bypass,
// mixed reduce/gather, rank-order cancellation and mismatched tags. The original
// engine is an arithmetic/protocol reference, not a replay of an old campaign.
module tb_qwen_collective_headreg;
    parameter integer DEPTH = 2;
    parameter integer BAD_TAG = 0;
    localparam integer N=4, W=120, MAXOUT=480;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0;
    integer cyc=0, sent[0:1][0:3], received[0:1][0:3], mismatch=0;
    wire [3:0] valid[0:1], ready[0:1], last[0:1], mode[0:1], ov[0:1], ol[0:1], oe[0:1], fault[0:1];
    wire [127:0] data[0:1], od[0:1], tag[0:1];
    wire [7:0] rank[0:1];
    wire [11:0] code[0:1];
    reg [34:0] captured[0:1][0:3][0:MAXOUT-1];
    integer i,j,k;
    function [31:0] sample(input integer index, input integer r);
        // ((2^24 + 1) + -2^24) + 1 is 1, not 2: order matters.
        if (index % 2 == 0)
            case(r) 0:sample=32'h4b800000; 1:sample=32'h3f800000;
                    2:sample=32'hcb800000; 3:sample=32'h3f800000; endcase
        else case(r) 0:sample=32'h3f800000; 1:sample=32'h40000000;
                    2:sample=32'h40400000; 3:sample=32'h40800000; endcase
    endfunction
    genvar b,r;
    generate for(b=0;b<2;b=b+1) begin: g_model
        for(r=0;r<4;r=r+1) begin: g_rank
            assign valid[b][r] = sent[b][r]<W && ((cyc+r*3)%(r+3)!=0);
            assign data[b][r*32+:32] = sample(sent[b][r],r);
            assign mode[b][r] = sent[b][r]%12>=8;
            assign last[b][r] = sent[b][r]%4==3;
            assign tag[b][r*32+:32] = sent[b][r]/4 + ((BAD_TAG && r==2 && sent[b][r]==45)? 1:0);
        end
        if(b==0) begin: g_old
            ot_rom_oneshot_allreduce #(.LANES(1),.DEPTH(DEPTH),.LAT(3),.BPC_NUM(4)) dut(
                .clk(clk),.rst_n(rst_n),.in_valid(valid[b]),.in_ready(ready[b]),.in_data(data[b]),
                .in_last(last[b]),.in_mode(mode[b]),.in_tag(tag[b]),.out_valid(ov[b]),.out_data(od[b]),
                .out_last(ol[b]),.out_rank(rank[b]),.out_err(oe[b]),.fault(fault[b]),.fault_code(code[b]),.link_stalls());
        end else begin: g_new
            ot_rom_oneshot_allreduce_headreg #(.REGISTER_HEAD(1),.LANES(1),.DEPTH(DEPTH),.LAT(3),.BPC_NUM(4)) dut(
                .clk(clk),.rst_n(rst_n),.in_valid(valid[b]),.in_ready(ready[b]),.in_data(data[b]),
                .in_last(last[b]),.in_mode(mode[b]),.in_tag(tag[b]),.out_valid(ov[b]),.out_data(od[b]),
                .out_last(ol[b]),.out_rank(rank[b]),.out_err(oe[b]),.fault(fault[b]),.fault_code(code[b]),.link_stalls());
        end
    end endgenerate
    initial begin
        for(i=0;i<2;i=i+1) for(j=0;j<4;j=j+1) begin received[i][j]=0; sent[i][j]=0; end
        repeat(5) @(negedge clk); rst_n=1;
    end
    always @(posedge clk) if(rst_n) begin
        for(i=0;i<2;i=i+1) begin
            for(j=0;j<4;j=j+1) if(valid[i][j] && ready[i][j]) sent[i][j]<=sent[i][j]+1;
        end
    end
    // Arrival times vary by rank. Compare accepted output sequences, including
    // rank/last, independently at all four dies instead of comparing clocks.
    always @(negedge clk) if(rst_n) begin
        cyc=cyc+1;
        for(i=0;i<2;i=i+1) for(j=0;j<4;j=j+1) if(ov[i][j]) begin
            if(received[i][j]>=MAXOUT || oe[i][j]!=0) $fatal(1,"output/error");
            captured[i][j][received[i][j]]={ol[i][j],rank[i][j*2+:2],od[i][j*32+:32]};
            received[i][j]=received[i][j]+1;
        end
        if(received[0][0]==240 && received[0][1]==240 && received[0][2]==240 && received[0][3]==240 &&
           received[1][0]==240 && received[1][1]==240 && received[1][2]==240 && received[1][3]==240) begin
            for(j=0;j<4;j=j+1) for(k=0;k<240;k=k+1) if(captured[0][j][k]!==captured[1][j][k]) mismatch=mismatch+1;
            if(mismatch || code[0]!==code[1] || (BAD_TAG ? fault[1]!=4'b1111 : fault[1]!=0)) $fatal(1,"mismatch=%0d faults=%h/%h",mismatch,code[0],code[1]);
            $display("HEADREG PASS depth=%0d badtag=%0d records=%0d cycles=%0d",DEPTH,BAD_TAG,received[1][0],cyc);
            $finish;
        end
    end
endmodule
