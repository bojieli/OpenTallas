import odb,json,sys
from pathlib import Path
db=odb.dbDatabase.create();odb.read_db(db,sys.argv[1] if len(sys.argv)>1 else '/input/6_final.odb');b=db.getChip().getBlock();src=b.findBTerm('clk_t8');sn=src.getNet() if src else None
out={'scope':'Actual final ODB read-only two forwarded-clock buffers; no source/proof/route/STA change','source_bterm':'clk_t8','source_net':None if not sn else sn.getName(),'buffers':[]}
def net(n):return None if not n else dict(name=n.getName(),sigtype=str(n.getSigType()),special=n.isSpecial(),bterms=sorted(x.getName() for x in n.getBTerms()),iterm_count=len(n.getITerms()))
for n in ('cland_fwd_fclk_out_bu_o','cland_fwd_fclk_out_h_rx_ft_o'):
 i=b.findInst(n)
 if i is None:
  out['buffers'].append(dict(instance=n,status='NOT_PRESENT_IN_CHECKPOINT'));continue
 pins={p:net(i.findITerm(p).getNet()) for p in ('A','Y')};a=i.findITerm('A').getNet();y=i.findITerm('Y').getNet()
 out['buffers'].append(dict(instance=n,master=i.getMaster().getName(),location=list(i.getLocation()),orient=str(i.getOrient()),status=str(i.getPlacementStatus()),pins=pins,A_same_net_as_clk_t8=(a is not None and sn is not None and a.getId()==sn.getId()),output_bterm_on_Y=(y is not None and n.replace('cland_fwd_','') in [z.getName() for z in y.getBTerms()])))
Path('/work/'+(Path(sys.argv[1]).stem if len(sys.argv)>1 else 'audit')+'.json').write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(out))
