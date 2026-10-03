import json,os,runpy,collections,re
from pathlib import Path
# Load functions only, without repeating the census/ref edits.
src=Path('/tmp/maxwell-legacy-retirement-20261003/cleanup.py').read_text();prefix=src[:src.index('R=refs();')];ns={};exec(prefix,ns)
refs=ns['refs']();out=Path('/tmp/maxwell-legacy-retirement-20261003');d=json.loads((out/'before.json').read_text());deleted=[];kept=[];groups=collections.defaultdict(list)
for x in d['candidates']:groups[str(Path(x['path']).parent)].append(x)
terminal=set()
for parent,xs in groups.items():
 od=[x for x in xs if Path(x['path']).suffix=='.odb']
 if od:
  def stage(x):
   n=Path(x['path']).name;v=re.match(r'(\d+)(?:_(\d+))?',n);return (int(v[1]),int(v[2] or 0),x['mtime']) if v else (100,0,x['mtime'])
  terminal.add(max(od,key=stage)['path'])
for x in d['candidates']:
 p=Path(x['path']);why=None
 if x['path'] in terminal or 'final' in p.name:why='terminal/latest checkpoint preserved'
 top=Path('/home/ubuntu/w18work')/p.relative_to('/home/ubuntu/w18work').parts[0] if x['path'].startswith('/home/ubuntu/w18work/') else Path('/tmp/claude-1000/wt')/p.relative_to('/tmp/claude-1000/wt').parts[0]
 if any(str(top) in t and pid!=str(os.getpid()) for pid,k,t in refs):why='fresh process reference'
 try:s=p.stat()
 except FileNotFoundError:kept.append(dict(x,reason='already absent'));continue
 if (s.st_ino,s.st_dev,s.st_size,s.st_mtime,s.st_ctime)!=(x['inode'],x['device'],x['size'],x['mtime'],x['ctime']):why='file changed since census'
 if s.st_mtime>=ns['CUTOFF'] or s.st_ctime>=ns['CUTOFF']:why='recent'
 if why:kept.append(dict(x,reason=why));continue
 p.unlink();deleted.append(x)
result={'deleted':deleted,'kept':kept,'reclaimed_allocated_bytes':sum(x['allocated_bytes'] for x in deleted),'deleted_count':len(deleted),'preserved_sources_logs_json_and_terminal_ODB':True,'no_jobs_killed_restarted_or_built':True,'checks':'privileged fresh cwd/exe/root/openFD/cmdline; old mtime+ctime; inode/device/size/times unchanged; explicit karb21/rebase excluded'}
(out/'after.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['deleted','kept']},indent=2))
