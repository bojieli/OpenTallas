from pathlib import Path
import sys,json,gzip,hashlib,collections
sys.path.insert(0,'/home/ubuntu/wt/s81-vm-merge-0600/tools/hier_contract')
import child_lint as CL
B=Path(__file__).resolve().parent;OLD=B.parent/'geometry/final536_bc297977c/actual_pins';OUT=B/'actual-pins-538';OUT.mkdir(exist_ok=True)
old=json.loads((OLD/'leaves.json').read_text())['leaves'];by={x['path']:x for x in old};models=json.load(gzip.open(OLD/'models.json.gz','rt'));newmods={};rows=[]
def lefmod(p):
 m=CL.parse_lef(p.read_text());W,H=m['W'],m['H'];ports={}
 for n,v in m['pins'].items():
  if CL.is_pg(n,v):continue
  n=n.replace('\\','');rects=v['rects'];choices=[(CL.face_of(r,W,H),r)for r in rects];faces=sorted({f for f,r in choices if f});r=next((r for f,r in choices if f),rects[0]);ports[n]=dict(rects=rects,faces=faces,anchor_um=[(r[1]+r[3])/2,(r[2]+r[4])/2],anchor_layer=r[0],anchor_face=next((f for f,r in choices if f),None))
 return dict(physical_cell=m['name'],outline_um=[W,H],source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),pin_kind='lef',pin_source_original=str(p),pins=ports)
for leaf in json.loads((B/'graph-native/inventory.json').read_text())['leaves']:
 p=leaf['path'];orig=by.get(p)
 if orig is None and p.startswith('dut.u_xsw.h'):
  orig=by['dut.u_xsel.'+p.rsplit('.',1)[1]]
 assert orig is not None,p
 assert orig['master']==leaf['master']and orig['parameters']==leaf['parameters'],p
 row={**orig,**leaf};row['scope']='Actual source-current geometry only; individual native qualification status remains explicit. No placement or timing inherited.'
 if p in ['dut.u_xio.u_ret','dut.u_wfc.u_ret']:
  fn='xio_return_r3.lef'if 'u_xio' in p else'wfc_return_r5_NATIVE_FAIL.lef';key='pin-inputs/'+fn;model=lefmod(B/key);row.update(kit='dsfd_vm_xio_return_native_1016_r3'if 'u_xio'in p else'dsfd_vm_wfc_return_hop1_native_1016_r5',pin_source=key,pin_kind='lef',pin_source_original=str(B/key),sha256=model['source_sha256']);row['native_status']='ROUTED_NATIVE_PASS'if'u_xio'in p else'ROUTED_CLOSED_NATIVE_FAIL_launch238.23_NOT_ADOPTABLE'
 else:
  key=row['pin_source'];model=models[key]
  row['native_status']='EXISTING_SNAPSHOT_STATUS_MUST_BE_CHECKED_SEPARATELY'
 row.update(outline_um=model['outline_um'],physical_cell=model['physical_cell']);newmods[key]=model;absent=[]
 for port,v in leaf['ports'].items():
  for bit in range(v['bits']):
   n=port+'['+str(bit)+']'if v['bits']>1 else port
   if n not in model['pins']and not(v['bits']==1 and port+'[0]'in model['pins']):absent.append(n)
 row['missing_bits']=absent;rows.append(row)
(OUT/'leaves.json').write_text(json.dumps(dict(leaves=rows),indent=1)+'\n')
with gzip.open(OUT/'models.json.gz','wt')as f:json.dump(newmods,f,separators=(',',':'))
s=dict(scope='Exact actual LEF/gate boundary pin registry; NOT native qualification, placement or die timing.',source_commit=json.loads((B/'source_manifest.json').read_text())['git_head'],source_manifest_sha256=hashlib.sha256((B/'source_manifest.json').read_bytes()).hexdigest(),xml_sha256=hashlib.sha256((B/'parent.xml').read_bytes()).hexdigest(),leaf_instances=len(rows),unique_pin_models=len(newmods),missing_leaves=[dict(path=r['path'],bits=r['missing_bits'])for r in rows if r['missing_bits']],signal_pin_shapes=sum(len(p['rects'])for m in newmods.values()for p in m['pins'].values()),native_blockers=['WFC return r5 is actual CLOSED route but strict native FAIL launch238.23ps; geometry evidence only. r6 strict CTS FAIL221.409, structural256slice pending and not in this production source.', 'Current x34_sw2 has live2bit fault OR without hardened home.','Old repeated model native/PG/source receipts remain separately required; registry does not assert those.'])
(OUT/'summary.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(s,indent=1));assert not s['missing_leaves']
