from pathlib import Path
r=Path(__file__).resolve().parent
s=(r/'tb_hp_calr.sv').read_text()
a=s.index('    qfd_tt_ctlm_dv_lpf_hp_lp #(');b=s.index(' u_lp (',a)
s=s[:a]+'    qfd_tt_ctlm_dv_hp_h16z_native32'+s[b:]
(r/'tb_hp_native.sv').write_text(s)
f=(r/'hp_calr.f').read_text().splitlines();f=[p for p in f if p not in ['rtl/qwen_dv/headprep/lp_h16z/qfd_tt_ctlm_dv_lpf_hp_lp.sv','tb_hp_calr.sv']]+['hp_native32.v','hp_native32_helpers.sv','tb_hp_native.sv']
(r/'hp_native_compare.f').write_text('\n'.join(f)+'\n')
