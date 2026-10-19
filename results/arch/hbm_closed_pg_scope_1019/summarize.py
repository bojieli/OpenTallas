#!/usr/bin/env python3
import json,pathlib
root=pathlib.Path(__file__).resolve().parent
rows=json.loads((root/'selected.json').read_text())
for row in rows:
 d=root/row['name']; p=d/'grouped_summary.json'
 if not p.exists(): row['audit_status']='INCOMPLETE'; continue
 q=json.loads(p.read_text());row.update(audit_status=q['status'],checked=int(q['checked']),failure_count=int(q['failure_count']),failure_groups=q['groups'])
 row['odb_before']=(d/'odb.before.sha256').read_text().strip();row['odb_after']=(d/'odb.after.sha256').read_text().strip();row['odb_unchanged']=row['odb_before']==row['odb_after'];row['audit_exit']=int((d/'audit.rc').read_text())
(root/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps([{k:r.get(k) for k in ['name','audit_status','checked','failure_count','odb_unchanged']} for r in rows],indent=2))
