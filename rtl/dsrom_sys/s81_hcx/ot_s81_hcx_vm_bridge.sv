`timescale 1ns/1ps
`default_nettype none
// Real HC packet-to-S81 row transport. Packet ingress is the existing exact
// HC engine's four-outstanding sector interface; the native VM is finite.
// Writes retire at bank COMMIT, never at queue acceptance. One native operation
// is outstanding, preserving HC's sector response order under arbitrary stalls.
// All queue, pin, cursor and packet state belongs to the HCX transport leaf.
// HC residual rows contain 32 BF16 values; coefficients contain 16 FP32 values.
// The exact HC engine sees a canonical FP32 view, with BF16 expanded by appending
// zero low bits. Input packet word-base is 32*native_row; output word-base is
// 16*native_row. No floating-point conversion or rounding occurs in transport.
module ot_s81_hcx_vm_bridge #(parameter integer QD=8, MUT_EARLY_COMMIT=0) (
    input wire clk, rst_n,
    input wire job_start, // invalidates immutable-within-job operand row cache
    input wire [337:0] vmq,
    output reg [273:0] vmr,
    output wire rq_v,
    input wire rq_rdy,
    output wire [13:0] rq_row,
    input wire rs_v,
    input wire [511:0] rs_d,
    output wire wq_v,
    input wire wq_rdy,
    input wire wq_commit,
    output wire [13:0] wq_row,
    output wire [15:0] wq_mask,
    output wire [511:0] wq_d,
    output reg fault
);
    localparam integer AW=$clog2(QD);
    reg [337:0] q[0:QD-1];
    reg [AW-1:0] wp,rp;
    reg [AW:0] n;
    reg waiting;
    reg cache_valid;
    reg [13:0] cache_row;
    reg [511:0] cache_data;
    wire [337:0] h=q[rp];
    wire half=h[309];
    wire we=h[336];
    wire present=(n!=0) && !fault;
    wire cache_hit=cache_valid && !job_start && cache_row==rq_row;
    assign rq_v=present && !waiting && !we && !cache_hit;
    assign wq_v=present && !waiting && we;
    assign rq_row=h[324:311];
    assign wq_row=h[323:310];
    wire [7:0] sm={h[44],h[40],h[36],h[32],h[28],h[24],h[20],h[16]};
    assign wq_mask=half ? {sm,8'd0} : {8'd0,sm};
    assign wq_d=half ? {h[303:48],256'd0} : {256'd0,h[303:48]};
    wire read_take=rq_v && rq_rdy;
    wire write_take=wq_v && wq_rdy;
    wire pop=present && ((!we && ((waiting && rs_v) || (!waiting && cache_hit))) || ((waiting || write_take) && we && (wq_commit || (MUT_EARLY_COMMIT && write_take))));
    wire push=vmq[337] && !fault;
    wire [1:0] quarter=h[310:309];
    wire [511:0] read_data=waiting ? rs_d : cache_data;
    wire [255:0] expanded;
    generate for(genvar lane=0;lane<8;lane=lane+1) begin:g_expand
        assign expanded[lane*32 +:32]={read_data[quarter*128+lane*16 +:16],16'd0};
    end endgenerate
    reg bad_mask;
    always @* begin
        bad_mask=1'b0;
        for (integer k=0;k<8;k=k+1)
            if (vmq[16+4*k +: 4]!=4'd0 && vmq[16+4*k +: 4]!=4'hf) bad_mask=1'b1;
    end
    initial begin
        if (QD<4 || (QD & (QD-1))!=0) $error("HCX VM queue must be power-of-two and cover four HC requests");
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin wp<=0;rp<=0;n<=0;waiting<=0;fault<=0;vmr<=0;cache_valid<=0;end
        else begin
            vmr[273]<=1'b0;
            if(job_start) begin cache_valid<=1'b0;if(n!=0 || waiting) fault<=1'b1;end
            if (push) begin
                if ((n==QD && !pop) || (vmq[336] ? |vmq[335:324] : |vmq[335:325]) || |vmq[308:304] || (vmq[336] && bad_mask)) fault<=1'b1;
                else begin q[wp]<=vmq;wp<=wp+1'b1;end
            end
            if (read_take || write_take) waiting<=1'b1;
            if (write_take) cache_valid<=1'b0;
            if (waiting && !we && rs_v) begin cache_valid<=1'b1;cache_row<=rq_row;cache_data<=rs_d;end
            if (pop) begin
                vmr<={1'b1,h[15:0],we,we ? 256'd0 : expanded};
                waiting<=1'b0;rp<=rp+1'b1;
            end
            case ({push,pop})
                2'b10: if (n<QD) n<=n+1'b1;
                2'b01: n<=n-1'b1;
                default: n<=n;
            endcase
            if (rs_v && !(present && !we && waiting)) fault<=1'b1;
            if (wq_commit && !(present && we && (waiting || write_take))) fault<=1'b1;
        end
    end
endmodule
`default_nettype wire
