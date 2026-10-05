`timescale 1ns/1ps
// One synchronous K-tail read per vector matrix group. The Qwen split
// schedule assigns adjacent head-dimension chunks to distinct SW banks.
module ot_hdc_qwen_kv_tail_group_port #(
    parameter integer G=4, SW=16, AW=24, W=16, LOG_HD=7, LOG_TW=2
) (
    input wire clk,rst_n,
    input wire [G-1:0] rd_v,
    input wire [G*AW-1:0] rd_word,
    output reg [2*SW-1:0] bank_re,
    output reg [2*SW*AW-1:0] bank_row,
    input wire [2*SW*128-1:0] bank_q,
    output wire [G*W*16-1:0] rd_data,
    output reg addr_error
);
    localparam integer LSW=$clog2(SW), LB=$clog2(2*SW);
    reg [G-1:0] valid_q;
    reg [G*LB-1:0] bank_sel_q;
    reg collision;
    reg [AW-1:0] row_seen [0:2*SW-1];
    integer g,b;
    reg [AW-1:0] word,row;
    always @(*) begin
        bank_re=0; bank_row=0; collision=0;
        for (b=0;b<2*SW;b=b+1) row_seen[b]=0;
        for (g=0;g<G;g=g+1) begin
            word=rd_word[g*AW +: AW];
            row=((word >> (LOG_HD+LOG_TW)) << (LOG_HD-LSW)) |
                ((word & ((1<<LOG_HD)-1)) >> LSW);
            b=(word[LOG_HD] ? SW : 0) + word[LSW-1:0];
            if (rd_v[g]) begin
                if (bank_re[b] && row_seen[b] != row) collision=1;
                bank_re[b]=1;
                bank_row[b*AW +: AW]=row;
                row_seen[b]=row;
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin valid_q<=0; bank_sel_q<=0; addr_error<=0; end
        else begin
            valid_q<=rd_v;
            if (collision) addr_error<=1;
            for (integer p=0;p<G;p=p+1)
                bank_sel_q[p*LB +: LB] <=
                    (rd_word[p*AW+LOG_HD] ? SW : 0) + rd_word[p*AW +: LSW];
        end
    end
    function automatic [15:0] fp8_to_bf16(input [7:0] c);
        reg [3:0] e; reg [2:0] m;
        begin
            e=c[6:3]; m=c[2:0];
            if (e!=0) fp8_to_bf16={c[7],(8'(e)+8'd120),m,4'b0};
            else if (m==0) fp8_to_bf16={c[7],15'b0};
            else if (m==1) fp8_to_bf16={c[7],8'd118,7'b0};
            else if (m<4) fp8_to_bf16={c[7],8'd119,m[0],6'b0};
            else fp8_to_bf16={c[7],8'd120,m[1:0],5'b0};
        end
    endfunction
    genvar p,lane;
    generate for (p=0;p<G;p=p+1) begin : g_port
        wire [127:0] word_q=bank_q[bank_sel_q[p*LB +: LB]*128 +: 128];
        for (lane=0;lane<W;lane=lane+1) begin : g_lane
            assign rd_data[(p*W+lane)*16 +: 16]=valid_q[p] ?
                fp8_to_bf16(word_q[lane*8 +: 8]) : 16'b0;
        end
    end endgenerate
endmodule
