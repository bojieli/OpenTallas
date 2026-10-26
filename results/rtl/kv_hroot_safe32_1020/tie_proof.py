import odb,json
from pathlib import Path
p=Path('/work/native_orfs/results/asap7/qkd_kvs_hroot_safe32/base')
def load(f):
 d=odb.dbDatabase.create();odb.read_db(d,str(p/f));return d,d.getChip().getBlock()
da,a=load('1_synth_raw.odb');db,b=load('1_synth.odb')
changes=[]
for ia in a.getInsts():
 ib=b.findInst(ia.getName());assert ib and ia.getMaster().getName()==ib.getMaster().getName()
 for ta in ia.getITerms():
  tb=ib.findITerm(ta.getMTerm().getName());na=ta.getNet();nb=tb.getNet()
  an=na.getName() if na else None;bn=nb.getName() if nb else None
  if an==bn:continue
  assert ta.getMTerm().getName()=='SETN'
  da=[t for t in na.getITerms() if t.getIoType()=='OUTPUT'];dd=[t for t in nb.getITerms() if t.getIoType()=='OUTPUT']
  assert len(da)==len(dd)==1
  ma=da[0].getInst().getMaster().getName();mb=dd[0].getInst().getMaster().getName()
  assert ma==mb and ma.startswith('TIEHI')
  changes.append(dict(pin=ia.getName()+'/SETN',before=an,after=bn,constant_master=ma))
for ta in a.getBTerms():
 tb=b.findBTerm(ta.getName());assert tb and ta.getNet().getName()==tb.getNet().getName()
added=[i for i in b.getInsts() if not a.findInst(i.getName())]
assert all(i.getMaster().getName().startswith('TIEHI') for i in added)
r=dict(pass_proof=True,original_cells=len(a.getInsts()),repaired_cells=len(b.getInsts()),added_tie_cells=len(added),rewired_unused_SETN=len(changes),functional_data_clock_reset_connectivity_identical=True,changes=changes)
Path('/work/results/rtl/kv_hroot_safe32_1020/tie_proof.json').write_text(json.dumps(r,indent=2)+'\n');print({k:v for k,v in r.items() if k!='changes'})
