import pathlib,subprocess,json
r=pathlib.Path.cwd();rows=[]
for label in ['landw107final','landw116final','landwn107final','landwn116final']:
 d=r/'native_synth_out'/label/'work/orfs'; out=d/'textbook_depth.json'
 p=subprocess.run(['python3','tools/textbook_lint.py','check','--netlist',str(d/'1_2_yosys.raw.v'),'--out',str(out),'--set','hf_report=32','hf_max=32','hf_port_refuse=32','hf_reset_refuse=32','hf_refuse=32'],text=True,capture_output=True)
 (d/'textbook_depth.log').write_text(p.stdout+p.stderr);print(label,p.returncode,p.stdout[-200:],flush=True);rows.append(dict(label=label,rc=p.returncode))
(r/'results/arch/qw_landw_fan32_1020/synth/final_depth_summary.json').write_text(json.dumps(rows,indent=2))
