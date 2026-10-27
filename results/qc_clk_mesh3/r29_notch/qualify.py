import json,collections
from pathlib import Path
import klayout.db as K
p=Path(__file__).parent;a=json.loads((p/'source_boxes.json').read_text());m=json.loads((p/'model_boxes.json').read_text());n=json.loads((p/'native_boxes.json').read_text())
key=lambda r:(r['net'],r['layer'],tuple(r['rect']))
assert collections.Counter(map(key,m['shapes']))==collections.Counter(map(key,n['shapes'])),'native/model geometry differs'
old=collections.Counter(key(r) for r in a['shapes'] if r['net']!='VSS');new=collections.Counter(key(r) for r in n['shapes'] if r['net']!='VSS');assert old==new,'clock/other-net geometry changed'
def regs(rows):
 out={}
 for l in ('M8','M9'):
  for net in ('VSS','other'):
   rr=K.Region()
   for r in rows:
    if r['layer']==l and ((r['net']=='VSS')==(net=='VSS')):rr.insert(K.Box(*r['rect']))
   rr.merge();out[l,net]=rr
 return out
before=regs(a['shapes']);after=regs(n['shapes']);counts={}
for l in ('M8','M9'):
 counts[l]=dict(before_space=before[l,'VSS'].space_check(40).size(),before_notch=before[l,'VSS'].notch_check(40).size(),after_space=after[l,'VSS'].space_check(40).size(),after_notch=after[l,'VSS'].notch_check(40).size(),other_net_space=after[l,'VSS'].separation_check(after[l,'other'],40).size())
 assert counts[l]['after_space']==counts[l]['after_notch']==counts[l]['other_net_space']==0,counts[l]
assert counts['M9']['before_space']==24
r=dict(verdict='PASS',source_geometry='Actual R25 routed.odb rectangles from24 NC3 windows; coupon only, no full-die route claim',klayout_version=K.__version__,dbu_um=.001,minimum_same_net_gap_um=.04,deck=counts,native_model_exact=True,other_nets_unchanged=True,shape_count=len(n['shapes']),native_edits=24)
(p/'qualification.json').write_text(json.dumps(r,indent=1));print(json.dumps(r,indent=1))
