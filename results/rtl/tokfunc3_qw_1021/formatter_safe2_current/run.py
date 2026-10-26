import pathlib,subprocess,os,json,hashlib
r=pathlib.Path(__file__).resolve().parent;o=r.parent/'formatter_current';o.mkdir(exist_ok=True)
vl=str(pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
with (o/'build.log').open('w') as f:p=subprocess.run([vl,'--binary','--timing','-j','4','-Wno-fatal','-Wno-lint','--top-module','tb_formatter','--Mdir',str(o/'obj'),str(r/'formatter.sv'),str(r/'tb_formatter.sv')],stdout=f,stderr=subprocess.STDOUT)
assert p.returncode==0,'build failure'
cases=[]
for mode,pos in [(0,255),(0,8191),(1,255),(2,255),(3,255)]:
 n=f'm{mode}_p{pos}';p=subprocess.run([str(o/'obj/Vtb_formatter'),f'+MODE={mode}',f'+POS={pos}'],capture_output=True,text=True);text=p.stdout+p.stderr;(o/(n+'.log')).write_text(text);good=p.returncode==0 and ('FMT_PASS' if mode==0 else 'FMT_CAUSAL_REJECT') in text;cases.append(dict(name=n,rc=p.returncode,ok=good));print(cases[-1],flush=True)
(o/'record.json').write_text(json.dumps(dict(source='91e9c3456',formatter_sha256=hashlib.sha256((r/'formatter.sv').read_bytes()).hexdigest(),binary_sha256=hashlib.sha256((o/'obj/Vtb_formatter').read_bytes()).hexdigest(),params={'ENABLE':1,'HEADS':1,'KV_FP8':1,'SAFE':2,'LOCAL_CTL':0},cases=cases),indent=2)+'\n')
raise SystemExit(0 if all(c['ok'] for c in cases) else 1)
