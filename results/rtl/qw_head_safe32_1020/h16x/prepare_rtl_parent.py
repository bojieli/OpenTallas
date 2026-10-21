#!/usr/bin/env python3
"""QW-H16X RTL parent vehicle (H16X=1) = results/rtl/qw_head_safe32_1020/prepare_parent.py plus the h16v safe32 sources."""
from pathlib import Path
a = Path('rtl/qwen_dv/qfd_tt_ctlm_dv.sv').read_text(); needle = 'ot_qfd_tt_ctlm_static_hr #('; assert a.count(needle) == 1
Path('rtl/qwen_dv/qfd_tt_ctlm_dv_safe32_h16x_parent.sv').write_text(a.replace(needle, 'ot_qfd_tt_ctlm_static_hr_safe32 #(.H16X(1), '))
src = Path('rtl/test/qwen_dv/tt_ctlm_dv_sources.f').read_text().splitlines()
src = ['rtl/qwen_dv/qfd_tt_ctlm_dv_safe32_h16x_parent.sv' if x == 'rtl/qwen_dv/qfd_tt_ctlm_dv.sv' else x for x in src]
src += ['rtl/qwen_sys/static_schedule_20261014/safe32/' + x for x in ['ot_hdc_ks_helpers.sv', 'ot_hdc_dyn_ttiles_tab.sv',
        'ot_qwen_tp8_rom_relocate_pb.sv', 'ot_qwen_fixed_issue_ld.sv', 'ot_qfd_head_fifo4_sram.sv',
        'ot_qwen_rom_core_ctrl_static_safe32.sv', 'ot_qfd_tt_ctlm_head_static_rk_safe32.sv', 'ot_qfd_tt_ctlm_static_hr_safe32.sv']]
src += ['physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v']
Path('rtl/test/qwen_dv/tt_ctlm_dv_safe32_h16x_sources.f').write_text('\n'.join(src) + '\n')
s = Path('rtl/test/qwen_dv/tt_ctlm_prog_bench.py').read_text().replace('tt_ctlm_dv_sources.f', 'tt_ctlm_dv_safe32_h16x_sources.f')
Path('rtl/test/qwen_dv/tt_ctlm_prog_safe32_h16x_bench.py').write_text(s)
print('prepared')
