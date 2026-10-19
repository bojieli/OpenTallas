`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hgi_coll_aq_scale13r: the COLL gather master quantiser's scale multiply amax * (1/448 | 1/6) =
// physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv (ot_hbm_xp_aq_mul_pipe13, closed tree13 RTL) with stage 4
// rebalanced (TW7-GQISSUE r4 10-19, SAFE-DESIGN item 4). Same 5 edges, same interface, same result bits.
//
// Why: the r3 gate's deepest reg->reg stage was s3_shift_q -> s4_mant (~630 ps, 17 levels): stage 4 computed, per
// output bit, i + shift (12-b signed add), a range compare and a 48:1 index decode, then the round add on top.
// Change: the alignment decision of both product-top-bit cases is already known at stage 2 (it depends only on the
// exponents), so stage 2 also registers it PRE-DECODED: a one-hot of the shift distance over 23..48 (oh) and the
// sticky thermometer (th[b] = b < shift - 1), and stage 3 registers the one its top bit selects (as it registered the
// encoded shift before). Stage 4 is then one-hot AND-OR alignment + sticky AND-OR + the round increment.
//   shift >= 23 always: normal results shift by msb - 23 (23 | 24); a subnormal result shifts by -(power + 149),
//   and fl = power + msb < -126 gives -(power + 149) > msb - 23. A distance >= 48 (only subnormal) leaves main 0;
//   the round bit exists for 0 < shift <= 48 (oh[25] = 48 -> product[47]); sticky = every bit below shift - 1.
// Data registers carry no reset (validity travels on s*_v / valid_out, as every consumer reads y only when valid;
// fault = valid_out && err): only the 5 valid flops load the reset net.
// Equivalence: the closed tree13 exact bench (tb_aq_tree13 vs ot_hdc_actquant, 1,024 blocks FP8 + FP4 incl. the FP4
// floor subnormal products) on ot_hgi_coll_aq13, and the exhaustive-exponent compare tb_aq_scale13r_eq.sv
// (this module vs ot_hbm_xp_aq_scale13, every a exponent field x random significands, both coefficients).
// ---------------------------------------------------------------------------
module ot_hgi_coll_aq_mul13r (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam [1:0] E_NONE = 2'd0;
    localparam [1:0] E_NONFINITE = 2'd1;
    localparam [1:0] E_OVERFLOW = 2'd2;

    // -- stage 1: decode, normalize subnormals, resolve zero and nonfinite (as the closed pipe) ----------------
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [23:0] a_raw = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_raw = {(b_field != 8'd0), b[22:0]};
    wire        s1_nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire        s1_zero = (a_raw == 24'd0) || (b_raw == 24'd0);
    function automatic [4:0] lead_shift_24;
        input [23:0] value;
        reg [4:0] shift;
        integer bit_index;
        begin
            shift = 5'd23;
            for (bit_index = 0; bit_index <= 23; bit_index = bit_index + 1)
                if (value[bit_index]) shift = 5'd23 - bit_index[4:0];
            lead_shift_24 = shift;
        end
    endfunction
    wire [4:0] a_shift = lead_shift_24(a_raw);
    wire [4:0] b_shift = lead_shift_24(b_raw);
    wire signed [11:0] a_power = (a_field == 8'd0)
        ? (-12'sd149 - {7'd0, a_shift})
        : ($signed({4'd0, a_field}) - 12'sd150);
    wire signed [11:0] b_power = (b_field == 8'd0)
        ? (-12'sd149 - {7'd0, b_shift})
        : ($signed({4'd0, b_field}) - 12'sd150);

    reg        s1_v;
    reg        s1_inv6, s1_byp, s1_sign;
    reg [1:0]  s1_err;
    reg [23:0] s1_a;
    reg signed [11:0] s1_power;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) s1_v <= 1'b0; else s1_v <= valid_in;
    always @(posedge clk) begin
        s1_inv6 <= (b == 32'h3e2aaaab);
        s1_byp <= s1_nonfinite || s1_zero;
        s1_err <= s1_nonfinite ? E_NONFINITE : E_NONE;
        s1_sign <= a[31] ^ b[31];
        s1_a <= a_raw << a_shift;
        s1_power <= a_power + b_power;
    end

    // -- stage 2: three 24x8 partial products; both exponent decisions, PRE-DECODED ------------------------------
    // dec = {sub, floor[11:0], oh[25:0] (shift == 23 + j), th[47:0] (b < shift - 1)}
    function automatic [86:0] decide;
        input signed [11:0] power;
        input [5:0] msb;
        reg signed [11:0] fl, sh;
        reg sub;
        reg [25:0] oh;
        reg [47:0] th;
        integer j;
        begin
            fl = power + $signed({6'd0, msb});
            sub = (fl < -12'sd126);
            sh = sub ? -(power + 12'sd149) : ($signed({6'd0, msb}) - 12'sd23);
            for (j = 0; j < 26; j = j + 1) oh[j] = (sh == 12'sd23 + j);
            for (j = 0; j < 48; j = j + 1) th[j] = ($signed(12'(j)) < sh - 12'sd1);
            decide = {sub, fl, oh, th};
        end
    endfunction

`ifdef OT_GQ_FAN32
    wire[23:0]s1_ac[0:5];
    generate for(genvar g=0;g<6;g=g+1)begin:g_s1_operand_copy
        ot_hgi_coll_scale_data_ff u_ff(.clk(clk),
`ifdef OT_GQ_MUT_SCALE_DATA
            .d((g==0)?((a_raw<<a_shift)^24'd1):(a_raw<<a_shift)),
`else
            .d(a_raw<<a_shift),
`endif
            .q(s1_ac[g]));
    end endgenerate
`else
    wire[23:0]s1_ac[0:5];
    assign s1_ac[0]=s1_a;assign s1_ac[1]=s1_a;assign s1_ac[2]=s1_a;
    assign s1_ac[3]=s1_a;assign s1_ac[4]=s1_a;assign s1_ac[5]=s1_a;
`endif
    reg        s2_v;
    reg        s2_byp, s2_sign;
    reg [1:0]  s2_err;
    reg [31:0] s2_pp0, s2_pp1, s2_pp2;
    reg [86:0] s2_d47, s2_d46;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) s2_v <= 1'b0; else s2_v <= s1_v;
    always @(posedge clk) begin
        s2_byp <= s1_byp; s2_sign <= s1_sign; s2_err <= s1_err;
        s2_pp0 <= s1_inv6 ? ({8'd0,s1_ac[0]}*32'hAB) : ({8'd0,s1_ac[1]}*32'h25);
        s2_pp1 <= s1_inv6 ? ({8'd0,s1_ac[2]}*32'hAA) : ({8'd0,s1_ac[3]}*32'h49);
        s2_pp2 <= s1_inv6 ? ({8'd0,s1_ac[4]}*32'hAA) : ({8'd0,s1_ac[5]}*32'h92);
        s2_d47 <= decide(s1_power, 6'd47);
        s2_d46 <= decide(s1_power, 6'd46);
    end

    // -- stage 3: the product, and the decision its top bit selects (as the closed pipe) -------------------------
    wire [47:0] pa={16'd0,s2_pp0},pb={8'd0,s2_pp1,8'd0},pc={s2_pp2,16'd0};
    wire [47:0] ps=pa^pb^pc,pcarry=((pa&pb)|(pa&pc)|(pb&pc))<<1;
    wire [8:0] byte_sum [0:5];
    wire [5:0] bg,bp;
    wire [6:0] bc;
    wire [47:0] s3_prod;
    assign bc[0]=1'b0;
    for(genvar j=0;j<6;j=j+1)begin:product_byte
        assign byte_sum[j]={1'b0,ps[j*8+:8]}+{1'b0,pcarry[j*8+:8]};
        assign bg[j]=byte_sum[j][8];
        assign bp[j]=&byte_sum[j][7:0];
        assign s3_prod[j*8+:8]=byte_sum[j][7:0]+bc[j];
    end
    assign bc[1]=bg[0];
    assign bc[2]=bg[1]|(bp[1]&bg[0]);
    assign bc[3]=bg[2]|(bp[2]&bg[1])|(&bp[2:1]&bg[0]);
    assign bc[4]=bg[3]|(bp[3]&bg[2])|(&bp[3:2]&bg[1])|(&bp[3:1]&bg[0]);
    assign bc[5]=bg[4]|(bp[4]&bg[3])|(&bp[4:3]&bg[2])|(&bp[4:2]&bg[1])|(&bp[4:1]&bg[0]);
    assign bc[6]=bg[5]|(bp[5]&bc[5]);
    wire s3_top=byte_sum[5][7]^(bc[5]&(&byte_sum[5][6:0]));
`ifdef OT_GQ_FAN32
    // Native combinational chunks own their top-bit decision. Same stage/edges;
    // one protected scalar controls at most eight decision bits (16 mux legs).
    wire[86:0]s3_dec;
    generate for(genvar g=0;g<11;g=g+1)begin:g_dec_control
        localparam integer W=(g==10)?7:8;
        (* keep="true" *)ot_hgi_coll_aq_dec_chunk #(.W(W),.G(g)) u_dec(.hi(byte_sum[5][7:0]),.carry(bc[5]),
            .d47(s2_d47[8*g+:W]),.d46(s2_d46[8*g+:W]),.q(s3_dec[8*g+:W]));
    end endgenerate
