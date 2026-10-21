from pathlib import Path
import hashlib,json,re,os
O=Path(os.environ.get('CANDIDATE_DIR','results/rtl/qw_head_safe32_1020/generate_r5'));v=(O/'native32.v').read_text()
name='ot_qfd_tt_ctlm_static_hr_safe32_native32'
needle='module '+name+'('
assert v.count(needle)==1
v=v.replace(needle,'module '+name+' #(parameter integer STAGE_ME=1, parameter integer SEGCAL=1) (')
end=v.rfind('endmodule');assert end>0
v=v[:end]+'initial if(STAGE_ME!=1 || SEGCAL!=1) $error("native32 candidate is specialized STAGE_ME1 SEGCAL1");\n'+v[end:]
(O/'native32_param.v').write_text(v)
a=Path('rtl/qwen_dv/qfd_tt_ctlm_dv.sv').read_text();needle='ot_qfd_tt_ctlm_static_hr #(';assert a.count(needle)==1
b=a.replace(needle,name+' #(')
Path('rtl/qwen_dv/qfd_tt_ctlm_dv_native32_parent.sv').write_text(b)
src=Path('rtl/test/qwen_dv/tt_ctlm_dv_sources.f').read_text().splitlines();src=['rtl/qwen_dv/qfd_tt_ctlm_dv_native32_parent.sv'if x=='rtl/qwen_dv/qfd_tt_ctlm_dv.sv'else x for x in src]
src += [str(O/'native32_param.v'),'physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v']
if (O/'native32_helpers.sv').exists():src.append(str(O/'native32_helpers.sv'))
Path('rtl/test/qwen_dv/tt_ctlm_dv_native32_sources.f').write_text('\n'.join(src)+'\n')
tb=Path('rtl/test/qwen_dv/tb_qfd_tt_ctlm_prog.sv').read_text()
for signal in ['fixed_issue','fixed_end','fixed_pc','fixed_unit']:
 tb=tb.replace('`TB_HEAD.'+signal,'dut.g_hard_hr.u_hr.'+chr(92)+'u_head.'+signal+' ')
Path('rtl/test/qwen_dv/tb_qfd_tt_ctlm_native32_prog.sv').write_text(tb)
s=Path('rtl/test/qwen_dv/tt_ctlm_prog_bench.py').read_text().replace('tt_ctlm_dv_sources.f','tt_ctlm_dv_native32_sources.f').replace("HERE / 'tb_qfd_tt_ctlm_prog.sv'","HERE / 'tb_qfd_tt_ctlm_native32_prog.sv'")
Path('rtl/test/qwen_dv/tt_ctlm_prog_native32_bench.py').write_text(s)
(O/'parent_binding.json').write_text(json.dumps(dict(original_parent_sha256=hashlib.sha256(a.encode()).hexdigest(),bench_parent_sha256=hashlib.sha256(b.encode()).hexdigest(),emitted_source_sha256=hashlib.sha256(v.encode()).hexdigest(),parameters=dict(STAGE_ME=1,SEGCAL=1),qualification='new named opt-in source vehicle; existing parent untouched'),indent=2)+'\n')
