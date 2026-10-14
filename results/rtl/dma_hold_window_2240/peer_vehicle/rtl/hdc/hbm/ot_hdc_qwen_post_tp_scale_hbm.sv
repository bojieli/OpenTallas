`timescale 1ns/1ps
// Qwen TP-2 o/down true-row scales, materialized as 64-bit CROM words.
// The two 4096-word ranges are contiguous in the emitted layer image. This
// source fetches their 2048 32-byte sectors through PC-local request banks,
// then preserves the core's one-cycle synchronous CROM read contract. Other
// CROM constants are deliberately outside this module's ownership.
module ot_hdc_qwen_post_tp_scale_hbm #(
    parameter integer AW=24,
    parameter integer HAW=28,
    parameter integer PCS=32,
    parameter integer TAGW=8,
    parameter integer ROWS_PER_SCALE=4096,
    parameter integer CROM_BASE=535041
) (
    input wire clk, rst_n, load,
    input wire [HAW-1:0] hbm_base_sector,
    output reg ready, fault,
    input wire crom_re,
    input wire [AW-1:0] crom_addr,
    output reg [63:0] crom_q,
    output reg [PCS-1:0] rq_v,
    input wire [PCS-1:0] rq_rdy,
    output reg [PCS*HAW-1:0] rq_addr,
    output reg [PCS*TAGW-1:0] rq_tag,
    input wire [PCS-1:0] rsp_v,
    input wire [PCS*TAGW-1:0] rsp_tag,
    input wire [PCS*256-1:0] rsp_data
);
    localparam integer WORDS=2*ROWS_PER_SCALE;
    localparam integer SECTORS=WORDS/4;
    localparam integer SPC=SECTORS/PCS;
    initial if (HAW<28 || PCS<1 || (PCS&(PCS-1))!=0 ||
                WORDS%4!=0 || SECTORS%PCS!=0 || TAGW<$clog2(SPC+1))
        $fatal(1,"unsupported Qwen post-TP scale HBM geometry");

    reg [255:0] sector_bank [0:PCS-1][0:SPC-1];
    reg [15:0] issued [0:PCS-1], received [0:PCS-1];
    reg prefetch;
    reg all_done;
    integer p, off, sec;
    always @(*) begin
        rq_v=0; rq_addr=0; rq_tag=0; all_done=1;
        for (integer q=0;q<PCS;q=q+1) begin
            if (prefetch && issued[q]<SPC) begin
                rq_v[q]=1;
                rq_addr[q*HAW +: HAW]=hbm_base_sector+issued[q]*PCS+q;
                rq_tag[q*TAGW +: TAGW]=issued[q][TAGW-1:0];
            end
            if (received[q]<SPC) all_done=0;
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            prefetch<=0; ready<=0; fault<=0; crom_q<=0;
            for (p=0;p<PCS;p=p+1) begin issued[p]<=0; received[p]<=0; end
        end else begin
            if (load) begin
                if (prefetch) fault<=1;
                else begin
                    prefetch<=1; ready<=0;
                    for (p=0;p<PCS;p=p+1) begin issued[p]<=0; received[p]<=0; end
                end
            end else if (prefetch) begin
                for (p=0;p<PCS;p=p+1) begin
                    if (rq_v[p] && rq_rdy[p]) issued[p]<=issued[p]+1;
                    if (rsp_v[p]) begin
                        if (rsp_tag[p*TAGW +: TAGW]>=SPC ||
                            rsp_tag[p*TAGW +: TAGW]>=issued[p]) fault<=1;
                        else begin
                            sector_bank[p][rsp_tag[p*TAGW +: TAGW]] <=
                                rsp_data[p*256 +: 256];
                            received[p]<=received[p]+1;
                        end
                    end
                end
                if (all_done && !fault) begin prefetch<=0; ready<=1; end
            end
            if (crom_re) begin
                if (!ready || crom_addr<CROM_BASE ||
                    crom_addr>=CROM_BASE+WORDS) begin
                    crom_q<=0; fault<=1;
                end else begin
                    off=crom_addr-CROM_BASE;
                    sec=off>>2;
                    crom_q<=sector_bank[sec%PCS][sec/PCS][(off&3)*64 +: 64];
                end
            end
        end
    end
endmodule
