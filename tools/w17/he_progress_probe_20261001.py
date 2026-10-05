#!/usr/bin/env python3
"""Host-only single-rank diagnostic using preserved generated RTL archive."""
import pathlib,re,subprocess,json,hashlib
out=pathlib.Path('/home/ubuntu/w17-he-progress-20261001-r1');out.mkdir(exist_ok=False)
build=pathlib.Path('/home/ubuntu/w17work/dierun2/die0')
prefix='ot_v41_rt_die__DOT__dut__DOT__u_tile__DOT__u_core__DOT__g_he_x__DOT__u_he__DOT__'
header=(build/'Vdie0___024root.h').read_text()
names=re.findall(r'\b('+prefix+r'\w+)\s*;',header)
selected=[n for n in names if n[len(prefix):] in ['st','lc','lp','o_valid','o_last','u_hcp__DOT__active','u_hcp__DOT__o','u_hcp__DOT__r','u_hcp__DOT__st','u_hcp__DOT__rq_wp','u_hcp__DOT__rq_rp']]
s=(pathlib.Path('/home/ubuntu/w17work/dbg/t1.cpp')).read_text().replace('#include "Vdie0.h"','#include "Vdie0.h"\n#include "Vdie0___024root.h"')
start=s.index(' for(int i=0;i<3000;i++)')
end=s.index(' printf("end pc',start)
prints=''.join('printf(" '+n[len(prefix):]+'=%u",unsigned(d.rootp->'+n+'));' for n in selected)
s=s[:start]+' for(int i=0;i<12000;i++){tick();if(i%200==0||i==5899||i==10499){printf("HE cycle=%d pc=%u",i+1,d.dbg_pc);'+prints+'printf("\\n");fflush(stdout);}if(d.fault||d.dbg_pc>9)break;}\n'+s[end:]
s=s[:s.index('  svSetScope(sc);')]+'}\n'
(out/'probe.cpp').write_text(s)
v=pathlib.Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator/include')
cmd=['g++','-std=c++20','-O1','-pthread','-I'+str(build),'-I'+str(v),'-I'+str(v/'vltstd'),str(out/'probe.cpp'),str(build/'Vdie0__ALL.a'),str(v/'verilated.cpp'),str(v/'verilated_dpi.cpp'),str(v/'verilated_threads.cpp'),'-o',str(out/'probe')]
record=dict(scope='HE single-rank internal diagnostic; no field/attention service, no full-token exactness',source_commit='d2e6290288a15f498461f0309225884aefcdac7f',selected_signals=selected,pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [build/'Vdie0__ALL.a',build/'Vdie0___024root.h',out/'probe.cpp']},compile=cmd)
(out/'launch.json').write_text(json.dumps(record,indent=2)+'\n')
with open(out/'compile.log','wb') as log:r=subprocess.run(['timeout','180s',*cmd],stdout=log,stderr=subprocess.STDOUT)
record['compile_returncode']=r.returncode
if r.returncode==0:
 with open(out/'trace.log','wb') as log:r=subprocess.run(['timeout','--kill-after=15s','1800s',str(out/'probe')],cwd=out,stdout=log,stderr=subprocess.STDOUT)
 record['run_returncode']=r.returncode
 record['trace_tail']=(out/'trace.log').read_text().splitlines()[-12:]
(out/'analysis.json').write_text(json.dumps(record,indent=2)+'\n')
with open('/tmp/claude-1000/queue/W17.manifest','a') as f:f.write('\n# HE internal probe terminal capture '+str(out/'analysis.json')+'; single-rank diagnostic only.\n')
