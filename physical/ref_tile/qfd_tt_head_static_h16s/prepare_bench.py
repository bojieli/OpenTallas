#!/usr/bin/env python3
"""qfd_tt_head_static_h16s bench vehicle: same transformation as results/rtl/qw_head_safe32_1020/prepare_native_parent.py
(Codex 02:06) but reads the COMMITTED native32_param.v (bound_r3) instead of regenerating it from native32.v."""
from pathlib import Path
O=Path('results/rtl/qw_head_safe32_1020/bound_r3');name='ot_qfd_tt_ctlm_static_hr_safe32_native32'
assert (O/'native32_param.v').read_text().count('module '+name+' #(')==1
a=Path('rtl/qwen_dv/qfd_tt_ctlm_dv.sv').read_text();needle='ot_qfd_tt_ctlm_static_hr #(';assert a.count(needle)==1
Path('rtl/qwen_dv/qfd_tt_ctlm_dv_native32_parent.sv').write_text(a.replace(needle,name+' #('))
src=Path('rtl/test/qwen_dv/tt_ctlm_dv_sources.f').read_text().splitlines()
src=['rtl/qwen_dv/qfd_tt_ctlm_dv_native32_parent.sv' if x=='rtl/qwen_dv/qfd_tt_ctlm_dv.sv' else x for x in src]
src+=[str(O/'native32_param.v'),'physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v',str(O/'native32_helpers.sv')]
Path('rtl/test/qwen_dv/tt_ctlm_dv_native32_sources.f').write_text('\n'.join(src)+'\n')
tb=Path('rtl/test/qwen_dv/tb_qfd_tt_ctlm_prog.sv').read_text()
for s in ['fixed_issue','fixed_end','fixed_pc','fixed_unit']:tb=tb.replace('`TB_HEAD.'+s,'dut.g_hard_hr.u_hr.'+chr(92)+'u_head.'+s+' ')
Path('rtl/test/qwen_dv/tb_qfd_tt_ctlm_native32_prog.sv').write_text(tb)
s=Path('rtl/test/qwen_dv/tt_ctlm_prog_bench.py').read_text().replace('tt_ctlm_dv_sources.f','tt_ctlm_dv_native32_sources.f').replace("HERE / 'tb_qfd_tt_ctlm_prog.sv'","HERE / 'tb_qfd_tt_ctlm_native32_prog.sv'")
Path('rtl/test/qwen_dv/tt_ctlm_prog_native32_bench.py').write_text(s)
