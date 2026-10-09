#!/usr/bin/env python3
"""Additive, default-off SRAM read station; leave the pinned sysctl sources intact."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'rtl/qwen_sys/system_20261008'


def replace_one(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def emit():
    s = (OUT / 'ot_qfd_prompt_sram.sv').read_text()
    s = replace_one(s, 'module ot_qfd_prompt_sram #(parameter integer MUT=0)',
                    'module ot_qfd_prompt_sram_pb2 #(parameter integer READ_STATION=0, MUT=0)')
    s = replace_one(s, ' wire [18:0] dec=decode(rd[lane*32+:24]);', ''' // Capture every physical SRAM output before lane selection and ECC. These
 // 192 used codeword DFF sinks are placed at the macro pins by the physical kit.
 wire [255:0] read_word; wire [2:0] read_lane; wire read_valid;
 generate if(READ_STATION!=0) begin:g_read_station
  reg [191:0] cap; reg [2:0] cap_lane; reg cap_valid;
  integer cc;
  genvar cl;
  always @(posedge clk) begin
   for(cc=0;cc<8;cc=cc+1) cap[cc*24+:24]<=rd[cc*32+:24];
   cap_lane<=lane;
  end
  always @(posedge clk or negedge rst_n)
   if(!rst_n) cap_valid<=0; else cap_valid<=valid;
  for(cl=0;cl<8;cl=cl+1) begin:g_cap_word
   assign read_word[cl*32+:32]={8'b0,cap[cl*24+:24]};
  end
  assign read_lane=cap_lane; assign read_valid=cap_valid;
 end else begin:g_read_bypass
  assign read_word=rd; assign read_lane=lane; assign read_valid=valid;
 end endgenerate
 wire [18:0] dec=decode(read_word[read_lane*32+:24]);''')
    s = replace_one(s, 'else if(valid && dec[18])', 'else if(read_valid && dec[18])')
    (OUT / 'ot_qfd_prompt_sram_pb2.sv').write_text(s)

    s = (ROOT / 'rtl/host/ot_host_if.sv').read_text()
    s = replace_one(s, 'module ot_host_if #(\n',
                    'module ot_host_if_pb2 #(\n    parameter integer PB_READ_PIPE = 0,\n')
    s = replace_one(s, 'I_GO = 4, I_RUN = 5;', 'I_GO = 4, I_RUN = 5, I_PB_WAIT = 6;')
    s = replace_one(s, 'I_RD: i_st <= I_WAIT;                    // prompt-buffer read (below)',
                    '''I_RD: i_st <= (PB_READ_PIPE && sl_pos[eng_slot] < sl_plen[eng_slot])
                                      ? I_PB_WAIT : I_WAIT;
                    I_PB_WAIT: i_st <= I_WAIT; // complete row/lane/valid capture before ECC''')
    (OUT / 'ot_host_if_pb2.sv').write_text(s)

    s = (OUT / 'ot_qfd_sysctl.sv').read_text()
    s = replace_one(s, 'module ot_qfd_sysctl #(\n',
                    'module ot_qfd_sysctl_pb2 #(\n    parameter integer PROMPT_READ_STATION = 0,\n')
    s = replace_one(s, 'ot_qfd_prompt_sram u_pb(',
                    'ot_qfd_prompt_sram_pb2 #(.READ_STATION(PROMPT_READ_STATION)) u_pb(')
    s = replace_one(s, 'ot_host_if #(',
                    'ot_host_if_pb2 #(.PB_READ_PIPE(PROMPT_SRAM && PROMPT_READ_STATION), ')
    (OUT / 'ot_qfd_sysctl_pb2.sv').write_text(s)

    s = (OUT / 'ot_qfd_sysctl_stn.sv').read_text()
    s = replace_one(s, 'module ot_qfd_sysctl_stn #(\n',
                    'module ot_qfd_sysctl_stn_pb2 #(\n    parameter integer PROMPT_READ_STATION = 0,\n')
    s = replace_one(s, 'ot_qfd_sysctl #(',
                    'ot_qfd_sysctl_pb2 #(.PROMPT_READ_STATION(PROMPT_READ_STATION), ')
    (OUT / 'ot_qfd_sysctl_stn_pb2.sv').write_text(s)

    s = (ROOT / 'rtl/test/qwen_system/tb_qfd_ctl_stn.sv').read_text()
    s = s.replace('tb_qfd_ctl_stn', 'tb_qfd_ctl_stn_pb2')
    s = replace_one(s, 'ot_qfd_sysctl_stn #(',
                    'ot_qfd_sysctl_stn_pb2 #(.PROMPT_READ_STATION(1), ')
    (ROOT / 'rtl/test/qwen_system/tb_qfd_ctl_stn_pb2.sv').write_text(s)

    s = (ROOT / 'rtl/test/qwen_system/tb_qfd_prompt_sram_fault.sv').read_text()
    s = s.replace('tb_qfd_prompt_sram_fault', 'tb_qfd_prompt_sram_pb2_fault')
    s = replace_one(s, 'ot_qfd_prompt_sram #(.MUT(MUT))',
                    'ot_qfd_prompt_sram_pb2 #(.READ_STATION(1),.MUT(MUT))')
    s = replace_one(s, 'force dut.rd=inject;\n    sampled(0);',
                    'force dut.rd=inject;\n    repeat(2) begin @(posedge clk);#1;end\n    sampled(0);')
    s = replace_one(s, '// UE appears immediately on q; sticky fault captures on following edge.\n    @(posedge clk);#1;if(q!==0) bad=bad+1;',
                    '// Row capture is one edge later; sticky UE follows the matching valid.\n    repeat(2) begin @(posedge clk);#1;end\n    if(q!==0) bad=bad+1;')
    (ROOT / 'rtl/test/qwen_system/tb_qfd_prompt_sram_pb2_fault.sv').write_text(s)
    print('SYSCTL_PROMPT_READ_EMIT_PASS additive_sources=6 capture_bits=192 prompt_edges=1 decode_edges=0')


if __name__ == '__main__':
    emit()
