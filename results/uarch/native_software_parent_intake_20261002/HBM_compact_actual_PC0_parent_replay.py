import json,hashlib,sqlite3,zlib,tarfile,tempfile,sys,time
from pathlib import Path
sys.path.insert(0,'tools')
import h3_complete_native_calendar as C
base=Path('results/uarch/h3_complete_native_calendar_20261002/compact_actual_PC0_journal_r2')
r=json.load(open(base/'lossless_replay.json'));a=base/'lossless_compact_events.tar.gz'
assert hashlib.sha256(a.read_bytes()).hexdigest()==r['archive_SHA256']
h=hashlib.sha256()
with open(r['source_journal_path'],'rb') as f:
 for b in iter(lambda:f.read(1048576),b''):h.update(b)
assert h.hexdigest()==r['source_gzip_SHA256']
start=time.monotonic();n=0;transactions=0
with tempfile.TemporaryDirectory(prefix='parent-compact-PC0-') as tmp:
 root=Path(tmp)
 with tarfile.open(a) as t:
  for member in t:
   assert member.isfile() and member.name in r['files'] and Path(member.name).name==member.name
   raw=t.extractfile(member).read();expected=r['files'][member.name]
   assert len(raw)==expected['bytes'] and hashlib.sha256(raw).hexdigest()==expected['sha256']
   (root/member.name).write_bytes(raw)
 assert len(list(root.iterdir()))==len(r['files'])
 db=sqlite3.connect('file:'+r['source_journal_path']+'?mode=ro',uri=True)
 for j in r['journals']:
  reader=C.open_compact_journal_reader(root,j['journal_id']);source=iter(db.execute('select value from event where journal=? order by seq',(j['journal_id'],)))
  digest=hashlib.sha256();count=0;v=C.CompactLifecycle()
  for e in reader:
   row=next(source);actual=json.dumps(e,sort_keys=True,separators=(',',':')).encode();original=zlib.decompress(row[0]);assert actual==original
   digest.update(len(actual).to_bytes(8,'little')+actual);count+=1;v.accept(e)
   transactions+=e['event']=='request_accept'
  assert next(source,None) is None and count==j['events'] and digest.hexdigest()==j['source_framed_SHA256'] and not v.live
  reader.budget.db.close();n+=count
  print(json.dumps({'journal':j['journal_id'],'events_verified':n,'elapsed_s':time.monotonic()-start}),flush=True)
 db.close()
assert n==r['events'] and transactions==r['sector_transactions']
out={'status':'PASS_PARENT_ALL_ACTUAL96_PC0_EVENTS_BYTE_EXACT','source_SQLite_SHA256':h.hexdigest(),'archive_SHA256':r['archive_SHA256'],'journals':len(r['journals']),'events':n,'sector_transactions':transactions,'artifact_files_verified':len(r['files']),'actual_PC0_only':True,'source_acquisition_scope_separate':True,'full_token_or_physical_qualified':False}
Path('results/uarch/native_software_parent_intake_20261002/HBM_compact_actual_PC0_parent_replay.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out),flush=True)
