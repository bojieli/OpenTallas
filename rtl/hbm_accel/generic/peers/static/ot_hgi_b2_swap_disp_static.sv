`timescale 1ns/1ps
`default_nettype none
// Compiler calendar command producer for the actual own-stack STORE engines.
// Same real move227 records from ot_hgi_b2_swap_rec / mtp_swap.py lowering.
// One fixed hold register per quadrant, released together by explicit GLAST.
// No input FIFO, credits, ready, endpoint admission or completion-driven issue.
module ot_hgi_b2_swap_disp_static(
    input wire clk,rst_n,
    input wire g_v,g_last,
    input wire [1:0] g_q,
    input wire [226:0] g_mv,
    input wire [31:0] g_issue_at,g_drain_at,
    input wire g_wb_bank,
    input wire [15:0] g_wb_epoch,
    output reg [31:0] cycle,
    output wire [4*309-1:0] dn,
    input wire [11:0] up,
    output reg fence_quiet,done,fault
);
    reg pv,pl;reg [1:0] pq;reg [226:0] pm;reg [31:0] pi,pd;reg pb;reg [15:0] pe;
    reg [3:0] held,launched;reg [307:0] records[0:3],payload[0:3];reg [3:0] dv;
    reg [3:0] src,quiet,bad;reg dirty;
    for(genvar q=0;q<4;q=q+1)begin:DOWN
        assign dn[q*309+:309]={payload[q],dv[q]};
    end
    always @(posedge clk)begin
        pq<=g_q;pl<=g_last;pm<=g_mv;pi<=g_issue_at;pd<=g_drain_at;pb<=g_wb_bank;pe<=g_wb_epoch;
        if(pv&&!pl)records[pq]<={pm,pi,pd,pb,pe};
        if(pv&&pl)for(integer q=0;q<4;q=q+1)
            if(held[q]||2'(q)==pq)payload[q]<=(2'(q)==pq)?{pm,pi,pd,pb,pe}:records[q];
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin cycle<=0;pv<=0;held<=0;launched<=0;dv<=0;src<=0;quiet<=0;bad<=0;dirty<=0;fence_quiet<=0;done<=0;fault<=0;end
        else begin
            cycle<=cycle+1;pv<=g_v;dv<=0;done<=0;
            for(integer q=0;q<4;q=q+1)begin
                src[q]<=up[q*3];quiet[q]<=up[q*3+1];bad[q]<=up[q*3+2];
                if(src[q])launched[q]<=0;
            end
            if(|bad)fault<=1;
            if(pv)begin
                if(held[pq])fault<=1;
                if(pl)begin
                    for(integer q=0;q<4;q=q+1)if(held[q]||2'(q)==pq)begin
                        if(launched[q])fault<=1;
                        dv[q]<=1;launched[q]<=1;
                    end
                    held<=0;dirty<=1;
                end else held[pq]<=1;
            end
            fence_quiet<=(&quiet)&&launched==0&&held==0&&dv==0&&!pv&&!g_v&&!fault&&!(|bad);
            if(dirty&&(&quiet)&&launched==0&&held==0&&dv==0&&!pv&&!g_v&&!fault&&!(|bad))begin done<=1;dirty<=0;end
        end
endmodule

`default_nettype wire
