import odb,json,sys,hashlib
from pathlib import Path
src,summary,out=map(Path,sys.argv[1:4]);db=odb.dbDatabase.create();odb.read_db(db,str(src));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();d=json.loads(summary.read_text())
def pin(k):
 i,p=k.rsplit('/',1);v=b.findInst(i).findITerm(p);z=v.getBBox();return {'pin':k,'bbox_um':[z.xMin()/u,z.yMin()/u,z.xMax()/u,z.yMax()/u],'master':v.getInst().getMaster().getName(),'net':v.getNet().getName() if v.getNet() else None,'inst_origin_um':[v.getInst().getLocation()[0]/u,v.getInst().getLocation()[1]/u]}
rows=[]
for r in d['reach_over405']:
 ends=r['endpoints'];rows.append({'driver':pin(r['driver']),'effective_terminals':r['terminals'],'bbox_L1_upper_um':r['max_L1_pin_bbox_upper_um'],'sinks':[pin(s) for s in ends],'classification':'eq pin register -> hard TE rt input; no registered parent intermediate' if '.eq' in r['driver'] else 'reset landing/copies -> hard child reset inputs; transparent buffers do not add a cycle'})
out.write_text(json.dumps({'odb_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'rows':rows},indent=2));print('REACH_COORDS',len(rows))
