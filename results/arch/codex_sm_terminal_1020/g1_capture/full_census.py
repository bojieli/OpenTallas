import pathlib,re,subprocess,json
root=pathlib.Path('/srv/opentallas-scratch/claude/ref_gate/smh_rp4hs_a_km64-20261019-214641/src')
kit=root/'physical/ref_tile/smh_rp4hs_a_km64'
spec=json.load(open(kit/'spec.json'))
defs=['-DSYNTHESIS']+['-D'+d for d in spec.get('defines',[])]
# Check the original kit property rather than silently dropping its defines.
if not defs: raise RuntimeError('missing original hard-build defines')
files=[str(root/f) for f in spec['sources']]
files=[str(pathlib.Path('ot_hbm_smh_rp4_clocks.sv').resolve()) if f.endswith('/ot_hbm_smh_rp4_clocks.sv') else f for f in files]
files.append(str(pathlib.Path('ot_rp4_g1_capture.sv').resolve()))
text='read_verilog -sv '+' '.join(defs+['-DOT_SMH_G1_CAPTURE']+files)+';\n'
for macro in spec['children']:
 path=macro.get('view') or macro.get('path')
 if not path: print(macro);raise RuntimeError('macro view schema')
 libs=list((root/path).glob('*_tt.lib'))
 if len(libs)!=1:raise RuntimeError((path,libs))
 text+='read_liberty -lib -overwrite '+str(libs[0])+';\n'
text+='hierarchy -check -top ot_hbm_smh_rp4h_s; tcl '+str(root/'physical/common_flow/ot_keep_regs.tcl')+'; synth -top ot_hbm_smh_rp4h_s -flatten; '
libs=pathlib.Path('/srv/opentallas-scratch/claude/l2h-pvmd/census/libs')
text+='dfflibmap -liberty '+str(libs/'asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib')+'; '
text+='abc '+' '.join('-liberty '+str(libs/n) for n in ['asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib','asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib','asap7sc7p5t_AO_RVT_TT_nldm_211120.lib','asap7sc7p5t_OA_RVT_TT_nldm_211120.lib'])+'; opt_clean -purge; write_verilog -noattr full_mapped.v; stat\n'
pathlib.Path('full.ys').write_text(text)
with open('full_synth.log','w') as out:subprocess.run(['yosys','-Q','-T','-s','full.ys'],stdout=out,stderr=subprocess.STDOUT,check=True)
subprocess.run(['python3','textbook_lint.py','check','--netlist','full_mapped.v','--top','ot_hbm_smh_rp4h_s','--out','full_census32.json','--set','hf_report=32','hf_max=32','hf_port_refuse=32','hf_reset_refuse=32','hf_refuse=32','--mode','refuse'],check=True)
