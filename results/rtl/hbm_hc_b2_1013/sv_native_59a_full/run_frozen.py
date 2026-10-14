#!/usr/bin/env python3
import sys,pathlib,json,subprocess,os,hashlib
r=pathlib.Path(__file__).resolve().parent;m=json.load(open(r/'sourcegraph.json'))
for e in m['files']:
 if hashlib.sha256((r/'src'/e['path']).read_bytes()).hexdigest()!=e['sha256']:raise SystemExit('SOURCE MISMATCH '+e['path'])
top=sys.argv[1];o=r/top;o.mkdir(exist_ok=True)
v=os.environ.get('VERILATOR',str(pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'))
cmd=[v,'--lint-only' if '--lint-only' in sys.argv else '--binary','--timing','-O1','-Wno-fatal','-Wno-WIDTH','-Wno-UNOPTFLAT','-Wno-LATCH','-Wno-MULTIDRIVEN','-j','4','--top-module',top,'-Mdir',str(o/'obj'),'-DSV','-DWIDE','-DN=512','-DM=128','-DLV=7','-DLWB=18','-DLQ=8']+[str(r/'src'/e['path']) for e in m['files']]
cmd+=['-I'+str(r/'vec')]+(['-DSU_AUX'] if (r/'vec/su_aux.svh').exists() else [])
with (o/'build.log').open('w') as f:rc=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT)
if rc:print((o/'build.log').read_text()[-8000:]);sys.exit(rc)
if '--lint-only' in sys.argv:print('NATIVE_LINT PASS');sys.exit(0)
with (o/'run.log').open('w') as f:rc=subprocess.call([str(o/'obj'/('V'+top)),'+DIR='+str(r/'vec')],stdout=f,stderr=subprocess.STDOUT)
print((o/'run.log').read_text()[-8000:]);sys.exit(rc)
