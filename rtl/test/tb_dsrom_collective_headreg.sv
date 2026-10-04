`timescale 1ns/1ps
// New differential gate: independently stalled producers, depth/wrap/bypass,
// mixed reduce/gather, rank-order cancellation and mismatched tags. The original
// engine is an arithmetic/protocol reference, not a replay of an old campaign.
module tb_dsrom_collective_headreg;
    parameter integer DEPTH = 4;
    parameter integer RELAY = 1;
    parameter integer GW = 4;
    parameter integer PAIRWISE = 1;
    parameter integer BAD_TAG = 0;
    localparam integer N=4, W=120, MAXOUT=480;
    localparam integer TOTAL=80+160/GW, FW=32, PW=67;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0;
    integer cyc=0, sent[0:1][0:3], received[0:1][0:3], mismatch=0;
    wire [3:0] valid[0:1], ready[0:1], last[0:1], mode[0:1], ov[0:1], ol[0:1], oe[0:1], fault[0:1];
    wire [127:0] data[0:1], tag[0:1];
    wire [4*GW*32-1:0] od[0:1];
    wire [3:0] txv[0:1][0:3], rxv[0:1][0:3], rlv[0:1][0:3];
    wire [PW-1:0] txrec[0:1][0:3];
    wire [4*PW-1:0] rxrec[0:1][0:3], rlrec[0:1][0:3];
    wire [7:0] crin[0:1][0:3], crout[0:1][0:3];
    wire [7:0] rank[0:1];
    wire [11:0] code[0:1];
    reg [GW*32+2:0] captured[0:1][0:3][0:MAXOUT-1];
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
        for(genvar dest=0;dest<4;dest=dest+1) begin:g_die
            for(genvar src=0;src<4;src=src+1) begin:g_wire
                assign rxv[b][dest][src]=txv[b][src][dest];
                assign rxrec[b][dest][src*PW+:PW]=txrec[b][src];
                assign crin[b][dest][2*src+:2]=crout[b][src][2*dest+:2];
            end
            if(b==0) begin:g_reference
                ot_w15_rom_oneshot_die_px #(.N(4),.RANK(dest),.LANES(1),.DEPTH(DEPTH),.RELAY(RELAY),.GW(GW),.PAIRWISE(PAIRWISE),.OUT_BP(GW==4)) dut(
                    .clk(clk),.rst_n(rst_n),.in_valid(valid[b][dest]),.in_ready(ready[b][dest]),
                    .in_data(data[b][dest*32+:32]),.in_last(last[b][dest]),.in_mode(mode[b][dest]),.in_tag(tag[b][dest*32+:32]),
                    .tx_valid(txv[b][dest]),.tx_rec(txrec[b][dest]),.tx_ready(4'b1111),.cr_in(crin[b][dest]),
                    .rx_valid(rxv[b][dest]),.rx_rec(rxrec[b][dest]),.cr_out(crout[b][dest]),
                    .rl_tx_valid(rlv[b][dest]),.rl_tx_rec(rlrec[b][dest]),.rl_rx_valid(rlv[b][dest^1]),.rl_rx_rec(rlrec[b][dest^1]),
                    .out_valid(ov[b][dest]),.out_ready((cyc+dest)%7!=0),.out_data(od[b][dest*GW*32+:GW*32]),
                    .out_last(ol[b][dest]),.out_rank(rank[b][dest*2+:2]),.out_err(oe[b][dest]),.fault(fault[b][dest]),.fault_code(code[b][dest*3+:3]));
            end else begin:g_cached
                ot_w15_rom_oneshot_die_px_headreg #(.REGISTER_HEAD(1),.N(4),.RANK(dest),.LANES(1),.DEPTH(DEPTH),.RELAY(RELAY),.GW(GW),.PAIRWISE(PAIRWISE),.OUT_BP(GW==4)) dut(
                    .clk(clk),.rst_n(rst_n),.in_valid(valid[b][dest]),.in_ready(ready[b][dest]),
                    .in_data(data[b][dest*32+:32]),.in_last(last[b][dest]),.in_mode(mode[b][dest]),.in_tag(tag[b][dest*32+:32]),
                    .tx_valid(txv[b][dest]),.tx_rec(txrec[b][dest]),.tx_ready(4'b1111),.cr_in(crin[b][dest]),
                    .rx_valid(rxv[b][dest]),.rx_rec(rxrec[b][dest]),.cr_out(crout[b][dest]),
                    .rl_tx_valid(rlv[b][dest]),.rl_tx_rec(rlrec[b][dest]),.rl_rx_valid(rlv[b][dest^1]),.rl_rx_rec(rlrec[b][dest^1]),
                    .out_valid(ov[b][dest]),.out_ready((cyc+dest)%7!=0),.out_data(od[b][dest*GW*32+:GW*32]),
                    .out_last(ol[b][dest]),.out_rank(rank[b][dest*2+:2]),.out_err(oe[b][dest]),.fault(fault[b][dest]),.fault_code(code[b][dest*3+:3]));
            end
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
    always @(posedge clk) if(rst_n) begin
        for(i=0;i<2;i=i+1) for(j=0;j<4;j=j+1) if(ov[i][j] && (GW!=4 || (cyc+j)%7!=0)) begin
            if(received[i][j]>=MAXOUT || oe[i][j]!=0) $fatal(1,"output/error");
            captured[i][j][received[i][j]]={ol[i][j],rank[i][j*2+:2],od[i][j*GW*32+:GW*32]};
            received[i][j]=received[i][j]+1;
        end
        if(received[0][0]==TOTAL && received[0][1]==TOTAL && received[0][2]==TOTAL && received[0][3]==TOTAL &&
           received[1][0]==TOTAL && received[1][1]==TOTAL && received[1][2]==TOTAL && received[1][3]==TOTAL) begin
            for(j=0;j<4;j=j+1) for(k=0;k<TOTAL;k=k+1) if(captured[0][j][k]!==captured[1][j][k]) mismatch=mismatch+1;
            if(mismatch || code[0]!==code[1] || (BAD_TAG ? fault[1]!=4'b1111 : fault[1]!=0)) $fatal(1,"mismatch=%0d faults=%h/%h",mismatch,code[0],code[1]);
            $display("DS_HEADREG PASS depth=%0d badtag=%0d records=%0d cycles=%0d",DEPTH,BAD_TAG,received[1][0],cyc);
            $finish;
        end
        cyc<=cyc+1;
    end
endmodule
