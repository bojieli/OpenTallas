import json,pathlib,shutil,subprocess,sys,time
k=pathlib.Path(sys.argv[1]);config=(k/'config.mk').read_text();srcs=next(l for l in config.splitlines()if l.startswith('export VERILOG_FILES = ')).split('=',1)[1].split();srcs=[str(k/s.removeprefix('/work/')) for s in srcs]
v=next((str(p)for p in [pathlib.Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator'),pathlib.Path('/home/ubuntu/.local/opentallas-tools/bin/verilator')]if p.exists()),shutil.which('verilator'))
if not v:raise RuntimeError('Verilator5.050 unavailable')
cmd=[v,'--binary','--timing','-O2','-Wno-fatal','-Wno-WIDTH','--top-module','tb','-Mdir',str(k/'obj'),'-j','8',*srcs,str(k/'tb.sv')]
start=time.time()
with (k/'bench_build.log').open('w')as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
if r.returncode:raise RuntimeError('actual native miter build failed; see bench_build.log')
with (k/'bench_run.log').open('w')as f:r=subprocess.run([str(k/'obj/Vtb')],cwd=k,stdout=f,stderr=subprocess.STDOUT)
s=(k/'bench_run.log').read_text();ok=r.returncode==0 and'SML_NATIVE_BOUNDARY PASS'in s
(k/'bench_result.json').write_text(json.dumps(dict(status='PASS'if ok else'FAIL',returncode=r.returncode,seconds=time.time()-start,source='captured failing production RS native SML; no DPI',mapping='all209bits/samecycles; drop-score-valid mutant',log=s),indent=2))
print(s,flush=True);sys.exit(0 if ok else 1)
