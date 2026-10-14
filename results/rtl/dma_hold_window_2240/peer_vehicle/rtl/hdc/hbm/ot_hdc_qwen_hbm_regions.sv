`timescale 1ns/1ps
// Full-token Qwen O4 HBM-only physical sector map for one TP-2 die.
// Bind once per (user, layer) invocation; all bases stay registered while
// the code/scale/CROM windows and packed-KV page are served. Sector units are
// 32 bytes. The 4 x 22.5 GB HBM3E capacity is 2,812,500,000 sectors.
module ot_hdc_qwen_hbm_regions #(
    parameter integer AW=32,
    parameter integer MAX_USERS=283
) (
    input wire clk, rst_n, bind_region,
    input wire [5:0] layer,
    input wire [8:0] user_id,
    output reg valid, fault,
    output reg [AW-1:0] layer_code_base,
    output reg [AW-1:0] layer_scale_base,
    output reg [AW-1:0] qk_norm_base,
    output reg [AW-1:0] post_tp_base,
    output reg [AW-1:0] packed_kv_base,
    output reg [AW-1:0] head_code_base,
    output reg [AW-1:0] head_scale_base,
    output reg [AW-1:0] head_norm_base,
    output reg [AW-1:0] embed_code_base,
    output reg [AW-1:0] embed_scale_base
);
    localparam [AW-1:0] HEAD_CODE = AW'(109707264);
    localparam [AW-1:0] LAYER_SCALE = AW'(119439360);
    localparam [AW-1:0] HEAD_SCALE = AW'(119494656);
    localparam [AW-1:0] QK_NORM = AW'(119499520);
    localparam [AW-1:0] POST_TP = AW'(119522560);
    localparam [AW-1:0] HEAD_NORM = AW'(119596288);
    localparam [AW-1:0] EMB_CODE = AW'(119597312);
    localparam [AW-1:0] EMB_SCALE = AW'(139045120);
    localparam [AW-1:0] KV = AW'(139054720);
    localparam [AW-1:0] CAPACITY = AW'(2812500000);
    localparam [AW-1:0] USER_KV_SECTORS = AW'(9437184);
    localparam [AW-1:0] LAYER_KV_SECTORS = AW'(262144);
    initial if (AW<32 || MAX_USERS<1 || MAX_USERS>283 ||
                KV+AW'(MAX_USERS)*USER_KV_SECTORS>CAPACITY)
        $fatal(1,"Qwen HBM region map exceeds four-stack capacity");
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid<=0; fault<=0;
            layer_code_base<=0; layer_scale_base<=0; qk_norm_base<=0;
            post_tp_base<=0; packed_kv_base<=0;
            head_code_base<=0; head_scale_base<=0; head_norm_base<=0;
            embed_code_base<=0; embed_scale_base<=0;
        end else if (bind_region) begin
            valid<=0;
            if (layer>=36 || user_id>=MAX_USERS) fault<=1;
            else begin
                valid<=1;
                layer_code_base<=AW'(layer)*AW'(3047424);
                layer_scale_base<=LAYER_SCALE+AW'(layer)*AW'(1536);
                qk_norm_base<=QK_NORM+AW'(layer)*AW'(640);
                post_tp_base<=POST_TP+AW'(layer)*AW'(2048);
                packed_kv_base<=KV+AW'(user_id)*USER_KV_SECTORS+
                                 AW'(layer)*LAYER_KV_SECTORS;
                head_code_base<=HEAD_CODE;
                head_scale_base<=HEAD_SCALE;
                head_norm_base<=HEAD_NORM;
                embed_code_base<=EMB_CODE;
                embed_scale_base<=EMB_SCALE;
            end
        end
    end
endmodule
