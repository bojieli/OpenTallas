`timescale 1ns/1ps
// QW-H16V 10-20: ot_qwen_tp8_rom_relocate with the stage-derived terms (valid_stage, head, code_base, scale_base)
// supplied precomputed (registered by the parent together with the stage, from the same next value).  The command
// arithmetic, fields and fault are the exact expressions of rtl/qwen_sys/static_schedule_20261014/ot_qwen_tp8_rom_relocate.sv.
module ot_qwen_tp8_rom_relocate_base(
 input wire[5:0] in_stage,
 output wire valid_stage, output wire head,
 output wire[23:0] code_base, output wire[23:0] scale_base
);
 assign valid_stage=in_stage>=1&&in_stage<=37;
 assign head=in_stage==37;
 assign code_base=head?24'd18432:(in_stage-6'd1)*24'd512;
 assign scale_base=head?24'd29376:(in_stage-6'd1)*24'd816;
endmodule
module ot_qwen_tp8_rom_relocate_pb(
 input wire[379:0] in_cmd,
 input wire valid_stage, input wire head,
 input wire[23:0] code_base, input wire[23:0] scale_base,
 output wire[379:0] out_cmd,
 output wire fault
);
 wire rom=in_cmd[0]&&!in_cmd[55];
 wire[24:0] code_sum, scale_sum;               // {carry, sum} of the 24-bit adds (Kogge-Stone, kept levels)
 ot_hdc_add_ks #(.W(24)) u_code (.a(in_cmd[79:56]),.b(code_base),.s(code_sum[23:0]),.cout(code_sum[24]));
 ot_hdc_add_ks #(.W(24)) u_scale (.a(in_cmd[278:255]),.b(scale_base),.s(scale_sum[23:0]),.cout(scale_sum[24]));
 assign out_cmd={in_cmd[379:279],rom?scale_sum[23:0]:in_cmd[278:255],
                 in_cmd[254:80],rom?code_sum[23:0]:in_cmd[79:56],in_cmd[55:0]};
 assign fault=rom&&(!valid_stage||code_sum[24]||scale_sum[24]||
              in_cmd[79:56]>=(head?24'd1600:24'd512)||
              in_cmd[278:255]>=(head?24'd1200:24'd816));
endmodule
