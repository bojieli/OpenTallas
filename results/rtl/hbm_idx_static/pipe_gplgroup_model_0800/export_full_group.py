import odb,json,gzip,hashlib
from pathlib import Path
out=Path('/audit/full_membership');out.mkdir(exist_ok=True)
def capture(name):
 p=Path('/audit')/name;db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();graph=[];rows=[];unbound=[]
 for i in b.getInsts():
  m=i.getMaster();graph.append(['I',i.getName(),m.getName(),bool(i.isDoNotTouch())])
  for pin in i.getITerms():
   n=pin.getNet();mt=pin.getMTerm();graph.append(['P',i.getName(),mt.getName(),str(mt.getIoType()),str(mt.getSigType()),n.getName() if n else None])
   if str(mt.getSigType()) in ['POWER','GROUND'] and not n:unbound.append(i.getName()+'/'+mt.getName())
  if m.isBlock() or all(str(mt.getSigType()) in ['POWER','GROUND'] for mt in m.getMTerms()):continue
  g=i.getGroup();r=i.getRegion();bb=i.getBBox();box=[bb.xMin()/u,bb.yMin()/u,bb.xMax()/u,bb.yMax()/u]
  rows.append({'instance':i.getName(),'master':m.getName(),'group':g.getName() if g else None,'group_region':g.getRegion().getName() if g and g.getRegion() else None,'region':r.getName() if r else None,'bbox_um':box,'dnt':bool(i.isDoNotTouch()),'status':str(i.getPlacementStatus()),'inside_band':box[0]>=2.16-1/u and box[1]>=2.16-1/u and box[2]<=343.44+1/u and box[3]<=45.36+1/u})
 for pin in b.getBTerms():graph.append(['B',pin.getName(),str(pin.getIoType()),str(pin.getSigType()),pin.getNet().getName() if pin.getNet() else None])
 for n in b.getNets():graph.append(['N',n.getName(),str(n.getSigType()),bool(n.isDoNotTouch())])
 graph.sort(key=lambda row:json.dumps(row,separators=(',',':')));rows.sort(key=lambda row:row['instance']);data=json.dumps(graph,separators=(',',':')).encode();gp=out/(name+'.graph.json.gz');gp.write_bytes(gzip.compress(data,mtime=0));rp=out/(name+'.membership.jsonl.gz');rp.write_bytes(gzip.compress(('\n'.join(json.dumps(r,separators=(',',':')) for r in rows)+'\n').encode(),mtime=0));bad=[r['instance'] for r in rows if r['group']!='codex_idx_lower_group' or r['region']!='codex_idx_lower_band' or r['group_region']!='codex_idx_lower_band'];return {'odb_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'complete_graph_sha256':hashlib.sha256(data).hexdigest(),'graph_records':len(graph),'functional_rows':len(rows),'outside_band':sum(not r['inside_band'] for r in rows),'bad_group_region':bad,'pg_unbound':unbound,'full_graph_gzip_sha256':hashlib.sha256(gp.read_bytes()).hexdigest(),'full_membership_gzip_sha256':hashlib.sha256(rp.read_bytes()).hexdigest()}
a=capture('model_group_input.odb');b=capture('model_group_gpl.odb');assert a['complete_graph_sha256']==b['complete_graph_sha256'];assert b['functional_rows']==46554 and not b['outside_band'] and not b['bad_group_region'] and not b['pg_unbound'];result={'schema':'opentallas.complete_native_gpl_group_archive.v1','before_gpl':a,'after_gpl':b,'all_pin_net_pg_dnt_records_identical':True,'scope':'PRIVATE_MODEL_ONLY'};(out/'summary.json').write_text(json.dumps(result,indent=2));print('FULL_NATIVE_GROUP_ARCHIVE_PASS',b['functional_rows'],b['outside_band'],len(b['pg_unbound']),b['graph_records'])
