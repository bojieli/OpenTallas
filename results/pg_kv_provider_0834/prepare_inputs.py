#!/usr/bin/env python3
"""Prepare exact source-owned PG reservation list and the canonical top-grid Tcl."""
import argparse,json,sys
from pathlib import Path
for root in (Path(__file__).resolve().parents[1],Path(__file__).resolve().parents[2]):
 sys.path.insert(0,str(root/'tools/die_plan'))
import schema as S
import die_trial as D

def prepare(plan,pdn,prepared,restore,target,out):
 p=S.Plan(S.load(plan),plan)
 source=Path(pdn).read_text().splitlines()
 if not source[-2].startswith('define_pdn_grid -name {parts}') or not source[-1].startswith('add_pdn_connect -grid {parts}'):
  raise ValueError('Unrecognized canonical PDN template; do not remove any other grid')
 r=Path(out);r.mkdir(parents=True,exist_ok=True)
 (r/'source_pg_reservations.json').write_text(json.dumps([['RESERVED',*q] for q in D.pg_stripes(p)],separators=(',',':')))
 (r/'pdn_top.tcl').write_text('read_db {'+prepared+'}\n'+'\n'.join(source[:-2])+'\npdngen\nsource {'+restore+'}\nwrite_db {'+target+'}\nputs KV_PG_TOP_MATERIALIZED\n')
 print('Prepared exact source PG reservations and canonical top PG; macro connector grid explicitly remains a separate obligation')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--pdn-template',required=True);p.add_argument('--prepared-odb',required=True);p.add_argument('--restore-tcl',required=True);p.add_argument('--target-odb',required=True);p.add_argument('--out',required=True);a=p.parse_args();prepare(a.plan,a.pdn_template,a.prepared_odb,a.restore_tcl,a.target_odb,a.out)
