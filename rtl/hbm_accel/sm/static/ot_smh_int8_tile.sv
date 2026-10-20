`timescale 1ns/1ps
// LH-SMATT/INT8 (10-19, COORD 0ki): hardened SAFE successor of ot_smh_static_int8 for ot_hbm_accel_smh_attn #(ENABLE_INT8=1).
// Cycle-exact with ot_smh_static_int8 (ot_hbm_accel_int8_line PIPE 1 behind a static wrapper, m_ready tied 1): a packed
// INT8 line (128 signed codes) presented with i_v in cycle t leaves as two BF16 lines, low 64 codes in cycle t+2 and
// high 64 codes in cycle t+3, both carrying the input tag; o_data is the 1024-bit weight field (the 64 scale bits of the
// line are zero for fmt 3 and are supplied as constants by the parent).  Same calendar: one packed line per two edges.
// SAFE structure (kit physical/ref_tile/smh_int8_t1 README):
//  - every input is registered at its pin (p_codes / p_tag / p_v[*]) and every output is driven by its own register
//    (o_data / o_tag / o_v / o_sel[*]); no combinational in->out path;
//  - one logic stage: a lane's 8-bit sign-magnitude classify + BF16 encode (~12 levels) between p_codes and o_data;
//  - no register drives more than 32 loads: the 512-bit low/high select uses 16 kept copies (32 bits each), the
//    parent's 1099-bit merge select is delivered as NSEL=35 kept output copies (o_sel[k] serves bits 32k..32k+31);
//  - no data enables: o_data and hi_codes load every edge (values outside a valid beat are never selected by the
//    parent: f_packet = o_sel ? {o_v, o_tag, 64'd0, o_data} : raw), so the data path has no enable fanout;
//  - no runtime-indexed storage, no flop delay line >= 3 (hi_codes holds one line for one edge);
//  - static: no ready / credit; an overlapping line is a parent schedule_fault (unchanged glue in smh_attn).
`ifdef OT_INT8_MUT_SIGN          // the parent bench's converter sign mutant (qwen_sm_mv_unit --mut sign) reaches this tile too
`ifndef OT_I8T_MUT_SIGN
`define OT_I8T_MUT_SIGN
`endif
`endif
module ot_smh_int8_tile (
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
    localparam integer NG = 16;        // select groups: 4 lanes = 32 code bits each
    localparam integer NSEL = 35;
    // ---- input pin registers --------------------------------------------------------------------------------------
    // i_v lands in 22 kept copies (the pin net has 22 sinks): [15:0] -> pend, [17:16] -> pend_s, [18] -> pend_c,
    // [20:19] -> the o_sel halves, [21] -> o_v / tag control.  Every copy below drives <= 32 loads.
    (* keep *) reg [21:0] p_v;
    reg [9:0]    p_tag;
    reg [1023:0] p_codes;
    always @(posedge clk) begin
        p_tag   <= i_tag;
        p_codes <= i_codes;
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) p_v <= 22'd0;
        else        p_v <= {22{i_v}};
    // ---- second half holding register + kept select copies ---------------------------------------------------------
    reg [511:0] hi_codes;
    (* keep *) reg [NG-1:0] pend;      // the next beat is the high half (one copy per 32-bit group)
    (* keep *) reg [1:0]    pend_s;    // copies for the two o_sel halves
    (* keep *) reg          pend_c;    // copy for o_v
    always @(posedge clk) hi_codes <= p_codes[1023:512];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin pend <= {NG{1'b0}}; pend_s <= 2'd0; pend_c <= 1'b0; end
`ifdef OT_I8T_MUT_PEND
        else begin pend <= {NG{1'b0}}; pend_s <= 2'd0; pend_c <= 1'b0; end   // mutant: never emits the high half
`else
        else begin pend <= p_v[15:0]; pend_s <= p_v[17:16]; pend_c <= p_v[18]; end
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
        wire [7:0] code = pend[l / 4] ? hi_codes[8*l +: 8] : p_codes[8*l +: 8];
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
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin r_v <= 1'b0; r_sel <= {NSEL{1'b0}}; r_tag <= 10'd0; held_tag <= 10'd0; end
        else begin
            r_v   <= p_v[21] | pend_c;
            r_sel <= {{(NSEL-18){p_v[20] | pend_s[1]}}, {18{p_v[19] | pend_s[0]}}};
            if (p_v[21]) held_tag <= p_tag;
`ifdef OT_I8T_MUT_TAG
            r_tag <= held_tag;                             // mutant: low beat carries the previous line's tag
`else
            r_tag <= p_v[21] ? p_tag : held_tag;
`endif
        end
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n && i_v && p_v[21])
        $fatal(1, "static INT8 compiler calendar overlapped packed lines (ot_smh_int8_tile)");
`endif
    assign o_v = r_v;
    assign o_sel = r_sel;
    assign o_tag = r_tag;
    assign o_data = r_data;
endmodule
