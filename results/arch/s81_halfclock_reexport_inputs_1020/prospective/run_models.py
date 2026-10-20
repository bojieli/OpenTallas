from pathlib import Path
import hashlib,json,subprocess,shutil
B=Path.cwd();rows=json.loads((B/'cases.json').read_text());repair=json.loads((B/'repair/repair_receipt.json').read_text());rmap={r['master']:r for r in repair['cases']};image='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29';tool=B/'source658/tools/tt_views/view_export.py';assert hashlib.sha256(tool.read_bytes()).hexdigest()=='578418117d3547dc46dcf08c119533d1fc36db122a7a8c22f44cf6d4ae7b82b3'
root=B/'CURRENT_IMAGE_PG_REPAIRED_MODEL_ONLY';root.mkdir(exist_ok=True);runs=[]
originals=json.loads((B/'inputs_before.json').read_text())
def sameoriginals():
 for p,r in originals.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==r['sha256'],p
sameoriginals()
for row in rows:
 name=row['master'];r=rmap[name];assert r['nativePG_unbound_after']==0 and all(c['rejected'] for c in r['causals']);repaired=Path(r['repaired_odb'].replace('/stage/',str(B)+'/'));assert hashlib.sha256(repaired.read_bytes()).hexdigest()==r['repaired_sha256'];orfs=root/name/'orfs';oldbase=next(f['path'] for f in row['files'] if f['path'].endswith('6_final.odb'));relative=Path(oldbase).relative_to(row['orfs_dir']).parent;base=orfs/relative;base.mkdir(parents=True,exist_ok=True)
 for suffix in ['v','sdc','spef']:
  src=Path(oldbase).with_suffix('.'+suffix);shutil.copyfile(src,base/src.name);assert hashlib.sha256(src.read_bytes()).digest()==hashlib.sha256((base/src.name).read_bytes()).digest()
 shutil.copyfile(repaired,base/'6_final.odb')
 posts=[next(f['path'] for f in row['files'] if f['path'].endswith('/w18_extra.sdc')),next(f['path'] for f in row['files'] if f['path'].endswith('/app0_io_ref_routed.sdc'))]
 args=['python3',str(tool),'--orfs-dir',str(orfs),'--name',name,'--out',str(root/name/'views'),'--corners','ss,ff,tt','--forwarded-clock','ck:ck_o','--no-verdict','--expect-tt',str(row['old_verdict_expect']['tt']),'--expect-ff',str(row['old_verdict_expect']['ff']),'--require-check','--image',image,'--pin-only-tech']
 for f in posts:args+=['--post-sdc',f]
 with (root/name/'export_driver.log').open('w') as log:res=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT)
 runs.append(dict(master=name,scope='PROSPECTIVE_CURRENT_IMAGE_PG_REPAIRED_MODEL_ONLY_NOT_ORIGINAL_SIGNOFF',original_pg_status='FAIL',original_odb_sha256=r['original_sha256'],private_repaired_odb_sha256=r['repaired_sha256'],exporter_source='6586b0856 (1b69058ed/source35)',exporter_sha256=hashlib.sha256(tool.read_bytes()).hexdigest(),command=args,returncode=res.returncode));(root/'execution.json').write_text(json.dumps(runs,indent=2)+'\n');print('PRIVATE_MODEL_EXPORT',name,res.returncode,flush=True)
sameoriginals();(root/'original_inputs_still_unchanged.json').write_text(json.dumps(dict(unchanged=True,inputs=originals),indent=2)+'\n')
raise SystemExit(0 if all(r['returncode']==0 for r in runs) else 1)
