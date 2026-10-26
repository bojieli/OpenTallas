import pathlib,subprocess,json,hashlib
r=pathlib.Path(__file__).resolve().parent;o=r.parent/'qbank_current2';o.mkdir(exist_ok=True);vl=str(pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator');cs=[]
for align in [0,1]:
 obj=o/f'obj_a{align}'
 with (o/f'build_a{align}.log').open('w') as f:p=subprocess.run([vl,'--binary','--timing','-j','4','-Wno-fatal','-Wno-lint','--top-module','tb_qbank',f'-GALIGN={align}','--Mdir',str(obj),str(r/'qbank.sv'),str(r/'sram.v'),str(r/'tb_qbank.sv')],stdout=f,stderr=subprocess.STDOUT)
 assert p.returncode==0,'BUILD FAILED'
 for gap in [1,2]:
  p=subprocess.run([str(obj/'Vtb_qbank'),f'+GAP={gap}'],capture_output=True,text=True);text=p.stdout+p.stderr;n=f'a{align}_g{gap}';(o/(n+'.log')).write_text(text);cs.append(dict(name=n,rc=p.returncode,pass_marker='QB_PASS' in text,fail_marker='QB_FAIL' in text,binary_sha256=hashlib.sha256((obj/'Vtb_qbank').read_bytes()).hexdigest()));print(cs[-1],flush=True)
(o/'record.json').write_text(json.dumps(dict(source='28cb06f38',macro_model_source='95781db13; current binding confirmation pending',selected_params={'QB_ALIGN':0,'QB_LOCAL32':0},source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in r.iterdir() if p.is_file()},cases=cs),indent=2)+'\n')
raise SystemExit(0 if cs[0]['pass_marker'] else 1)
