from pathlib import Path
import json
base=Path('/srv/opentallas-scratch2/claude/codex-hbm-2001')
rows=[]
for tag in ['mu_r13','mu32_r13','mu32_banklocal','mu32_vm32_banklocal','mu32_vm32_banklocal_v2','mu32_vm32_tree','mu32_vm32_tree_l4','mu32_balanced_named_l4','mu32_balanced_equal_l4','mu32_buddy_named_l4']:
 for p in sorted((base/tag).glob('h*.otrun.log')):
  parsed=False
  for ln in p.read_text().splitlines():
   if ln.startswith('{"mode"'):
    parsed=True;r=json.loads(ln)
    for hub,v in r['hubs'].items():
     row=dict(snapshot=tag,log=str(p),H=r['H'],hub=hub,raw=v)
     if 'error' in v:
      row['verdict']='FAIL_NOTRUN' if 'NameError' in v['error'] else 'FAIL_MODEL_PACK'
     else:
      row['max_axis']=max(v['x'],v['y'],*[a or 0 for pair in v['seg'] for a in pair])
      row['verdict']='PASS_MODEL_CUT' if row['max_axis']<=.6+1e-9 else 'FAIL_MODEL_CUT'
     row['qualification']='native VM/FUSED rate guard and real views required'
     if tag not in ['mu32_balanced_named_l4','mu32_balanced_equal_l4','mu32_buddy_named_l4']:
      row['qualification']='PROXY ONLY: incomplete shape and/or geometric endpoint identity; not native MU evidence'
     rows.append(row)
  if not parsed:rows.append(dict(snapshot=tag,log=str(p),verdict='RUNNING_OR_INCOMPLETE'))
(base/'collected_models.json').write_text(json.dumps(rows,indent=1)+'\n')
for r in rows:
 print(r['snapshot'],r.get('H'),r.get('hub'),r['verdict'],r.get('max_axis'))
