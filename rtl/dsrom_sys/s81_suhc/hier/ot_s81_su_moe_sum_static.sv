`timescale 1ns/1ps
// Actual source MOE_SUM: (((((E0+E1)+E2)+E3)+E4)+E5)+E6.
// Each intermediate is binary32 RNE; BF16 rounding occurs only at the LAST leaf.
// The physically reusable leaf has sixteen actual six-stage FP32 adders and a
// registered output boundary. Six leaves avoid one large clock root. Operand
// alignment uses real mapped SRAM delay lines, not wide flop shift registers.
module ot_s81_su_moe_add_leaf #(
    parameter integer LAST=0, EARLY_BF16_MUTANT=0
)(
    input wire clk,rst_n,i_v,
    input wire [511:0] i_acc,i_side,
    output reg o_v,
    output reg [511:0] o_d,
    output reg fault
);
    wire[511:0] y;wire[15:0]v;wire[31:0]err;
    function automatic [31:0] bf16(input [31:0]x);
        reg[32:0]s;
        begin s={1'b0,x}+33'h7fff+{32'd0,x[16]};bf16={s[31:16],16'd0};end
    endfunction
    genvar l;
    generate for(l=0;l<16;l=l+1)begin:g_l
        ot_dsrom_fp32_add_f12_l6 u_add(.clk(clk),.rst_n(rst_n),.valid_in(i_v),
            .a(i_acc[32*l+:32]),.b(i_side[32*l+:32]),.y(y[32*l+:32]),
            .err(err[2*l+:2]),.valid_out(v[l]));
        always@(posedge clk)o_d[32*l+:32]<=(LAST!=0 || EARLY_BF16_MUTANT!=0)?bf16(y[32*l+:32]):y[32*l+:32];
    end endgenerate
    always@(posedge clk or negedge rst_n)begin
        if(!rst_n)begin o_v<=0;fault<=0;end
        else begin
            o_v<=v[0];
            if((|v && !(&v)) || (v[0] && |err))fault<=1;
        end
    end
endmodule

module ot_s81_su_moe_sum_static #(
    parameter integer MUT=0
)(
    input wire [5:0] ck,
    input wire rst_n,i_v,
    input wire [3583:0] i_e,
    input wire [6:0] i_present,
    input wire [13:0] i_row,
    output wire o_v,
    output wire [511:0] o_d,
    output wire [13:0] o_row,
    output wire fault
);
    reg source_fault;
    always@(posedge ck[0] or negedge rst_n)
        if(!rst_n)source_fault<=0;
        else if(i_v && i_present!=7'h7f)source_fault<=1;
    wire[511:0]acc[0:6];wire[6:0]v;wire[5:0]f;
    assign acc[0]=(MUT==1)?i_e[1024+:512]:i_e[0+:512];
    assign v[0]=i_v;
    genvar s;
    generate for(s=0;s<6;s=s+1)begin:g_s
        wire[511:0]side;
        wire[511:0]source_side=(MUT==1 && s==1)?i_e[0+:512]:i_e[512*(s+1)+:512];
        if(s==0)begin:g_first
            assign side=source_side;
        end else begin:g_align
            // SRAM delay is exactly 7*s edges; includes each preceding leaf's
            // actual six-stage adder and registered boundary output.
            ot_sram_dline #(.W(512),.D(7*s)) u_side(.clk(ck[s]),.rst_n(rst_n),.d(source_side),.q(side));
        end
        ot_s81_su_moe_add_leaf #(.LAST(s==5),.EARLY_BF16_MUTANT(MUT==2 && s!=5)) u_leaf(
            .clk(ck[s]),.rst_n(rst_n),.i_v(v[s]),.i_acc(acc[s]),.i_side(side),
            .o_v(v[s+1]),.o_d(acc[s+1]),.fault(f[s]));
    end endgenerate
    ot_hdc_delay #(.W(14),.D(42)) u_row(.clk(ck[5]),.rst_n(rst_n),.d(i_row),.q(o_row));
    assign o_v=v[6];assign o_d=acc[6];assign fault=|f|source_fault;
endmodule
