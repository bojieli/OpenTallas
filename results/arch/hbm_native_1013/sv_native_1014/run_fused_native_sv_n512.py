#!/usr/bin/env python3
import json,pathlib,os,hashlib,subprocess,sys
r=pathlib.Path(__file__).resolve().parent;m=json.load(open(r/'sourcegraph.json'));mut=int(os.environ.get('FMUT','0'));o=r/('m'+str(mut));o.mkdir(exist_ok=True)
for e in m['files']:
 if hashlib.sha256((r/'src'/e['path']).read_bytes()).hexdigest()!=e['sha256']:raise SystemExit('SOURCE MISMATCH '+e['path'])
for p,h in m['vector_sha256'].items():
 if hashlib.sha256((r/'vec'/p).read_bytes()).hexdigest()!=h:raise SystemExit('VECTOR MISMATCH '+p)
v=os.environ.get('VERILATOR',str(pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'))
cmd=[v,'--binary','--timing','-O1','-Wno-fatal','-Wno-WIDTH','-Wno-UNOPTFLAT','-Wno-LATCH','-Wno-MULTIDRIVEN','-j','4','--top-module','tb_hgi_fused_native_sv','-Mdir',str(o/'obj'),'-DWIDE','-DUN=512','-DUM=128','-DVLQ=8','-I'+str(r/'vec')]+(['-DMUT_SEG'] if mut else [])+[str(r/'src'/e['path']) for e in m['files']]
(o/'compile_command.json').write_text(json.dumps(cmd,indent=2)+'\n')
with (o/'build.log').open('w') as f:rc=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT)
if rc:print((o/'build.log').read_text()[-8000:]);sys.exit(rc)
with (o/'run.log').open('w') as f:rc=subprocess.call([str(o/'obj/Vtb_hgi_fused_native_sv'),'+DIR='+str(r/'vec')],stdout=f,stderr=subprocess.STDOUT)
log=(o/'run.log').read_text();print(log[-8000:]);expect='HGI_FUSED_NATIVE_SV '+('FAIL' if mut else 'PASS');sys.exit(rc or (0 if expect in log else 1))
