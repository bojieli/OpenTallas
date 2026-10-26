`timescale 1ns/1ps
module tb_hbm_qdq_bf16;
    parameter integer MUT=0;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0;
    reg [33:0] rq;
    reg [513:0] rr;
    reg [305:0] compact;
    reg [561:0] original;
    wire [33:0] g_rq,d_rq;
    wire [513:0] g_rr,d_rr;
    wire [561:0] g_wq,d_wq;
    integer seed=32'h65f3a, checks=0;
    reg [15:0] words[0:15];
    reg [7:0] mask[0:1];
    reg [15:0] addr[0:1];
    reg valid[0:1];
    ot_hgi_qdq_lg_port_group_r2 #(.BANKS(2)) golden(
        .clk(clk),.rst_n(rst_n),.rq_i(rq),.rq_o(g_rq),
        .rr_i(rr),.rr_o(g_rr),.wq_i(original),.wq_o(g_wq));
    ot_hgi_qdq_lg_bf16_r2 #(.BANKS(2),.MUT(MUT)) dut(
        .clk(clk),.rst_n(rst_n),.rq_i(rq),.rq_o(d_rq),
        .rr_i(rr),.rr_o(d_rr),.wq_i(compact),.wq_o(d_wq));
    initial begin
        rq=0;rr=0;compact=0;original=0;
        for(integer cycle=0;cycle<1000;cycle=cycle+1) begin
            @(negedge clk);
            rst_n=cycle>=3 && cycle%83!=0;
            rq={$random(seed),$random(seed)};
            for(integer j=0;j<17;j=j+1)rr[j*30+:30]=$random(seed);
            for(integer b=0;b<2;b=b+1)begin
                mask[b]=$random(seed);addr[b]=$random(seed);valid[b]=$random(seed);
                for(integer k=0;k<8;k=k+1)words[8*b+k]=$random(seed);
                compact[b*153+:153]={valid[b],addr[b],words[8*b+7],words[8*b+6],
                    words[8*b+5],words[8*b+4],words[8*b+3],words[8*b+2],words[8*b+1],words[8*b],mask[b]};
                original[b*281+:281]={valid[b],addr[b],
                    words[8*b+7],16'd0,words[8*b+6],16'd0,words[8*b+5],16'd0,words[8*b+4],16'd0,
                    words[8*b+3],16'd0,words[8*b+2],16'd0,words[8*b+1],16'd0,words[8*b],16'd0,mask[b]};
            end
            @(posedge clk);#1;
            if(cycle>3)begin
                if({g_rq,g_rr,g_wq}!=={d_rq,d_rr,d_wq})$fatal(1,"QDQ_BF16 mismatch cycle%0d MUT%0d",cycle,MUT);
                checks=checks+1;
            end
        end
        $display("QDQ_BF16 PASS checks%0d MUT%0d added_cycles0",checks,MUT);$finish;
    end
endmodule
