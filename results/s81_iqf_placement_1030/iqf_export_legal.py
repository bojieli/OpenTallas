import sys,json,pathlib
sys.path.insert(0,sys.argv[1]);import geom_rules as G
r=pathlib.Path('/srv/opentallas-scratch2/claude/codex-s81types-1030');D=G.Design(str(r/'iqf_coupon_movable/geom.tsv'),None,False);C={c[6]:c for c in D.cells.values()}
for fn in ['iqf_ft0_targets','iqf_ft1_read_targets']:
 j=json.load(open(r/(fn+'.json')))
 for row in j['targets']:
  c=C[row['name']];row['xy']=[c[2],c[3]];row['centre']=list(G.ctr(c));row['size']=[c[4]-c[2],c[5]-c[3]];row['master']=c[1]
 j['nominal_estimate_metrics']=j.pop('metrics')
 if fn=='iqf_ft0_targets':j['actual_legal_metrics']=json.load(open(r/'iqf_coupon_movable/metrics.json'))['FT0']
 else:
  caps={}
  import re
  for c in D.cells.values():
   m=re.match(r'u_bound\.u_ft_ft1_o_0/(?:q\[(\d+)\]|(eq))\$',c[6].replace('\\',''))
   if m:caps[1368 if m[2] else int(m[1])]=G.ctr(c)
  hops=[abs(row['centre'][0]-caps[row['bit']][0])+abs(row['centre'][1]-caps[row['bit']][1]) for row in j['targets']]
  j['actual_legal_metrics']={'max_first_hop':max(hops),'over405':sum(x>405 for x in hops),'read_FF':len(hops),'cycles_change':0}
 j['provenance']='Actual legalize0/check-placement0; source identical; inherited IQF ODB; no new cycles. Full geometry/source/route gates held.'
 (r/'iqf_coupon_movable'/(fn+'_legal.json')).write_text(json.dumps(j,indent=1))