`else
    wire [86:0] s3_dec = s3_top ? s2_d47 : s2_d46;
`endif

    reg        s3_v;
    reg        s3_byp, s3_sign, s3_is_sub_q;
    reg [1:0]  s3_err;
    reg [47:0] s3_product;
    reg signed [11:0] s3_floor_q;
    reg [25:0] s3_oh;
    reg [47:0] s3_th;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) s3_v <= 1'b0; else s3_v <= s2_v;
    always @(posedge clk) begin
        s3_byp <= s2_byp; s3_sign <= s2_sign; s3_err <= s2_err; s3_product <= s3_prod;
        {s3_is_sub_q, s3_floor_q, s3_oh, s3_th} <= s3_dec;
    end

    // -- stage 4: one-hot align, round bit, sticky, round to nearest even -----------------------------------------
    reg [23:0] s4_main;
    reg        s4_round_bit;
    always @(*) begin
        s4_main = 24'd0;
        s4_round_bit = 1'b0;
        for (integer j = 0; j < 26; j = j + 1) begin
            for (integer i = 0; i < 24; i = i + 1)
                if (i + 23 + j < 48) s4_main[i] = s4_main[i] | (s3_oh[j] & s3_product[i + 23 + j]);
            s4_round_bit = s4_round_bit | (s3_oh[j] & s3_product[22 + j]);
        end
    end
    wire s4_sticky = |(s3_product & s3_th);
    wire [24:0] s4_rounded = {1'b0, s4_main} + {24'd0, (s4_round_bit && (s4_sticky || s4_main[0]))};

    reg        s4_v;
    reg        s4_byp, s4_sign, s4_is_sub;
    reg [1:0]  s4_err;
    reg [24:0] s4_mant;
    reg signed [11:0] s4_floor;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) s4_v <= 1'b0; else s4_v <= s3_v;
    always @(posedge clk) begin
        s4_byp <= s3_byp; s4_sign <= s3_sign; s4_err <= s3_err; s4_is_sub <= s3_is_sub_q;
        s4_mant <= s4_rounded; s4_floor <= s3_floor_q;
    end

    // -- stage 5: the post-round carry, the encoding, and the refusals (as the closed pipe) -----------------------
    wire        s5_carry = !s4_is_sub && s4_mant[24];
    wire [23:0] s5_man = s5_carry ? s4_mant[24:1] : s4_mant[23:0];
    wire signed [11:0] s5_floor = s4_floor + $signed({11'd0, s5_carry});
    wire        s5_over = !s4_is_sub && (s5_floor > 12'sd127);
    wire [7:0]  s5_field = s5_floor[7:0] + 8'd127;
    wire        s5_sub_carry = s4_is_sub && (s4_mant >= 25'h080_0000);
    wire [31:0] s5_code =
        s4_is_sub ? (s5_sub_carry ? {s4_sign, 8'h01, 23'd0}
                                  : {s4_sign, 8'h00, s4_mant[22:0]})
                  : {s4_sign, s5_field, s5_man[22:0]};
    always @(posedge clk or negedge rst_n)
        if (!rst_n) valid_out <= 1'b0; else valid_out <= s4_v;
    always @(posedge clk) begin
        if (s4_byp) begin
            y <= 32'd0;
            err <= s4_err;
        end else if (s5_over) begin
            y <= 32'd0;
            err <= E_OVERFLOW;
        end else begin
            y <= (s5_code[30:0] == 31'd0) ? 32'd0 : s5_code;
            err <= E_NONE;
        end
    end
endmodule

// Only the two actual AQ coefficient operands are legal in this distinct pipe.
module ot_hgi_coll_aq_scale13r(input wire clk,rst_n,v,input wire [31:0] a,b,output wire [31:0] y,output wire fault);
 wire [1:0] err;wire vo;
 ot_hgi_coll_aq_mul13r u(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(y),.err(err),.valid_out(vo));
 assign fault=vo&&(err!=0);
`ifndef SYNTHESIS
 always @(posedge clk)if(rst_n&&v&&b!=32'h3b124925&&b!=32'h3e2aaaab)$fatal(1,"AQ_SCALE_COEFFICIENT_UNSUPPORTED");
`endif
endmodule

(* keep_hierarchy="yes" *)
module ot_hgi_coll_aq_dec_chunk #(parameter integer W=8,G=0)(input wire[7:0]hi,input wire carry,input wire[W-1:0]d47,d46,output wire[W-1:0]q);
    wire top;
    (* keep="true" *)ot_hgi_coll_aq_top_dec u_top(.hi(hi),.carry(carry),.q(top));
`ifdef OT_GQ_MUT_SCALE_CTL
    wire select_top=(G==6)?!top:top;
`else
    wire select_top=top;
`endif
    assign q=select_top?d47:d46;
endmodule

(* keep_hierarchy="yes" *)
module ot_hgi_coll_aq_top_dec(input wire[7:0]hi,input wire carry,output wire q);
    assign q=hi[7]^(carry&&(&hi[6:0]));
endmodule

(* keep_hierarchy="yes" *)
module ot_hgi_coll_scale_data_ff(input wire clk,input wire[23:0]d,output wire[23:0]q);
    (* keep="true",dont_touch="true" *)reg[23:0]r;
    always @(posedge clk)r<=d;
    assign q=r;
endmodule
