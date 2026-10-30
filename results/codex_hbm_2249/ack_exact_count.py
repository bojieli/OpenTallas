#!/usr/bin/env python3
"""Preserve original local_w_done station count during opstore V1 repack; R3 ceiling405 unchanged."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import station_resite as SR;import hub_repack as HR
src=Path(sys.argv[2]);out=Path(sys.argv[3]);out.mkdir(parents=True,exist_ok=False)
r=json.loads((src/'die_plan.json').read_text());report=[]
for tn in ('q_b113','q_b113__physical_v1'):
 t=r['partition_types'][tn];rects=SR.core_rects(t);free=HR.Raster(*t['outline_um'],[x[1:]for x in rects]).f
 for i in (41,43):
  s=t['internal_stations'][i];assert s['capture']=='u_sfucore_Q_ctl.local_w_done' and s['bits']==8
  assert len(s['regs_um'])==6
  before=dict(s);solved=None
  for reach in (375.,390.,405.):
   regs=SR.route(free,s['from_um'],s['to_um'],5,reach)
   if regs is not None:solved=(reach,regs);break
  if solved is None: report.append(dict(type=tn,index=i,conn=s['conn'],result='FAIL_EXACT_COUNT'));continue
  reach,regs=solved;s['regs_um']=regs;s['note']+=' | CODEX 22:49 exact5 count recovered within existing405um R3; source WRITE_RETURN unchanged'
  assert SR.max_hop(s)<=405.+1e-5 and not any(SR.blocked(rects,p)for p in regs)
  report.append(dict(type=tn,index=i,conn=s['conn'],result='PASS_CONSTRUCTION',registers=5,old_candidate_registers=6,hop_um=SR.max_hop(s),solver_reach_um=reach,source_cycles_added=0,from_um=s['from_um'],to_um=s['to_um'],regs_um=regs))
(out/'die_plan.json').write_text(json.dumps(r,indent=1)+'\n')
rep=dict(rows=report,plan_sha=hashlib.sha256((out/'die_plan.json').read_bytes()).hexdigest(),all_solved=all(x['result']=='PASS_CONSTRUCTION'for x in report))
(out/'ack_exact_report.json').write_text(json.dumps(rep,indent=1)+'\n');print(json.dumps(rep))
