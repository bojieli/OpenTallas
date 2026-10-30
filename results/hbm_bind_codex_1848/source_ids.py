"""Match plan lane identity straps to exact selected source literal terminals; no RTL change."""
import json,os,shutil,hashlib
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-hbm-bind-1848')
SRC=Path('/srv/opentallas-scratch2/claude/die-hbm-24/plan/d23c')
OUT=R/'d23c_ids'
M=json.load(open('/srv/opentallas-scratch2/claude/hbm-bind-13-1029/g3/out/asbuilt.json'))['modules']
C=json.load(open('/srv/opentallas-scratch2/claude/hbm-bind-13-1029/g3/compose.json'))
MAP=json.load(open('/srv/opentallas-scratch2/claude/hbm-bind-7-1029/c1/map.json'))['parts']
p=json.load(open(SRC/'die_plan.json'));parts={x['name']:x for x in p['partitions']}
def cell(path):
 m=M['hbm_current_native_top'];left=path
 while True:
  names=[n for n in m['cells'] if left==n or left.startswith(n+'.')]
  assert names,path
  n=max(names,key=len);c=m['cells'][n]
  if left==n:return c
  left=left[len(n)+1:];m=M[c['type']]
values={};seen=[]
for c in C['cores']:
 if c['inst'] not in MAP or 'lane_lane_id' not in c.get('ports',{}):continue
 part,inst=MAP[c['inst']];tn=parts[part]['type'];t=p['partition_types'][tn]
 ds=[d for d in t.get('contents',[])+t.get('hard_cores',[]) if d.get('parent_id_leaf',d.get('inst'))==inst and 'lane_lane_id' in d.get('parent_id_straps',{})]
 if not ds:continue
 bits=[];refs=[]
 for group in c['ports']['lane_lane_id']['bits']:
  raw=[cell(a['member'])['connections'][a['port']][a['bit']] for a in group]
  assert raw and set(raw)<=set('01') and len(set(raw))==1,(c['inst'],raw)
  bits.append(raw[0]);refs.append(group)
 value=sum(int(v)<<i for i,v in enumerate(bits));key=(tn,inst)
 assert key not in values or values[key]==value
 values[key]=value
 for d in ds:
  v=d['parent_id_straps']['lane_lane_id'];assert v['width']==len(bits),(key,v,len(bits))
  if v['value']!=value:
   seen.append(dict(type=tn,inst=inst,source=c['inst'],before=v['value'],after=value,width=len(bits),literal_lsb=''.join(bits),terminals=refs))
   v['value']=value
assert seen
assert not OUT.exists()
shutil.copytree(SRC,OUT,copy_function=os.link)
(OUT/'die_plan.json').unlink();(OUT/'die_plan.json').write_text(json.dumps(p,indent=1))
receipt=dict(source_plan_sha256=hashlib.sha256((SRC/'die_plan.json').read_bytes()).hexdigest(),plan_sha256=hashlib.sha256((OUT/'die_plan.json').read_bytes()).hexdigest(),changed_descriptors=len(seen),changed_cores=len({(x['type'],x['inst']) for x in seen}),changes=seen,cycles_added=0,rtl_changed=False)
(R/'source_ids_report.json').write_text(json.dumps(receipt,indent=1))
print(json.dumps({k:v for k,v in receipt.items() if k!='changes'}))
