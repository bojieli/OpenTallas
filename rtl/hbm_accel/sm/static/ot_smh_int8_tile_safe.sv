`timescale 1ns/1ps
// Bounded opt-in same-age prototype; model results/arch/hbm_int8_safe_source_1019/model.json.
`ifdef OT_INT8_MUT_SIGN          // the parent bench's converter sign mutant (qwen_sm_mv_unit --mut sign) reaches this tile too
`ifndef OT_I8T_MUT_SIGN
`define OT_I8T_MUT_SIGN
`endif
`endif
module ot_smh_int8_tile_safe (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          i_v,          // packet[1098] & command[116] (the parent's mark)
    input  wire [9:0]    i_tag,        // packet[1097:1088]
    input  wire [1023:0] i_codes,      // packet[1023:0]: 128 INT8 codes, low 64 first
    output wire          o_v,
    output wire [9:0]    o_tag,
    output wire [1023:0] o_data,       // 64 BF16 lanes
    output wire [34:0]   o_sel         // kept copies of o_v for the parent's 1099-bit merge select (<= 32 bits each)
);
    localparam integer NG = 128;        // select groups: 4 lanes = 32 code bits each
    localparam integer NSEL = 35;
    // Distinct opt-in physical primitive. Canonical module is unchanged.
    // Exactly two sampled edges, matching the inherited generated wrapper.
    (* keep *) reg reset_first;
    (* keep *) reg [8:0] reset_final;
    always @(posedge clk) begin
        reset_first <= rst_n;
        reset_final <= {9{reset_first}};
    end
    (* keep *) reg [21:0] p_v;
    reg [9:0] p_tag;
    reg [1023:0] p_codes;
    always @(posedge clk) begin
        p_tag <= i_tag;
        p_codes <= i_codes;
    end
    reg [511:0] hi_codes;
    (* keep *) reg [127:0] pend;
    (* keep *) reg [1:0] pend_s;
    (* keep *) reg pend_c;
    always @(posedge clk) hi_codes <= p_codes[1023:512];
    genvar q;
    generate for (q=0; q<22; q=q+1) begin : g_pv
        always @(posedge clk or negedge reset_final[q/24])
            if (!reset_final[q/24]) p_v[q] <= 1'b0;
            else p_v[q] <= i_v;
    end
    for (q=0; q<128; q=q+1) begin : g_pend
        always @(posedge clk or negedge reset_final[(22+q)/24])
            if (!reset_final[(22+q)/24]) pend[q] <= 1'b0;
`ifdef OT_I8T_MUT_PEND
            else pend[q] <= 1'b0;
`else
            else pend[q] <= p_v[q/8];
`endif
    end
    for (q=0; q<2; q=q+1) begin : g_pends
        always @(posedge clk or negedge reset_final[(150+q)/24])
            if (!reset_final[(150+q)/24]) pend_s[q] <= 1'b0;
`ifdef OT_I8T_MUT_PEND
            else pend_s[q] <= 1'b0;
`else
            else pend_s[q] <= p_v[16+q];
`endif
    end endgenerate
    always @(posedge clk or negedge reset_final[152/24])
        if (!reset_final[152/24]) pend_c <= 1'b0;
`ifdef OT_I8T_MUT_PEND
        else pend_c <= 1'b0;
`else
        else pend_c <= p_v[18];
`endif
    // ---- classify + encode (one stage) ----------------------------------------------------------------------------
    function automatic [15:0] to_bf16(input [7:0] code);
        reg [7:0] mag, shifted;
        integer b, top;
        begin
            mag = code[7] ? (~code + 8'd1) : code;
            top = 0;
            for (b = 0; b < 8; b = b + 1) if (mag[b]) top = b;
            shifted = mag << (7 - top);
            to_bf16 = (mag == 8'd0) ? 16'd0 : {code[7], 8'd127 + top[7:0], shifted[6:0]};
        end
    endfunction
    wire [1023:0] widened;
    genvar l;
    generate for (l = 0; l < 64; l = l + 1) begin : g_lane
        wire [7:0] code;
        assign code[3:0] = pend[2*l] ? hi_codes[8*l +: 4] : p_codes[8*l +: 4];
        assign code[7:4] = pend[2*l+1] ? hi_codes[8*l+4 +: 4] : p_codes[8*l+4 +: 4];
`ifdef OT_I8T_MUT_SIGN
        assign widened[16*l +: 16] = to_bf16(code & 8'h7f);  // mutant: sign dropped
`else
        assign widened[16*l +: 16] = to_bf16(code);
`endif
    end endgenerate
    // ---- output registers -------------------------------------------------------------------------------------------
    reg [1023:0] r_data;
    reg          r_v;
    (* keep *) reg [NSEL-1:0] r_sel;
    reg [9:0]    r_tag, held_tag;
    always @(posedge clk) r_data <= widened;
    always @(posedge clk or negedge reset_final[153/24])
        if (!reset_final[153/24]) r_v <= 1'b0;
        else r_v <= p_v[21] | pend_c;
    generate for (q=0; q<NSEL; q=q+1) begin : g_sel
        always @(posedge clk or negedge reset_final[(154+q)/24])
            if (!reset_final[(154+q)/24]) r_sel[q] <= 1'b0;
            else r_sel[q] <= q<18 ? (p_v[19] | pend_s[0]) : (p_v[20] | pend_s[1]);
    end
    for (q=0; q<10; q=q+1) begin : g_tag
        always @(posedge clk or negedge reset_final[(189+q)/24])
            if (!reset_final[(189+q)/24]) r_tag[q]<=1'b0;
`ifdef OT_I8T_MUT_TAG
            else r_tag[q] <= held_tag[q];
`else
            else r_tag[q] <= p_v[21] ? p_tag[q] : held_tag[q];
`endif
        always @(posedge clk or negedge reset_final[(199+q)/24])
            if (!reset_final[(199+q)/24]) held_tag[q]<=1'b0;
            else if (p_v[21]) held_tag[q] <= p_tag[q];
    end endgenerate
`ifndef SYNTHESIS
    always @(posedge clk) if (reset_final[0] && i_v && p_v[21])
        $fatal(1, "static INT8 compiler calendar overlapped packed lines (ot_smh_int8_tile)");
`endif
    assign o_v = r_v;
    assign o_sel = r_sel;
    assign o_tag = r_tag;
    assign o_data = r_data;
endmodule
