import pathlib,tarfile,hashlib,json,time
root=pathlib.Path('/home/ubuntu/w6');archive=pathlib.Path('/home/ubuntu/otarchives/w6-source-preservation-20261003-r1/copied-sources.tar.gz');rows=[]
with tarfile.open(archive,'r:gz') as tf:
 for m in tf.getmembers():
  p=root/m.name
  if m.isfile():
   live=hashlib.sha256(p.read_bytes()).hexdigest();saved=hashlib.sha256(tf.extractfile(m).read()).hexdigest();rows.append(dict(path=m.name,bytes=m.size,sha256=live,archive_equal=live==saved))
  elif m.issym():rows.append(dict(path=m.name,symlink=m.linkname,archive_equal=p.is_symlink() and p.readlink().as_posix()==m.linkname))
source_set={str(p.relative_to(root)) for sub in ['wt','wthbm'] for p in (root/sub).rglob('*') if p.is_file() or p.is_symlink()}
report=dict(time_ns=time.time_ns(),archive=str(archive),archive_bytes=archive.stat().st_size,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),source_roots=['/home/ubuntu/w6/wt','/home/ubuntu/w6/wthbm'],files=rows,all_bytes_equal=all(r['archive_equal'] for r in rows),complete_file_set=source_set=={r['path'] for r in rows},git_cleanliness='UNKNOWN: neither copied source directory contains .git',deletion=False)
print(json.dumps(report,indent=2))
