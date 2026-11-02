#!/usr/bin/env python3
"""Copy only the actual frozen compilation readset into repo-relative pricing paths."""
import hashlib,json,re,shutil
from pathlib import Path
D=Path('/srv/opentallas-scratch2/claude/codex-kv-sourcejoin-2110');D.mkdir(exist_ok=True);root=D/'source_root';receipt=json.load(open('/srv/opentallas-scratch2/claude/codex-kv-hostcredit-top-2100/cache_receipt.json'));rows={};skipped=[]
for x in receipt['unchanged_hdl_inputs']:
 p=Path(x['path']);s=str(p);rel=None
 if p.parent.name.startswith('close__'):rel=p.parent.name[len('close__'):].replace('__','/')+'/'+p.name
 elif '__rtl__' in str(p.parent):rel='rtl/'+str(p.parent).split('__rtl__',1)[1].replace('__','/')+'/'+p.name
 elif '__physical__' in str(p.parent):rel='physical/'+str(p.parent).split('__physical__',1)[1].replace('__','/')+'/'+p.name
 elif '/src_main/rtl/' in s:rel='rtl/'+s.split('/src_main/rtl/',1)[1]
 elif '/src_main/physical/' in s:rel='physical/'+s.split('/src_main/physical/',1)[1]
 if rel is None:skipped.append(s);continue
 h=hashlib.sha256(p.read_bytes()).hexdigest();assert h==x['sha256'];assert rel not in rows or rows[rel]['sha256']==h,(rel,rows.get(rel),s)
 q=root/rel;q.parent.mkdir(parents=True,exist_ok=True)
 if not q.exists():shutil.copy2(p,q)
 assert hashlib.sha256(q.read_bytes()).hexdigest()==h
 rows[rel]=dict(source=s,file=str(q),sha256=h)
for rel in ['rtl/qwen_sys/static_kv_20261014/ot_qkd_static_kv_timing.sv','rtl/qwen_sys/static_kv_20261014/qkd_static_kv_return_calendar.sv','rtl/qwen_sys/static_kv_20261014/qkd_static_kv_pc_path_nc.sv']:assert rel in rows,rel
(D/'pricing_source.json').write_text(json.dumps(dict(scope='actual frozen veh60 GEN1 compilation sources only; no current remote checkout fallback',source_root=str(root),rows=rows,non_repo_generated_sources=skipped),indent=2)+'\n');print('PRICING_SOURCE',len(rows),root)
