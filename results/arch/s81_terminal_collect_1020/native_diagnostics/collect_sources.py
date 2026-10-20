from pathlib import Path
import json,hashlib,gzip,shutil
out=Path('receipts');out.mkdir(exist_ok=True)
for r in json.loads(Path('inputs.json').read_text()):
 label=r['label'];root=Path('/srv/opentallas-scratch/claude/ref_gate')/r['case'];binding=r['binding'];expected={f['path']:f for f in binding['files']};records=[]
 for name in binding['consumed']['paths']:
  rec=expected.get(name);p=root/'src'/name
  if rec and rec.get('kind')=='file':
   actual=hashlib.sha256(p.read_bytes()).hexdigest()if p.is_file()else None
   records.append(dict(path=name,expected=rec.get('sha256'),actual=actual,match=actual==rec.get('sha256')))
 status=all(x['match']for x in records)and bool(records)
 report=dict(status='PASS'if status else'FAIL',scope='historical consumed source snapshot, not current-main gate admissibility',start_commit=binding['start_commit'],archive_sha256=binding['archive_sha256'],remote_archive_verified=binding.get('remote_archive_verified'),runtime_tool_provenance=binding.get('runtime_tool_provenance'),files=records)
 d=out/label;d.mkdir(exist_ok=True);(d/'consumed_source_verification.json').write_text(json.dumps(report,indent=2))
 for name in ['cts.log','execution.log','pin_geometry.json','textbook.json','layout_floorplan.log']:
  p=root/name
  if p.exists():(d/(name+'.gz')).write_bytes(gzip.compress(p.read_bytes(),mtime=0))
 p=root/'routes/gate/work/orfs/native_census.json'
 if p.exists():(d/'native_census.json.gz').write_bytes(gzip.compress(p.read_bytes(),mtime=0))
 print(label,report['status'],len(records),flush=True)
