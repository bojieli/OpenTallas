`timescale 1ns/1ps
// Fetch the token's INT8 embedding row and BF16 row scale as 32-byte HBM
// sectors before the package starts its core. Core reads then have the same
// one-cycle latency as the embedding ROM. The HBM controller and its arbitration
// with matrix weights/KV are external to this bounded row source.
module ot_hdc_qwen_embed_row_hbm #(
    parameter integer AW = 24,
    parameter integer TW = 16,
    parameter integer HAW = 28,
    parameter integer PCS = 2,
    parameter integer ROW_WORDS = 2, // 64 signed codes per 512-bit word
    parameter integer TAGW = 8
) (
    input wire clk, rst_n,
    input wire load,
    input wire [TW-1:0] token,
    input wire [HAW-1:0] code_base_sector, scale_base_sector,
    output reg ready, fault,
    input wire code_re,
    input wire [AW-1:0] code_addr,
    output reg [511:0] code_q,
    input wire scale_re,
    input wire [TW-1:0] scale_addr,
    output reg [15:0] scale_q,
    output reg [PCS-1:0] rq_v,
    input wire [PCS-1:0] rq_rdy,
    output reg [PCS*HAW-1:0] rq_addr,
    output reg [PCS*TAGW-1:0] rq_tag,
    input wire [PCS-1:0] rsp_v,
    input wire [PCS*TAGW-1:0] rsp_tag,
    input wire [PCS*256-1:0] rsp_data
);
    localparam integer CODE_SECTORS=ROW_WORDS*2;
    localparam integer SPC=(CODE_SECTORS+PCS-1)/PCS;
    localparam [1:0] IDLE=0, CODE=1, SCALE=2, DONE=3;
    initial if (PCS < 1 || TAGW < $clog2(SPC+1)+1 || ROW_WORDS < 1 || HAW < 28)
        $fatal(1,"unsupported Qwen embedding HBM geometry");
    reg [1:0] state;
    reg [TW-1:0] tok_r;
    reg [255:0] code_bank [0:CODE_SECTORS-1];
    reg [255:0] scale_sector;
    reg [31:0] issued [0:PCS-1], received [0:PCS-1];
    integer p, s, off;
    reg all_done;
    always @(*) begin
        rq_v=0; rq_addr=0; rq_tag=0; all_done=1;
        for (integer q=0;q<PCS;q=q+1) begin
            if (state==CODE) begin
                if (issued[q] < (CODE_SECTORS+PCS-1-q)/PCS) begin
                    rq_v[q]=1;
                    rq_addr[q*HAW +: HAW]=code_base_sector+tok_r*CODE_SECTORS+issued[q]*PCS+q;
                    rq_tag[q*TAGW +: TAGW]=issued[q][TAGW-2:0];
                end
                if (received[q] < (CODE_SECTORS+PCS-1-q)/PCS) all_done=0;
            end else if (state==SCALE && q==0) begin
                if (issued[q]==0) begin
                    rq_v[q]=1;
                    rq_addr[q*HAW +: HAW]=scale_base_sector+(tok_r >> 4);
                    rq_tag[q*TAGW +: TAGW]={1'b1,{(TAGW-1){1'b0}}};
                end
                if (received[q]==0) all_done=0;
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state<=IDLE; tok_r<=0; ready<=0; fault<=0;
            for (p=0;p<PCS;p=p+1) begin issued[p]<=0; received[p]<=0; end
        end else begin
            if (load) begin
                ready<=0;
                if (state==CODE || state==SCALE) fault<=1;
                else begin
                    state<=CODE; tok_r<=token; fault<=0;
                    for (p=0;p<PCS;p=p+1) begin issued[p]<=0; received[p]<=0; end
                end
            end else if (state==CODE || state==SCALE) begin
                for (p=0;p<PCS;p=p+1) begin
                    if (rq_v[p] && rq_rdy[p]) issued[p]<=issued[p]+1;
                    if (rsp_v[p]) begin
                        if ((state==SCALE && p!=0) ||
                            rsp_tag[p*TAGW+TAGW-1] != (state==SCALE) ||
                            rsp_tag[p*TAGW +: TAGW-1] >=
                                ((state==CODE) ? (CODE_SECTORS+PCS-1-p)/PCS : 1)) fault<=1;
                        else begin
                            if (state==CODE)
                                code_bank[rsp_tag[p*TAGW +: TAGW-1]*PCS+p] <= rsp_data[p*256 +: 256];
                            else if (p==0) scale_sector<=rsp_data[p*256 +: 256];
                            received[p]<=received[p]+1;
                        end
                    end
                end
                if (all_done && !fault) begin
                    for (p=0;p<PCS;p=p+1) begin issued[p]<=0; received[p]<=0; end
                    if (state==CODE) state<=SCALE;
                    else begin state<=DONE; ready<=1; end
                end
            end
            // The prior token can leave a trailing synchronous read after
            // package done. While the new row is being prefetched, the core
            // is gated from starting; those old reads have no consumer.
            if (code_re && ready) begin
                if (code_addr < tok_r*ROW_WORDS ||
                    code_addr >= tok_r*ROW_WORDS+ROW_WORDS) fault<=1;
                else begin
                    off=code_addr-tok_r*ROW_WORDS;
                    code_q<={code_bank[off*2+1],code_bank[off*2]};
                end
            end
            if (scale_re && ready) begin
                if (scale_addr!=tok_r) fault<=1;
                else scale_q<=scale_sector[tok_r[3:0]*16 +: 16];
            end
        end
    end
endmodule
