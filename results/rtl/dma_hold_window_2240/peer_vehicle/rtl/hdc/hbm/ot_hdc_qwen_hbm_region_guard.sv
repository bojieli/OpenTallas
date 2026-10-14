`timescale 1ns/1ps
// Bound every Qwen HBM owner to its current stage's physical sector pages.
// Insert between source-lane PC mapping and the shared four-stack service.
// Invalid requests are not forwarded or acknowledged; fault is sticky.
module ot_hdc_qwen_hbm_region_guard #(
    parameter integer NPC=128, NC=6, AW=32
) (
    input wire clk, rst_n,
    input wire region_valid, head_mode,
    input wire [AW-1:0] layer_code_base,layer_scale_base,
    input wire [AW-1:0] qk_norm_base,post_tp_base,packed_kv_base,
    input wire [AW-1:0] head_code_base,head_scale_base,head_norm_base,
    input wire [AW-1:0] embed_code_base,embed_scale_base,
    input wire [NPC*NC-1:0] in_req_v,in_req_we,
    input wire [NPC*NC*AW-1:0] in_req_addr,
    output wire [NPC*NC-1:0] out_req_v,
    input wire [NPC*NC-1:0] out_req_rdy,
    output wire [NPC*NC-1:0] in_req_rdy,
    output reg fault
);
    initial if (NPC!=128 || NC!=6 || AW!=32)
        $fatal(1,"Qwen O4 region guard requires 128 PCs and six owners");
    function automatic in_range(input [AW-1:0] addr,base,input [AW:0] length);
        in_range=addr>=base && {1'b0,addr}<({1'b0,base}+length);
    endfunction
    wire [NPC*NC-1:0] bad;
    for (genvar p=0;p<NPC;p=p+1) begin : g_pc
        for (genvar c=0;c<NC;c=c+1) begin : g_owner
            localparam integer I=p*NC+c;
            wire [AW-1:0] addr=in_req_addr[I*AW +: AW];
            wire allowed;
            if (c==0) begin : g_matrix
                assign allowed=(head_mode ?
                    (in_range(addr,head_code_base,33'd9732096) ||
                     in_range(addr,head_scale_base,33'd4752)) :
                    (in_range(addr,layer_code_base,33'd3047424) ||
                     in_range(addr,layer_scale_base,33'd1536)));
            end else if (c==1) begin : g_qk
                assign allowed=in_range(addr,qk_norm_base,33'd640);
            end else if (c==2) begin : g_post
                assign allowed=in_range(addr,post_tp_base,33'd2048);
            end else if (c==3) begin : g_embed
                assign allowed=in_range(addr,embed_code_base,33'd19447808) ||
                               in_range(addr,embed_scale_base,33'd9600);
            end else if (c==4) begin : g_head_norm
                assign allowed=in_range(addr,head_norm_base,33'd1024);
            end else begin : g_kv
                assign allowed=in_range(addr,packed_kv_base,33'd262144);
            end
            // Only the packed-KV owner may issue writes.
            assign bad[I]=in_req_v[I] &&
                (!region_valid || !allowed || (in_req_we[I] && c!=5));
            assign out_req_v[I]=in_req_v[I] && !bad[I];
            assign in_req_rdy[I]=!bad[I] && out_req_rdy[I];
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault<=0;
        else if (|bad) fault<=1;
    end
endmodule
