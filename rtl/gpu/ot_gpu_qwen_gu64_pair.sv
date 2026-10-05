`timescale 1ns/1ps
// Model: qwen_hbm_connected_20261001. Two independent rows per 128B line.
// No 128-leaf combine, padding, K rechunking, or cross-row arithmetic.
// Caller supplies the real global row and circulating slot for each row.
// Results require the modeled addressed FIFO/row-scale path downstream.
module ot_gpu_qwen_gu64_pair #(
    parameter integer ENABLE_GU64 = 0,
    parameter integer ROWW = 18,
    parameter integer ALAT = 7
) (
    input wire clk, rst_n, v, first, last,
    input wire [1023:0] weights_i8,
    input wire [1023:0] x_bf16,
    input wire [2*ROWW-1:0] global_rows,
    input wire [5:0] slots,
    output wire [1:0] ov,
    output wire [63:0] sums,
    output wire [2*ROWW-1:0] result_rows,
    output wire [5:0] result_slots,
    output wire fault
);
    localparam integer TW = ROWW+3;
    function automatic [15:0] i8_bf16(input [7:0] code);
        reg s; reg [7:0] m,n; reg [2:0] msb; integer b;
        begin
            s=code[7]; m=s ? (~code+8'd1) : code; msb=0;
            for(b=0;b<8;b=b+1) if(m[b]) msb=b;
            n=m << (7-msb);
            i8_bf16=(m==0) ? 16'd0 : {s,8'd127+{5'd0,msb},n[6:0]};
        end
    endfunction
    generate if (ENABLE_GU64) begin : g_enabled
        wire [3:0] cv,cf;
        wire [127:0] cy;
        wire [4*TW-1:0] ct;
        genvar r,s,l;
        for(r=0;r<2;r=r+1) begin : g_row
            for(s=0;s<2;s=s+1) begin : g_sub
                wire [511:0] w,x;
                for(l=0;l<32;l=l+1) begin : g_lane
                    assign w[16*l+:16]=i8_bf16(weights_i8[8*(r*64+s*32+l)+:8]);
                    assign x[16*l+:16]=x_bf16[16*(s*32+l)+:16];
                end
                ot_gpu_tc_col #(.L(32),.IL(8),.TAGW(TW),.ALAT(ALAT)) u_col(
                    .clk(clk),.rst_n(rst_n),.v(v),.first(first),.last(last),
                    .tag({global_rows[ROWW*r+:ROWW],slots[3*r+:3]}),.w(w),.x(x),
                    .ov(cv[r*2+s]),.y(cy[32*(r*2+s)+:32]),
                    .otag(ct[TW*(r*2+s)+:TW]),.fault(cf[r*2+s]));
            end
            wire tf;
            wire [TW-1:0] tag_out;
            ot_gpu_tree #(.N(2),.TAGW(TW),.ALAT(ALAT)) u_combine64(
                .clk(clk),.rst_n(rst_n),.v(cv[2*r]),.d(cy[64*r+:64]),
                .tag(ct[TW*2*r+:TW]),.ov(ov[r]),.y(sums[32*r+:32]),
                .otag(tag_out),.fault(tf));
            assign result_rows[ROWW*r+:ROWW]=tag_out[TW-1:3];
            assign result_slots[3*r+:3]=tag_out[2:0];
            wire mismatch=(cv[2*r]!=cv[2*r+1]) ||
                (cv[2*r] && ct[TW*2*r+:TW]!=ct[TW*(2*r+1)+:TW]);
            wire row_fault=tf | mismatch;
        end
        assign fault=(|cf) | g_row[0].row_fault | g_row[1].row_fault;
    end else begin : g_disabled
        assign ov=0; assign sums=0; assign result_rows=0;
        assign result_slots=0; assign fault=v;
    end endgenerate
endmodule
