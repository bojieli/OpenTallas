#!/usr/bin/env python3
"""Apply the approved ATT_MARK functional fix to a current S8 contract.
No geometry/forest or hard-view qualification is transferred by this transform.
"""
import argparse,copy,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('contract');p.add_argument('out');p.add_argument('--report',required=True);a=p.parse_args()
c=json.loads(Path(a.contract).read_text());changed=[]
for n,i in c['instances'].items():
 if i['master']!='ot_hbm_svc_sm_group_rel_id':continue
 q=i.setdefault('params',{})
 if q.get('PREL')!=1:raise SystemExit('ATT_MARK requires the tested PREL=1 envelope: '+n)
 if q.get('ATT_MARK',0) not in (0,1):raise SystemExit('unsupported ATT_MARK value: '+n)
 q['ATT_MARK']=1;changed.append(n)
if not changed:raise SystemExit('no SVG instances found; no transformation performed')
Path(a.out).write_text(json.dumps(c,indent=1)+'\n')
r=dict(source_fix='b5b98bda84bd3dd6767ca12578815036b73acfff',proof='478773d5d',changed=sorted(changed),count=len(changed),input_sha256=hashlib.sha256(Path(a.contract).read_bytes()).hexdigest(),output_sha256=hashlib.sha256(Path(a.out).read_bytes()).hexdigest(),external_ports_changed=False,added_programme_or_data_edges=0,geometry_forest_qualification='NOT_TRANSFERRED',hard_svg_view='REHARDEN_REQUIRED',current_source_token='REQUIRED')
Path(a.report).write_text(json.dumps(r,indent=1)+'\n');print('ATT_MARK_CONTRACT',len(changed),'instances; geometry/forest and hard view qualification remain required')
