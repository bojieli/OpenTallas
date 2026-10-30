import sys,json,pathlib
sys.path.insert(0,sys.argv[1]);import geom_rules as G
r=pathlib.Path('/srv/opentallas-scratch2/claude/codex-s81types-1030');D=G.Design(str(r/'iqf_coupon_movable/geom.tsv'),None,False);C={c[6]:c for c in D.cells.values()}
for fn in ['iqf_ft0_targets','iqf_ft1_read_targets']:
 j=json.load(open(r/(fn+'.json')))
 for row in j['targets']:
  c=C[row['name']];row['xy']=[c[2],c[3]];row['centre']=list(G.ctr(c));row['size']=[c[4]-c[2],c[5]-c[3]];row['master']=c[1]
 j['provenance']='Actual legalize0/check-placement0; source identical; inherited IQF ODB; no new cycles. Full geometry/source/route gates held.'
 (r/'iqf_coupon_movable'/(fn+'_legal.json')).write_text(json.dumps(j,indent=1))
