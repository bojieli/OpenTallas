`timescale 1ns/1ps
// Q4 merge-side finite queue. One reserved row packet produces one merged write.
// The row sender owns DEPTH credits and spends one BEFORE launch. land_v is
// consequently not ready/valid: each asserted arrival must already have a seat.
// A credit is returned only when the merged word leaves this queue.
module ot_qfd_kv_merge_skid #(
    parameter integer DEPTH=8, AW=7, DW=512,
    parameter integer MUT_CREDIT_EARLY=0
)(
    input wire clk, rst_n,
    input wire land_v, input wire [AW-1:0] land_addr,
    input wire [DW-1:0] land_data, land_mask,
    input wire tok_v, input wire [AW-1:0] tok_addr,
    input wire [DW-1:0] tok_data, tok_mask,
    output reg credit_free,
    output reg kvw_ce, output reg [AW-1:0] kvw_addr,
    output reg [DW-1:0] kvw_data, kvw_mask,
    output reg fault,
    output wire drained
);
    localparam integer PW=$clog2(DEPTH), CW=$clog2(DEPTH+1);
    reg [AW+2*DW-1:0] mem [0:DEPTH-1];
    reg [PW-1:0] rp, wp;
    reg [CW-1:0] count;
    reg pv; reg [AW+2*DW-1:0] pd;
    wire pop=(count!=0) && !tok_v && !fault;
    wire push=land_v && !fault && ((count<CW'(DEPTH)) || pop);
    wire overflow=land_v && !fault && (count==CW'(DEPTH)) && !pop;
    assign drained=(count==0) && !pv && !kvw_ce;
    initial begin
        if (DEPTH<2 || (DEPTH & (DEPTH-1))!=0) $fatal(1,"DEPTH must be power-of-two >=2");
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            rp<=0;wp<=0;count<=0;pv<=0;pd<=0;kvw_ce<=0;
            kvw_addr<=0;kvw_data<=0;kvw_mask<=0;credit_free<=0;fault<=0;
        end else begin
            credit_free<=!fault && !overflow && (MUT_CREDIT_EARLY!=0 ? push : pop);
            fault<=fault || overflow;
            if(push) begin mem[wp]<={land_addr,land_data,land_mask};wp<=wp+1'b1;end
            if(pop) rp<=rp+1'b1;
            case({push,pop})
                2'b10:count<=count+1'b1;
                2'b01:count<=count-1'b1;
                default:count<=count;
            endcase
            // Pin output station is two edges from token or queue dequeue.
            pv<=!fault && !overflow && (tok_v || pop);
            if(tok_v) pd<={tok_addr,tok_data,tok_mask};
            else if(pop) pd<=mem[rp];
            kvw_ce<=pv && !fault && !overflow;
            if(pv) {kvw_addr,kvw_data,kvw_mask}<=pd;
        end
    end
endmodule

// Sender lives beside row arbitration, so same-cycle ready stays local.
// Reverse-chain credit arrivals may be arbitrarily delayed. No credit is
// inferred from PHY arrival, elapsed time, or token completion.
module ot_qfd_kv_credit_tx #(parameter integer DEPTH=8)(
    input wire clk,rst_n,request,credit_return,
    output wire grant, output reg fault
);
    localparam integer CW=$clog2(DEPTH+1);
    reg [CW-1:0] credits;
    assign grant=request && (credits!=0) && !fault;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin credits<=CW'(DEPTH);fault<=0;end
        else begin
            if(credit_return && credits==CW'(DEPTH) && !grant) fault<=1;
            case({credit_return,grant})
                2'b10:if(credits<CW'(DEPTH)) credits<=credits+1'b1;
                2'b01:credits<=credits-1'b1;
                default:credits<=credits;
            endcase
        end
    end
endmodule
