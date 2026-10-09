`timescale 1ns/1ps
// Separately harden the existing input capture state at the leaf's request pins.
// This is not an extra pipeline stage. No input/reset timing exception is used.
module ot_qwen_embedding_ingress_padded #(parameter integer AW=18)(
    input wire clk, rst_n,
    input wire [AW-1:0] address,
    input wire valid, credit,
    (* keep=1, dont_touch=1 *) output reg [AW-1:0] address_q, address_n,
    (* keep=1, dont_touch=1 *) output reg valid_q, valid_n, credit_q, credit_n
);
    // Ten actual fixed cells per pin, sized from each predecessor SS/FF path.
    // Simulation uses their exact Boolean function; timing comes only from P&R.
    wire [AW+2:0] incoming = {rst_n,credit,valid,address};
    (* keep="true" *) wire [AW+2:0] padded;
    for(genvar b=0;b<AW+3;b=b+1) begin:g_pad
        (* keep="true" *) wire [10:0] chain;
        assign chain[0]=incoming[b];
        for(genvar s=0;s<10;s=s+1) begin:g_stage
`ifdef SYNTHESIS
            (* keep=1, dont_touch=1 *) BUFx2_ASAP7_75t_R u_pad(.A(chain[s]),.Y(chain[s+1]));
`else
            assign chain[s+1]=chain[s];
`endif
        end
        assign padded[b]=chain[10];
    end
    wire rst_padded=padded[AW+2];
    (* keep=1, dont_touch=1 *) always @(posedge clk) begin
        address_q<=padded[AW-1:0];address_n<=~padded[AW-1:0];
    end
    (* keep=1, dont_touch=1 *) always @(posedge clk or negedge rst_padded)
        if(!rst_padded) begin valid_q<=0;valid_n<=1;credit_q<=0;credit_n<=1;end
        else begin valid_q<=padded[AW];valid_n<=~padded[AW];credit_q<=padded[AW+1];credit_n<=~padded[AW+1];end
endmodule
