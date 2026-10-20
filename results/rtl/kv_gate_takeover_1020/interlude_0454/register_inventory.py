import odb,json,sys,hashlib,collections,gzip
from pathlib import Path
odbpath,gate,out=map(Path,sys.argv[1:]);db=odb.dbDatabase.create();odb.read_db(db,str(odbpath));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
roles=json.loads(Path('/audit/roles.json').read_text())['master_roles']
base=odbpath.parent;classes={}
for line in (base/'ot_hroot_central_members.tsv').read_text().splitlines()[1:]:
 name,master,status,cls=line.split('\t');classes[name]={'source_master':master,'source_status':status,'class':cls}
rows=[];counts=collections.Counter();boxes={};class_missing=[];seqcl=collections.Counter();existing={i.getName() for i in b.getInsts()}
for name,meta in classes.items():
 if name not in existing:class_missing.append(meta|{'instance':name})
for i in b.getInsts():
 name=i.getName();mn=i.getMaster().getName();meta=classes.get(name,{'class':'post_hook_birth_unclassified'});cls=meta['class'];r=i.getBBox();box=[r.xMin()/u,r.yMin()/u,r.xMax()/u,r.yMax()/u];counts[cls]+=1
 if cls not in boxes:boxes[cls]=box[:]
 else:boxes[cls]=[min(boxes[cls][0],box[0]),min(boxes[cls][1],box[1]),max(boxes[cls][2],box[2]),max(boxes[cls][3],box[3])]
 if not roles.get(mn,{}).get('sequential'):continue
 seqcl[cls]+=1;pins=[]
 for it in i.getITerms():
  mt=it.getMTerm();pn=mt.getName();role=roles[mn]['pins'].get(pn);net=it.getNet();pins.append({'pin':pn,'net':net.getName() if net else None,'role':role,'sigtype':str(mt.getSigType()),'iotype':str(mt.getIoType())})
 rows.append({'instance':name,'master':mn,'bbox_um':box,'placement_status':str(i.getPlacementStatus()),'hook_membership':meta,'actual_pins':pins})
files={}
for p in [gate/'src/physical/qwen_kv_hroot_safe32_1020/central_fence_s32v4.tcl',gate/'src/physical/qwen_kv_hroot_safe32_1020/central_fence_release.tcl',next((gate/'src/physical/ref_tile').glob('qkd_kvs_hroot_s32v4*/pre_gpl.tcl')),base/'ot_hroot_central_members.tsv',base/'ot_out_flop_at_pins.txt',base/'ot_inhold_firm.txt']:
 files[str(p)]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
out.mkdir(parents=True,exist_ok=True)
with gzip.open(out/'sequential_inventory.json.gz','wt') as f:json.dump(rows,f)
s={'scope':'Actual CTS sequential register inventory and transformed instance bboxes joined to consumed pre-GPL hook membership. Membership is consumed original Tcl classification, not independently semantic classification. Post-hook births explicitly unclassified; no extrapolated final PG/405/clock proof.','odb_sha256':hashlib.sha256(odbpath.read_bytes()).hexdigest(),'sequential_count':len(rows),'sequential_by_hook_class':dict(seqcl),'all_cells_by_hook_class':dict(counts),'all_cell_bbox_by_hook_class_um':boxes,'hook_members_missing_at_cts':class_missing,'consumed_files':files}
(out/'summary.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps({k:v for k,v in s.items() if k not in ['consumed_files','hook_members_missing_at_cts']}))
