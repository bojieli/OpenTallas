import json,pathlib,tarfile,hashlib,time,os
root=pathlib.Path('/home/ubuntu/w6');inv=json.load(open('/tmp/w6_consumers_r2.json'));rows=[r for r in inv['small_evidence_records'] if not any('/'+x+'/' in r['path'] for x in ['wt','wthbm'])];target=pathlib.Path('/home/ubuntu/otarchives/w6-source-preservation-20261003-r1/small-evidence-r2.tar.gz')
with tarfile.open(target,'x:gz') as tf:
 for r in rows:tf.add(r['path'],arcname=str(pathlib.Path(r['path']).relative_to(root)),recursive=False)
with tarfile.open(target,'r:gz') as tf:
 for r in rows:
  m=tf.extractfile(str(pathlib.Path(r['path']).relative_to(root)));assert hashlib.sha256(m.read()).hexdigest()==r['sha256']
print(json.dumps(dict(archive=str(target),bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),records=len(rows),source_to_archive_all_equal=True,records_preserved=rows,no_deletion=True),indent=2))
