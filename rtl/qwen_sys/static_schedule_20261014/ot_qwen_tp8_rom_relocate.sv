`timescale 1ns/1ps
// Source cmd380 ABI: rtl/physical/ot_qfd_tt_ctlm_split.sv assign cmd.
// Only ROM descriptors change: resident weights use 512 words/layer and
// resident BF16 row scales use 816 DENSE words/layer. Head bases18432/29376.
// Native WSRC1 descriptors retain their exact KV addressing and payload.
// stage MUST accompany this same command through its actual physical path.
// Combinational consumer adds NO edge; any physical capture added by parent
// must be represented in its compiled command/XS/tree calendar.
module ot_qwen_tp8_rom_relocate(
 input wire[379:0] in_cmd,
 input wire[5:0] in_stage,
 output wire[379:0] out_cmd,
 output wire fault
);
 wire rom=in_cmd[0]&&!in_cmd[55];
 wire valid_stage=in_stage>=1&&in_stage<=37;
 wire head=in_stage==37;
 wire[23:0] code_base=head?24'd18432:(in_stage-6'd1)*24'd512;
 wire[23:0] scale_base=head?24'd29376:(in_stage-6'd1)*24'd816;
 wire[24:0] code_sum={1'b0,in_cmd[79:56]}+{1'b0,code_base};
 wire[24:0] scale_sum={1'b0,in_cmd[278:255]}+{1'b0,scale_base};
 assign out_cmd={in_cmd[379:279],rom?scale_sum[23:0]:in_cmd[278:255],
                 in_cmd[254:80],rom?code_sum[23:0]:in_cmd[79:56],in_cmd[55:0]};
 assign fault=rom&&(!valid_stage||code_sum[24]||scale_sum[24]||
              in_cmd[79:56]>=(head?24'd1600:24'd512)||
              in_cmd[278:255]>=(head?24'd1200:24'd816));
endmodule
