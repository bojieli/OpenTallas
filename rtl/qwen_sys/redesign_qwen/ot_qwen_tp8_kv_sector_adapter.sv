`timescale 1ns/1ps
// Actual native host map reused for SU-originated mutable KV rows. One128B
// row becomes four32B dimension-quarter writes, never four full replicas.
// Backend ACKs must follow actual mapped storage writes; credits are separate.
module ot_qwen_tp8_kv_sector_adapter #(parameter integer MAP_MUT=0)(
    input wire clk,rst_n,
    input wire row_v,output wire row_ready,input wire row_kind,
    input wire [15:0] row_epoch,input wire [5:0] row_layer,input wire [17:0] row_pos,
    input wire [1023:0] row_data,
    output wire [1163:0] commands,
    output wire [15:0] command_epoch,output wire [5:0] command_layer,
    output wire [17:0] command_pos,output wire command_kind,
    input wire [3:0] ack_v,ack_kind,input wire [63:0] ack_epoch,
    input wire [23:0] ack_layer,input wire [71:0] ack_pos,
    output wire fault,output wire [31:0] sectors_issued,sectors_committed
);
    reg active,local_fault;reg [15:0] epoch_q;reg [5:0] layer_q;
    reg [17:0] pos_q;reg kind_q;reg [1023:0] data_q;
    reg [2:0] sent;reg [3:0] issued,acked;reg [3:0] ingress_credits;
    reg [4:0] pending_order_credits;
    wire map_fault,map_ing_credit,map_issue_v;wire [6:0] map_issue_pc;
    wire [3:0] good_ack;reg [127:0] map_out_credit;
    reg [7:0] ack_count;reg bad_ack;reg [3:0] next_issued,next_acked;
    wire tx=active&&sent<4&&ingress_credits!=0&&!fault;
    wire return_order_credit=pending_order_credits!=0;
    wire [5:0] next_order_credits={1'b0,pending_order_credits}+ack_count-6'(return_order_credit);
    wire [31:0] address={8'd0,layer_q,kind_q,1'b0,pos_q[6],pos_q[13:9],pos_q[5:3],pos_q[8:7],sent[1:0],pos_q[2:0]};
    wire [289:0] ingress={data_q[256*sent[1:0]+:256],address,1'b1,tx};
    assign fault=local_fault||map_fault;
    assign row_ready=!active&&!fault&&sectors_issued==sectors_committed;
    assign command_epoch=epoch_q;assign command_layer=layer_q;
    assign command_pos=pos_q;assign command_kind=kind_q;
    for(genvar q=0;q<4;q++)begin:g_identity
        assign good_ack[q]=ack_v[q]&&active&&ack_kind[q]==kind_q&&
                           ack_epoch[16*q+:16]==epoch_q&&ack_layer[6*q+:6]==layer_q&&ack_pos[18*q+:18]==pos_q;
    end
    always @*begin
        next_issued=issued;next_acked=acked;map_out_credit=0;ack_count=0;bad_ack=0;
        if(map_issue_v)begin
            if(!active||map_issue_pc[6:5]!=pos_q[8:7]||map_issue_pc[2:0]!=pos_q[2:0]||issued[map_issue_pc[4:3]])bad_ack=1;
            else next_issued[map_issue_pc[4:3]]=1;
        end
        for(integer q=0;q<4;q++)if(ack_v[q])begin
            if(!good_ack[q]||!next_issued[q]||next_acked[q])bad_ack=1;
            else begin
                next_acked[q]=1;ack_count=ack_count+1'b1;
                map_out_credit[{pos_q[8:7],2'(q),pos_q[2:0]}]=1;
            end
        end
    end
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            active<=0;local_fault<=0;epoch_q<=0;layer_q<=0;pos_q<=0;kind_q<=0;data_q<=0;
            sent<=0;issued<=0;acked<=0;ingress_credits<=8;pending_order_credits<=0;
        end else begin
            if(row_v&&row_ready)begin
                if(row_pos>=8192||row_layer>=36)local_fault<=1;
                else begin
                    active<=1;epoch_q<=row_epoch;layer_q<=row_layer;pos_q<=row_pos;
                    kind_q<=row_kind;data_q<=row_data;sent<=0;issued<=0;acked<=0;
                end
            end else begin
                issued<=next_issued;acked<=next_acked;
                if(active&&(&next_acked))active<=0;
            end
            case({map_ing_credit,tx})
                2'b10:if(ingress_credits==8)local_fault<=1;else ingress_credits<=ingress_credits+1'b1;
                2'b01:ingress_credits<=ingress_credits-1'b1;default:;
            endcase
            if(tx)sent<=sent+1'b1;
            if(bad_ack)local_fault<=1;
            if(next_order_credits>31)local_fault<=1;
            else pending_order_credits<=next_order_credits[4:0];
        end
    end
    qkd_host_ingest_map #(.ORDERED(1),.MUT(MAP_MUT)) actual_map (
        .ck(clk),.rst_n(rst_n),.ing(ingress),.ing_cr(map_ing_credit),
        .out(commands),.out_cr(map_out_credit),.ack_n(ack_count),
        .marker_v(),.marker(),.marker_cr(1'b0),.fault(map_fault),
        .issued(sectors_issued),.landed(sectors_committed),
        .ord_cr(return_order_credit),.issue_v(map_issue_v),.issue_pc(map_issue_pc));
endmodule
