from pathlib import Path
import importlib.util,subprocess,json,sys,hashlib
r=Path(sys.argv[1]).resolve();base='d2c8e45a7'
spec=importlib.util.spec_from_file_location('lp',r/'tools/landed_parent/lp.py');lp=importlib.util.module_from_spec(spec);spec.loader.exec_module(lp)
macrofiles={'ot_qfd_tt_ctlm_static_hr_safe32_native32_1r':'rtl/qwen_dv/headprep/h16z/native32_1r_param.v','ot_sram_1r1w_128x256_m1_r2c2':'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v','ot_sram_1r1w_64x512_m1_r2c2':'physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v','ot_sram_1r1w_32x128_m1':'physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v','ot_rom_4096x72_m8':'physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v','ot_rom_4096x266_m8':'physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v'}
libs=[];contracts={}
for mod,path in macrofiles.items():
 f=r/path
 if not f.exists():f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(subprocess.check_output(['git','show',base+':'+path]))
 data=f.read_bytes();m=lp.parse_module(lp.preprocess(data.decode(),[]),mod)
 ports={p['name']:dict(direction='input' if p['dir']=='in' else 'output',width=lp.eval_width(p['range'],m['params']),clock=p['name'] in ['clk','ck_head'])for p in m['ports']}
 row=dict(kind='physical_macro',source_sha256=hashlib.sha256(data).hexdigest(),ports=ports)
 if mod.startswith('ot_rom_'):row['parameter_types']={'VIAMAP':'string','INSTANCE':'string'}
 contracts[mod]=row
 params=' #(parameter VIAMAP="", parameter INSTANCE="")' if mod.startswith('ot_rom_') else ''
 s=f'(* blackbox *) module {mod}{params}('+','.join(ports)+');\n'
 for n,p in ports.items():s+=p['direction']+' wire '+(f'[{p["width"]-1}:0] 'if p['width']>1 else '')+n+';\n'
 s+='endmodule\n';libs.append(s)
(r/'native_macros.v').write_text('\n'.join(libs));(r/'native_macro_contracts.json').write_text(json.dumps(contracts,indent=2)+'\n')
files=[]
for f in (r/'source.f').read_text().splitlines():
 if f in macrofiles.values() or f=='calr/ot_rom_4096x266_m8_calrbench.v' or f.endswith('native32_helpers.sv'):continue
 files.append(f)
files.append('rtl/qwen_dv/headprep/lp_h16z/qfd_tt_ctlm_dv_lpf_hp_lp.sv')
ys=['read_verilog -sv -lib native_macros.v','read_verilog -sv -defer -D SYNTHESIS '+ ' '.join(dict.fromkeys(files))]
params=json.loads((r/'tools/landed_parent/specs/qfd_tt_ctlm_dv_lpf_hp_h16z.json').read_text())['params']
ys+=['hierarchy -top qfd_tt_ctlm_dv_lpf_hp_lp '+' '.join(f'-chparam {k} {v}' for k,v in params.items()),'synth -top qfd_tt_ctlm_dv_lpf_hp_lp -flatten -noabc -nofsm -noshare','check -assert','write_json generic_hp.json']
(r/'native_generic.ys').write_text('\n'.join(ys)+'\n')
p='tools/qwen_dv/ctlm6_bound_macro.py';f=r/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(subprocess.check_output(['git','show',base+':'+p]))
