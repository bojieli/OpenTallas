#!/usr/bin/env python3
"""Authoritative SS/FF regional metrics for new WFC masters; explicit +15ps gate."""
import argparse,json
from pathlib import Path
import dsrom_wfc_split_physical as L

def main():
 p=argparse.ArgumentParser();p.add_argument('--case',type=Path,required=True);p.add_argument('--check',action='store_true');a=p.parse_args()
 r=L.case_record(a.case);modes=['incontext','reg2reg','region','die150']
 ss=min(r['timing'][m]['ss_setup_ps'] for m in modes)
 ff=min(r['timing'][m]['ff_hold_ps'] for m in modes)
 out=dict(ss_ps=ss,ff_ps=ff,drc=r['drc_errors'],orfs_dir=str(next(a.case.rglob('results/asap7/*/base/6_final.odb')).parent),
          setup_corner='SS',accepted=ss>=15 and ff>=15 and r['accepted_15_15_region'],case=r)
 print(json.dumps(out,separators=(',',':')))
 if a.check and not out['accepted']:raise SystemExit(1)
if __name__=='__main__':main()
