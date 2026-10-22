import pathlib,subprocess,json,hashlib
r=pathlib.Path(__file__).resolve().parent;o=r/'proof';o.mkdir(exist_ok=True)
vl=pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
assert '5.050' in subprocess.check_output([str(vl),'--version'],text=True)
cases=[]
for mut in [0,1]:
 obj=o/f'obj_mut{mut}'
 cmd=[str(vl),'--binary','--timing','-j','4','-Wno-fatal','-Wno-lint','--top-module','tb_qbank','-GALIGN=1','-GLOCAL=1',f'-GMUT={mut}','--Mdir',str(obj),str(r/'qbank.sv'),str(r/'sram.v'),str(r/'tb_qbank_local.sv')]
 with (o/f'build_mut{mut}.log').open('w') as f:subprocess.run(cmd,check=True,stdout=f,stderr=subprocess.STDOUT)
 for gap in ([1,2] if not mut else [1]):
  p=subprocess.run([str(obj/'Vtb_qbank'),f'+GAP={gap}'],capture_output=True,text=True);s=p.stdout+p.stderr;(o/f'mut{mut}_gap{gap}.log').write_text(s)
  ok=(p.returncode==0 and f'QB_PASS ALIGN=1 LOCAL32=1 GAP={gap} rows=32 checks=512' in s) if not mut else (p.returncode!=0 and 'QB_FAIL' in s and 'QB_MISMATCH' in s)
  c=dict(mut=mut,gap=gap,rc=p.returncode,expected=ok,binary_sha256=hashlib.sha256((obj/'Vtb_qbank').read_bytes()).hexdigest());cases.append(c);print(c,flush=True)
(o/'record.json').write_text(json.dumps({'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [r/'qbank.sv',r/'sram.v',r/'tb_qbank_local.sv',r/'run_local.py']},'params':{'QB_ALIGN':1,'QB_LOCAL32':1},'cases':cases},indent=2)+'\n')
assert all(c['expected'] for c in cases),'LOCAL32 proof failed'
print('QBANK_LOCAL32_PROOF_PASS',flush=True)
