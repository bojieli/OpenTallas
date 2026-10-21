#!/usr/bin/env python3
"""qfd_tt_head_static_h16xb bench vehicle (QW-H16X 10-20, h16x/net_ifg2 H16X=1; = h16u vehicle): the h16t vehicle (prepare_native_parent.py transformation)
on the single-region netlist h16u/native32_1r_param.v.  The parent u_hr drops its .ck_pm0(ck)/.ck_pm1(ck) connections
(the head has one clock port ck_head, which the parent already drives with the same ck)."""
from pathlib import Path
O = Path('results/rtl/qw_head_safe32_1020/h16x/net_ifg2'); B = O
name = 'ot_qfd_tt_ctlm_static_hr_safe32_native32_1r'
assert (O/'native32_1r_param.v').read_text().count('module '+name+' #(') == 1
a = Path('rtl/qwen_dv/qfd_tt_ctlm_dv.sv').read_text(); needle = 'ot_qfd_tt_ctlm_static_hr #('; assert a.count(needle) == 1
ck = '.ck_head(ck), .ck_pm0(ck), .ck_pm1(ck),'; assert a.count(ck) == 1
a = a.replace(needle, name+' #(').replace(ck, '.ck_head(ck),')
Path('rtl/qwen_dv/qfd_tt_ctlm_dv_native32_1r_parent.sv').write_text(a)
src = Path('rtl/test/qwen_dv/tt_ctlm_dv_sources.f').read_text().splitlines()
src = ['rtl/qwen_dv/qfd_tt_ctlm_dv_native32_1r_parent.sv' if x == 'rtl/qwen_dv/qfd_tt_ctlm_dv.sv' else x for x in src]
src += [str(O/'native32_1r_param.v'), 'physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v',
        str(B/'native32_helpers.sv')]
Path('rtl/test/qwen_dv/tt_ctlm_dv_native32_1r_sources.f').write_text('\n'.join(src)+'\n')
tb = Path('rtl/test/qwen_dv/tb_qfd_tt_ctlm_prog.sv').read_text()
for s in ['fixed_issue', 'fixed_end', 'fixed_pc', 'fixed_unit']:
    tb = tb.replace('`TB_HEAD.'+s, 'dut.g_hard_hr.u_hr.'+chr(92)+'u_head.'+s+' ')
Path('rtl/test/qwen_dv/tb_qfd_tt_ctlm_native32_1r_prog.sv').write_text(tb)
s = Path('rtl/test/qwen_dv/tt_ctlm_prog_bench.py').read_text().replace('tt_ctlm_dv_sources.f', 'tt_ctlm_dv_native32_1r_sources.f')\
    .replace("HERE / 'tb_qfd_tt_ctlm_prog.sv'", "HERE / 'tb_qfd_tt_ctlm_native32_1r_prog.sv'")
Path('rtl/test/qwen_dv/tt_ctlm_prog_native32_1r_bench.py').write_text(s)
