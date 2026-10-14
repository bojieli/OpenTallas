#!/usr/bin/env python3
import json,pathlib,hashlib,subprocess,os,sys
r=pathlib.Path(__file__).resolve().parent;m=json.load(open(r/'sourcegraph.json'));mut=int(os.environ.get('AMUT','0'));o=r/('m'+str(mut));o.mkdir(exist_ok=True)
for e in m['files']:
 if hashlib.sha256((r/'src'/e['path']).read_bytes()).hexdigest()!=e['sha256']:raise SystemExit('SOURCE MISMATCH '+e['path'])
v=os.environ.get('VERILATOR',str(pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'))
cmd=[v,'--cc','--exe','--build','-j','4','-O1','-CFLAGS','-O1','-MAKEFLAGS','OPT_SLOW=-O0','-Wno-fatal','-Wno-WIDTH','-Wno-UNUSED','-Wno-TIMESCALEMOD','-Wno-PINMISSING','--top-module','tb_hfd_attn_half_b','--prefix','Vtb','-Mdir',str(o/'obj'),'-GROLE=4','-GLDK=1','-GCG=1','-GMUT='+str(mut)]+['-G'+k+'='+str(v) for k,v in m['params'].items()]+[str(r/'src'/e['path']) for e in m['files']]
(o/'compile_command.json').write_text(json.dumps(cmd,indent=2)+'\n')
with (o/'build.log').open('w') as f:rc=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT)
if rc:print((o/'build.log').read_text()[-8000:]);sys.exit(rc)
with (o/'run.log').open('w') as f:rc=subprocess.call([str(o/'obj/Vtb')],stdout=f,stderr=subprocess.STDOUT)
log=(o/'run.log').read_text();print(log[-8000:]);sys.exit(0 if ('ATTNHALF' in log and ((not mut and rc==0 and 'mismatches=0' in log) or (mut and rc!=0))) else 1)
