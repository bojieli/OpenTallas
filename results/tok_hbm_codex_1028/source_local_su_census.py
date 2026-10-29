#!/usr/bin/env python3
"""Trace actual eight-slice SU producer ownership and orphan VMS client0 sockets."""
import argparse,hashlib,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('top',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
s=a.top.read_text()
pat=r'^  (\w+)(?: #(\([^\n]*\)))? (\w+) \(\n(.*?)^  \);'
inst={m[2]:dict(master=m[0],params=m[1],ports=dict(re.findall(r'\.(\w+)\(([^\n]*)\)',m[3]))) for m in re.findall(pat,s,re.M|re.S)}
su={n:o for n,o in inst.items() if re.fullmatch('su_(?:NW|NE|SW|SE)[0-3]',n)}
errors=[]
expected={f'su_{r}{k}' for r in ('NW','NE') for k in range(4)}
if set(su)!=expected:errors.append('source does not contain exactly eight NW/NE SU slices')
rows=[]
for n,o in sorted(su.items()):
 qid=re.search(r'\.QID\((\d+)\)',o['params']);actual=int(qid[1]) if qid else None
 if actual != {'NW':2,'NE':3}[n[3:5]]:errors.append(n+' unexpected QID')
 rows.append(dict(instance=n,master=o['master'],qid=actual,control=o['ports'].get('control'),
                  read_return=o['ports'].get('lg_rr'),write_return=o['ports'].get('lg_w_done')))
pg=inst.get('su_prog',{})
if '.PARTS(2)' not in pg.get('params',''):errors.append('SU programme is not PARTS2')
orphans=[]
for role in ('SW','SE'):
 for b in range(8):
  bank=f'vmb_{role}{b}';o=inst.get(bank,{})
  rq=f'su_{role}{b//2}__lg_rq[{17*(b%2)+16}:{17*(b%2)}]'
  wq=f'su_{role}{b//2}__lg_wq[{281*(b%2)+280}:{281*(b%2)}]'
  if o.get('ports',{}).get('rq0')!=rq or o.get('ports',{}).get('wq0')!=wq:errors.append(bank+' client0 topology differs')
  orphans.append(dict(bank=bank,master=o.get('master'),rq0=rq,wq0=wq,producer_absent=f'su_{role}{b//2}' not in inst))
report=dict(status='SOURCE_8SU_CENSUS' if not errors else 'FAIL_CLOSED',source_top_sha256=hashlib.sha256(s.encode()).hexdigest(),
 source_top=str(a.top),su_slices=rows,programme=pg,orphan_client0=orphans,errors=errors,
 calendar_proof='NOT_RUN: actual current SU/MTP/MU VM calendars not provided; no bank specialization adoption',
 consequence='No direct SW/NW alias: QID validation and memory-return domains differ; no extra SU producer may be invented')
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n')
print(report['status'],len(su),'SU slices;',len(orphans),'orphan bank client0 sockets;errors',errors)
raise SystemExit(bool(errors))
