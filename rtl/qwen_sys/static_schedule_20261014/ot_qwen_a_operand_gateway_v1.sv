`timescale 1ns/1ps
// Source-preserving partition of the real SU controller A-operand path.
// State reset/enable and decoder order are unchanged. No row SRAM or issue gate.
module ot_qwen_a_operand_gateway_v1 #(
 parameter integer SW=64,AW=24,NW=18,HID=4096,EMB_CODE_LANES=64,
 parameter integer EMB_ADDR_BASE=0,INT8_EMBED=1,QWEN_FULLSHAPE=1
)(
 input wire clk,rst_n,start_idle,su_go,a_src,
 input wire[NW-1:0]token,tok_r,
 input wire[SW-1:0]a_re,input wire[SW*AW-1:0]a_addr,
 output wire[SW*32-1:0]a_q,
 output wire[SW-1:0]vm_re,output wire[SW*AW-1:0]vm_addr,
 input wire[SW*32-1:0]vm_q,
 output wire embed_code_re,output wire[AW-1:0]embed_code_addr,
 input wire[EMB_CODE_LANES*8-1:0]embed_code_q,
 output wire embed_scale_re,output wire[NW-1:0]embed_scale_addr,
 input wire[15:0]embed_scale_q,output wire[SW-1:0]embed_faults
);
    reg embed_active, embed_scale_pending;
    reg [15:0] embed_scale_hold;
    reg [SW-1:0] embed_sel;
    reg [SW*$clog2(EMB_CODE_LANES)-1:0] embed_lanes;
    assign embed_scale_re = (INT8_EMBED != 0) && start_idle;
    assign embed_scale_addr = token;
    assign embed_code_re = (INT8_EMBED != 0) && (|(a_re & {SW{embed_active}}));
    // The stream's element address is AW bits; token*HID wraps for vocab
    // rows >= 2^(AW-log2(HID)). Recover the in-row offset from those low
    // bits, then form the code-word address from the full NW-bit token.
    assign embed_code_addr = (QWEN_FULLSHAPE != 0) ?
        ((tok_r * (HID / EMB_CODE_LANES)) +
         (((a_addr[0 +: AW] - EMB_ADDR_BASE) & (HID - 1)) /
          EMB_CODE_LANES)) :
        ((a_addr[0 +: AW] - EMB_ADDR_BASE) >> $clog2(EMB_CODE_LANES));
    assign vm_re = a_re & ~({SW{(INT8_EMBED != 0) && embed_active}});
    assign vm_addr = a_addr;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            embed_active <= 1'b0;
            embed_scale_pending <= 1'b0;
            embed_sel <= 0;
        end else begin
            if (su_go) embed_active <= (INT8_EMBED != 0) && a_src;
            embed_scale_pending <= embed_scale_re;
            embed_sel <= a_re & {SW{(INT8_EMBED != 0) && embed_active}};
        end
    end
    always @(posedge clk) begin
        if (embed_scale_pending) embed_scale_hold <= embed_scale_q;
    end
    genvar el;
    generate if (INT8_EMBED != 0) begin : g_int8_embed
    for (el = 0; el < SW; el = el + 1) begin : g_embed_decode
        localparam integer ELI = $clog2(EMB_CODE_LANES);
        always @(posedge clk) embed_lanes[el*ELI +: ELI] <= a_addr[el*AW +: ELI];
        wire [31:0] decoded;
        wire bad;
        ot_hdc_qwen_int8_embed_decode u_decode (
            .code(embed_code_q[8*embed_lanes[el*ELI +: ELI] +: 8]),
            .scale(embed_scale_hold), .value(decoded), .fault(bad));
        assign a_q[el*32 +: 32] = embed_sel[el] ? decoded : vm_q[el*32 +: 32];
        assign embed_faults[el] = embed_sel[el] && bad;
    end
    end else begin : g_plain_embed
        assign a_q = vm_q;
        assign embed_faults = 0;
    end endgenerate
endmodule
