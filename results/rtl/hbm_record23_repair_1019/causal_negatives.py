from pathlib import Path
import sys,json,subprocess,re
D=Path('/srv/opentallas-scratch/claude/hbm-native-record23-clock-1019');C=Path('/srv/opentallas-scratch/claude/hbm-record23-consumer-trace-1019');O=Path.cwd()
sys.path[:0]=[str(D/'tools'),str(D/'tools/hbm_static'),str(D)]
from hbm_layer_vehicle.layer_images import column_image
from su_arith_generate import FIELDS
from native_su_calendar import compile_calendar
off={};n=0
for name,width in reversed(FIELDS):off[name]=n;n+=width
read=lambda p:[int(x,16)for x in p.read_text().split()]
good=read(O/'drain1/quarter.mem');old=read(C/'original_quarter.mem') if (C/'original_quarter.mem').exists()else read(D/'record23_profile/native18/quarter.mem')
held=read(C/'hold_only/quarter.mem');mask=((1<<78)-1)<<128
noid=[x&~mask for x in held]+[held[-1]&~mask]
for i,x in enumerate(held):noid[i+1]|=x&mask
# Keep only old per-edge control enables and backend words; transplant only
# the known legal address terms/base, not the fixed live backend controls.
nometa=[]
for i,x in enumerate(good):
 oc=old[i]>>680 if i<len(old)else 0;gc=x>>680
 for field in ['ld_c','vb']:
  m=((1<<dict(FIELDS)[field])-1)<<off[field];oc=(oc&~m)|(gc&m)
 nometa.append((x&((1<<680)-1))|(oc<<680))
early=good.copy()
for field,src,dst in [('ld',14,6),('emit',22,14)]:
 m=1<<(off[field]+680)
 assert early[src]&m,(field,src)
 early[src]&=~m;early[dst]|=m
cases={'absent_reader_identity':noid,'missing_control_lifetime':nometa,'old_drain_gap':read(O/'drain0/quarter.mem'),'old_fill_deadline':early}
report={}
for name,words in cases.items():
 dest=O/name;column_image(words,dest)
 cw=[(x&~(((1<<180)-1)<<500))&~(((1<<234)-1)<<206)for x in words]
 c,m=compile_calendar(cw,first_serial=2675,bridge_serial=2675,bridge_stream=3567,host_launch=3500,rows=160,request_lane_edges_by_bank=[4,5,0,0,0,0,0,0],write_lane_edges_by_bank=[3,3,0,0,0,0,0,0])
 (O/'calendar.mem').write_text(''.join(f'{x:064x}\n'for x in c));(dest/'calendar_model.json').write_text(json.dumps(m,indent=2))
 with(dest/'replay.log').open('w')as f:
  r=subprocess.run([str(C/'observe'),f'+CFG={dest}/cols/config.mem',f'+GOLD={dest}/quarter.mem',f'+N={len(words)}',f'+W={len((dest/"cols/config.mem").read_text().split())}'],stdout=f,stderr=subprocess.STDOUT)
 text=(dest/'replay.log').read_text();assert r.returncode!=0,(name,'unexpected PASS')
 assert 'ARITHMETIC FAIL' in text,name
 report[name]={'exit':r.returncode,'fail_regex':'ARITHMETIC FAIL','words':len(words)}
 (dest/'exit.txt').write_text(str(r.returncode));print('CAUSAL',name,r.returncode,flush=True)
(O/'causal_summary.json').write_text(json.dumps(report,indent=2))
