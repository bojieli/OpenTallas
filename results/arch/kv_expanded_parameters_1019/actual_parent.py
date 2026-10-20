import sys,json,collections
from pathlib import Path
import kv_expand as E
import kv_expand_parameters as P
root=Path('/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14r-4db097403-codexmub')
E.ROOT=root
report=json.loads(Path('/srv/opentallas-scratch/claude/qwen-kvsys/kvs14r-4db097403-codexmub/expand.json').read_text())
leaf={}
for mod,r in report['leaves'].items():
 p=root/r['view']/(mod+'.lef')
 if p.exists():
  nm,blk,sz,ports=E.lef_macro(p)
  leaf[mod]=dict(ports=ports)
profiles=json.loads(Path('actual_candidates/candidate_profiles.json').read_text())
out={}
for file in ('rtl/qwen_sys/split_20261014/qkd_pvw_die_t_ba.sv','rtl/qwen_sys/split_20261014/qkd_pvw_die_t_f_ba.sv'):
 j=E.elaborate('qkd_pvw_die_tb',file,leaf)
 rows=[]
 for name,c in j['cells'].items():
  mod=E.base_type(c['type'])
  if mod not in profiles: continue
  r=report['leaves'][mod]
  literals,proof=P.preserve(root,mod,c.get('parameters',{}),r['rtl'],r['view'],profiles,True)
  rows.append(dict(instance=name,module=mod,literals=literals,parameters=proof['parameters'],native_qualified=proof['native_qualified']))
 counts=dict(collections.Counter(r['module'] for r in rows))
 assert counts=={'ot_qwen_tp8_pv_slice_t':256,'ot_qwen_tp8_pv_join_t':32,'ot_qwen_tp8_pv_wide_ctl_tb':1}, counts
 out[file]=dict(parent_sha256=P.sha(root/file),counts=counts,instances=rows)
Path('actual_parent_profiles.json').write_text(json.dumps(out,indent=1)+'\n')
print('PASS both actual generated boot-age parent sources, 578 PV leaf profiles preserved; native qualification missing')
