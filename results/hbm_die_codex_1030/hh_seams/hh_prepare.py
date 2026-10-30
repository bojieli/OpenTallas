import json,shutil,sys
from pathlib import Path
base=Path(sys.argv[1]);out=Path(sys.argv[2]);assert not out.exists();shutil.copytree(base,out,symlinks=False)
r=json.load(open(out/'die_plan.json'));removed=[]
for p in r['ports']:
 if p['id'] in ('L4_0','L4_1','L4m_0','L4m_1'):
  assert p['width']==2816;p['width']=2784
for tn,t in r['partition_types'].items():
 for b in t.get('buses',[]):
  if b['name'] in ['L4_o','L4_i']:
   assert b['width']==2816;b['width']=2784;removed.append([tn,b['name'],32])
 for s in t.get('ft_slots',[]):
  if s['name'] in ['L4x1','L4mx1']:
   assert s['width']==2816;s['width']=2784
   if 'bit_sites_um' in s:s['bit_sites_um']=[row[:2784]+[row[-1]] for row in s['bit_sites_um']]
r['note']='CODEX SouthernVMS coherent bundle: retain NorthernVMS/prHCOL L4 width2784; 32SouthernVMSbits move to complete newdetour word, oldL9622bits coherently padded | '+r.get('note','')
json.dump(r,open(out/'die_plan.json','w'),indent=1)
json.dump({'old_L4_width':2816,'new_L4_width':2784,'Southern_bits_moved_per_direction':32,'old_L96_width_retained':22,'removed_bits':removed,'status':'UNADOPTED: actualstrictbindR8required'},open(out/'coherent_input_report.json','w'),indent=1)
