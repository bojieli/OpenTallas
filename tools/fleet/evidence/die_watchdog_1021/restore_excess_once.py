import json,os,runpy,sys
from pathlib import Path
ns=runpy.run_path('/usr/local/bin/ot-protect-die'); rows=ns['inventory'](); current=ns['sweep'](False); keep={r['pid'] for r in current['selected']}
initial=json.loads(Path(sys.argv[1]).read_text().splitlines()[0]); changed=set(initial['changed']); wrong={r['pid']:r for r in initial['selected'] if r['pid'] in changed and r['pid'] not in keep}
rd=ns['rd']; groups={}
for pid,old in wrong.items():
 if pid not in rows or rows[pid]['start']!=old['start']:continue
 cg=rd(f'/proc/{pid}/cgroup').strip()
 if '/oth-' in cg and not any(rd(f'/proc/{p}/cgroup').strip()==cg for p in keep):groups[cg]=old['adj']
restored=[]
for pid,row in rows.items():
 if pid in keep:continue
 old=wrong.get(pid); value=groups.get(rd(f'/proc/{pid}/cgroup').strip())
 if old and old['start']==row['start']:value=old['adj']
 if value is None or row['adj']!='-1000':continue
 try:
  if rd(f'/proc/{pid}/stat').rsplit(')',1)[1].split()[19]!=row['start']:continue
  Path(f'/proc/{pid}/oom_score_adj').write_text(value+'\n');restored.append(dict(pid=pid,start=row['start'],restored=value))
 except (OSError,IndexError):pass
print(json.dumps(dict(host=os.uname().nodename,restored=restored,retained_die=len(keep))))
