#!/usr/bin/env python3
"""Bounded required native pair path proof, with actual production DL4 relays.

Fleet-only. Uses a passing kv_vp_1021 source inventory, then adds only the
current XRT/RSTOPT and slice relay source. One local, V, horizontal pair plus
one V payload-corruption control; no full-die or physical timing claim.
"""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--baseline', required=True, type=Path)
p.add_argument('--out', required=True, type=Path)
p.add_argument('--resume-objects', type=Path)
a=p.parse_args()
ROOT=Path(__file__).resolve().parents[3]
a.out.mkdir(parents=True,exist_ok=False)
base=json.loads((a.baseline/'result.json').read_text());assert base['status']=='PASS'
src=[s for s in base['source_sha256'] if not Path(s).name.startswith('tb_')]
src+=['rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv',
      'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstopt.sv',
      'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv',
      'tools/s81_dv/rdpair_leaf4_1021/tb_rd_pair_leaf4.sv']
src=list(dict.fromkeys(src))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
pins={s:sha(ROOT/s) for s in src}
for s,d in base['source_sha256'].items():
 if s in pins:assert pins[s]==d,s
obj=a.resume_objects or a.out/'obj'
if a.resume_objects:
 assert json.loads((obj.parent/'result.json').read_text())['source_sha256']==pins
 assert (obj/'Vtb_rd_pair_leaf4.mk').is_file()
 cmd=['make','-C',str(obj),'-f','Vtb_rd_pair_leaf4.mk','-j','2']
else:
 v=str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
 cmd=[v,'--binary','--timing','-O1','-fno-dfg','--unroll-count','4',
      '-Wno-fatal','-Wno-WIDTH','--top-module','tb_rd_pair_leaf4','-Mdir',str(obj),
      '-j','2',*[str(ROOT/s) for s in src],'-CFLAGS','-O1']
result=dict(status='RUNNING',full_token=False,full_layer=False,source_sha256=pins,argv=cmd,
 scope='One-pair native local, typed-V and direct adjacent horizontal; current XRT/RSTOPT/VP + production DL4',
 open=['actual XS/CAP producer','29-leg programme calendar','interrank exchange','landed physical links','full layer/token'])
def save():(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
save()
b=subprocess.run(cmd,capture_output=True,text=True);(a.out/'build.log').write_text(b.stdout+b.stderr)
if b.returncode:
 result.update(status='FAIL',reason='build',exit_code=b.returncode);save();sys.exit(1)
guard_dir=Path.home()/'.local/opentallas-tools/verilator-5.050/share/ot_nba_guard'
sys.path.insert(0,str(guard_dir));import verilator_nba_guard as G
guard=G.scan(str(obj));(a.out/'nba_guard.json').write_text(json.dumps(guard,indent=2)+'\n')
result['nba_guard_sha256']=sha(guard_dir/'verilator_nba_guard.py')
if guard['findings']:
 result.update(status='FAIL',reason='NBA guard');save();sys.exit(86)
checks={}
for name,mode,mut in [('local',0,0),('typed_v',1,0),('horizontal',2,0),('negative_payload',1,1)]:
 r=subprocess.run([str(obj/'Vtb_rd_pair_leaf4'),f'+MODE={mode}',f'+MUT={mut}'],cwd=a.out,capture_output=True,text=True)
 log=r.stdout+r.stderr;(a.out/(name+'.log')).write_text(log)
 good=(r.returncode!=0 and 'RDPAIR_LEAF4 FAIL' in log) if mut else (r.returncode==0 and 'RDPAIR_LEAF4 PASS' in log)
 checks[name]=dict(passed=good,exit_code=r.returncode)
assert pins=={s:sha(ROOT/s) for s in src}
ok=all(x['passed'] for x in checks.values());result.update(status='PASS' if ok else 'FAIL',checks=checks);save()
for name in checks:print((a.out/(name+'.log')).read_text(),flush=True)
sys.exit(int(not ok))
