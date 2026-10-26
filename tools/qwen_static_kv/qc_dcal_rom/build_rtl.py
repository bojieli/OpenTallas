#!/usr/bin/env python3
"""Opt-in QC live calendar-image macro; existing sources remain unchanged."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[3]
D=ROOT/'rtl/qwen_sys/d2d_static_20261015'

def build():
    core=(D/'ot_qwen_d2d_cal_seq.sv').read_text()
    core=core.replace('module ot_qwen_d2d_cal_seq #(', 'module ot_qwen_d2d_cal_seq_image64 #(parameter IMAGE_VIAMAP = "", parameter IMAGE_INSTANCE = "qc_dcal_image",')
    core='\n'.join(l for l in core.splitlines() if not ('parameter ' in l and re.search(r'\b(?:TX_IMG|RX_IMG)\b',l.split('//')[0])))+'\n'
    core=core.replace("cfg_data <= ip[0] ? RX_IMG[32*x +: 32] : TX_IMG[32*x +: 32];", "cfg_data <= ip[0] ? image_q[63:32] : image_q[31:0];")
    insert='''    // INIT emits TX then RX for each row. Fetch the next row on the RX
    // edge, so the following TX observes the real synchronous macro output.
    // The reset/idle address is zero, preparing the first image row before use.
    wire [5:0] image_addr = (!rst_n || !init || ip >= 2*NE) ? 6'd0 : 6'((ip + 1'b1) >> 1);
    wire [63:0] image_q;
    ot_rom_64x64_m2 #(.VIAMAP(IMAGE_VIAMAP), .INSTANCE(IMAGE_INSTANCE)) u_image (
        .clk(ck), .ce_in(1'b1), .addr_in(image_addr), .rd_out(image_q));
    initial if (NE != 32) $fatal(1, "QC image-ROM profile requires NE32");
'''
    core=core.replace('    integer x;',insert+'    integer x;')
    assert not re.search(r'\b(?:TX_IMG|RX_IMG)\[',re.sub(r'//[^\n]*','',core))
    ovl=(D/'ot_qwen_d2d_ovl_seq.sv').read_text()
    ovl=ovl[ovl.index('module ot_qwen_d2d_ovl_seq #('):]
    ovl=ovl.replace('module ot_qwen_d2d_ovl_seq #(', 'module ot_qwen_d2d_ovl_seq_image64 #(parameter IMAGE_VIAMAP = "", parameter IMAGE_INSTANCE = "qc_dcal_image",')
    ovl='\n'.join(l for l in ovl.splitlines() if not ('parameter ' in l and re.search(r'\b(?:TX_IMG|RX_IMG)\b',l.split('//')[0])))+'\n'
    ovl=ovl.replace('ot_qwen_d2d_cal_seq #(.NE(NE), .NL(1), .TX_IMG(TX_IMG), .RX_IMG(RX_IMG),', 'ot_qwen_d2d_cal_seq_image64 #(.IMAGE_VIAMAP(IMAGE_VIAMAP), .IMAGE_INSTANCE(IMAGE_INSTANCE), .NE(NE), .NL(1),')
    top=(D/'qfd_d2d_cal_seq_ovl_rope.sv').read_text()
    top=top.replace('module qfd_d2d_cal_seq_ovl_rope #(', 'module qfd_d2d_cal_seq_ovl_rope_image64 #(parameter IMAGE_VIAMAP = "",')
    top=top.replace('ot_qwen_d2d_ovl_seq #(.MUT_HALT_REWIND(MUT_HALT_REWIND), .TX_IMG(OVL_C_TX_IMG), .RX_IMG(OVL_C_RX_IMG),', 'ot_qwen_d2d_ovl_seq_image64 #(.IMAGE_VIAMAP(IMAGE_VIAMAP), .MUT_HALT_REWIND(MUT_HALT_REWIND),')
    for name,text in [('ot_qwen_d2d_cal_seq_image64.sv',core),('ot_qwen_d2d_ovl_seq_image64.sv',ovl),('qfd_d2d_cal_seq_ovl_rope_image64.sv',top)]:
        (D/name).write_text('// Generated opt-in candidate by tools/qwen_static_kv/qc_dcal_rom/build_rtl.py.\n'+text)

if __name__=='__main__':build()
