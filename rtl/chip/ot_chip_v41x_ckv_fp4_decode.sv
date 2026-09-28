`timescale 1ns/1ps
// Exact E2M1 * E4M3FN -> E4M3FN, with RNE and saturation.
// The product is an at-most-eight-bit integer times a power of two, so no
// floating-point multiplier or intermediate rounding is required.
module ot_chip_v41x_ckv_fp4_decode (
    input wire [3:0] code,
    input wire [7:0] scale,
    output reg [7:0] fp8,
    output reg [31:0] fp32,
    output wire poison
);
    assign poison = (scale[6:0] == 7'h7f);
    reg [3:0] m2, sm;
    reg [7:0] prod;
    reg signed [6:0] se, e;
    reg [3:0] hi, shift, quot;
    reg [7:0] rem, half, mask;
    reg [4:0] rounded;
    reg [4:0] be;
    reg sign;
    integer i;
    reg [3:0] e4;
    reg [2:0] mant;
    reg [3:0] sig;
    reg [23:0] sig24;
    reg [23:0] sub;
    integer biased, subshift;
    always @(*) begin
        case (code[2:0])
            3'd0: m2=0; 3'd1: m2=1; 3'd2: m2=2; 3'd3: m2=3;
            3'd4: m2=4; 3'd5: m2=6; 3'd6: m2=8; default: m2=12;
        endcase
        if (scale[6:3] == 0) begin sm={1'b0,scale[2:0]}; se=-7'sd9; end
        else begin sm={1'b1,scale[2:0]}; se=$signed({3'b000,scale[6:3]})-7'sd10; end
        prod=m2*sm;
        hi=0;
        for (i=0;i<8;i=i+1) if (prod[i]) hi=4'(i);
        e=$signed({3'b000,hi})+se-7'sd1;
        sign=code[3]^scale[7];
        shift=0; quot=0; rem=0; half=0; mask=0; rounded=0; be=0;
        fp8=0;
        if (!poison && prod != 0) begin
            if (e >= -7'sd6) begin
                shift=(hi>3) ? (hi-4'd3) : 4'd0;
                if (hi>3) begin
                    quot=4'(prod >> shift);
                    mask=(8'd1<<shift)-8'd1;
                    rem=prod & mask;
                    half=8'd1 << (shift-1'b1);
                    rounded={1'b0,quot}+5'(rem>half || (rem==half && quot[0]));
                end else rounded=5'(prod << (3-hi));
                be=5'(e+7'sd7);
                if (rounded==16) begin rounded=8; be=be+1'b1; end
                if (be>15 || (be==15 && rounded>14)) fp8={sign,7'h7e};
                else fp8={sign,be[3:0],rounded[2:0]};
            end else begin
                if (se+7'sd8 >= 0) rounded=5'(prod << (se+7'sd8));
                else begin
                    shift=4'(-(se+7'sd8));
                    quot=4'(prod >> shift);
                    mask=(8'd1<<shift)-8'd1;
                    rem=prod & mask;
                    half=8'd1 << (shift-1'b1);
                    rounded={1'b0,quot}+5'(rem>half || (rem==half && quot[0]));
                end
                if (rounded>=8) fp8={sign,7'h08};
                else if (rounded!=0) fp8={sign,4'b0000,rounded[2:0]};
            end
        end
        // Exact expansion of the resulting E4M3FN code to binary32.
        e4=fp8[6:3]; mant=fp8[2:0]; sig=0; sig24=0; sub=0;
        biased=0; subshift=0; fp32=0;
        if (fp8[6:0]!=0) begin
            if (e4!=0) begin
                sig={1'b1,mant}; biased=integer'(e4)+120;
            end else begin
                sig={1'b0,mant};
                for (i=0;i<3;i=i+1) if (mant[i]) biased=integer'(i)+118;
                sig=sig << (3-(biased-118));
            end
            sig24={sig,20'b0};
            fp32={fp8[7],8'(biased),sig24[22:0]};
        end
    end
endmodule
