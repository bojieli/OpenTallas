#!/usr/bin/env python3
"""Prove every bound canonical SU ID and current lane/bank parameters; no guessed IDs."""
import argparse,json,pathlib,collections
M={'ot_hbm_su_static_pgslice_lg__lane_exp__canon_7cd691':11,'ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77':9,'ot_hbm_su_static_pgslice_lg__lanes_plain__canon_663526':9}
def prove(plan,facts):
 rows=[]
 for part in plan['partitions']:
  t=plan['partition_types'][part['type']]
  for core in t.get('hard_cores',[]):
   m=core['module']
   if m not in M:continue
   width=M[m];v=core['parent_id_straps']['lane_lane_id'];assert v['width']==width
   native=[r for r in facts if r['plan_part']==part['name'] and (r['plan_local'] or '').startswith(core['inst']+'.')]
   lanes=[r for r in native if r['module']=='ot_hbm_su_static_lane_pinreg'];banks=[r for r in native if r['module']=='ot_hbm_su_static_pinned_bank']
   count=1 if width==11 else 4;assert len(lanes)==len(banks)==count,(part['name'],core['inst'],len(lanes),len(banks))
   expected=[v['value']] if count==1 else [v['value']*4+i for i in range(4)]
   actual=sorted(r['id_ports']['lane_id']['value'] for r in lanes);assert actual==expected,(part['name'],core['inst'],actual,expected)
   for r in lanes:
    assert r['parameters']==dict(ALAT='4',FETCH_EXTRA_EDGES='2',KIND='1' if count==1 else '0',LEAF='1',LN='7',MLAT='4'),r
    assert r['id_ports']['lane_id']['width']==11
   for r in banks:assert r['parameters']==dict(RB='9',READERS='6',WCOPY='0'),r
   rows.append(dict(part=part['name'],plan_type=part['type'],inst=core['inst'],module=m,width=width,declared_value=v['value'],actual_lane_ids=actual,native_lanes=[r['instance'] for r in lanes],MLAT=4,ALAT=4,WCOPY=0))
 assert set(r['module'] for r in rows)==set(M)
 return rows
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('plan');ap.add_argument('facts');ap.add_argument('out');a=ap.parse_args();rows=prove(json.load(open(a.plan)),json.load(open(a.facts)))
 report=dict(status='NATIVE_MEMBER_ID_AND_PARAMETER_PROOF_ONLY_UNADOPTED',cores=len(rows),lane_ids=sum(len(r['actual_lane_ids']) for r in rows),families=dict(collections.Counter(r['module'] for r in rows)),rows=rows)
 pathlib.Path(a.out).write_text(json.dumps(report,indent=2)+'\n');print('PASS',report['cores'],'bound cores',report['lane_ids'],'native lane IDs',report['families'])
