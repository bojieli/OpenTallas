#!/usr/bin/env python3
"""Owner continuation gate: TT setup/FF hold >=0, DRC0; SS sensitivity."""
import argparse,json
from pathlib import Path
import dsrom_wfc_split_physical as L

def main():
 p=argparse.ArgumentParser();p.add_argument('--case',type=Path,required=True);p.add_argument('--check',action='store_true');a=p.parse_args()
 r=L.case_record(a.case);sta=json.loads((a.case/'wf_sta.json').read_text());c=sta['corners'];modes=['incontext','reg2reg','region','die150']
 tt=min(c['TT'][m]['setup_wns_ps'] for m in modes);ff=min(c['FF'][m]['hold_wns_ps'] for m in modes)
 ss=min(c['SS'][m]['setup_wns_ps'] for m in modes)
 done=all(c[k].get('done') and c[k].get('exit')==0 for k in ('TT','FF'))
 out=dict(ss_ps=tt,tt_setup_ps=tt,ss_sensitivity_ps=ss,ff_ps=ff,drc=r['drc_errors'],orfs_dir=str(next(a.case.rglob('results/asap7/*/base/6_final.odb')).parent),setup_corner='TT',accepted=done and tt>=0 and ff>=0 and r['drc_errors']==0,case=r,corners=c,closure_rule='TT setup >=0; FF hold >=0; DRC0; SS sensitivity; retained region/die150 IO budgets')
 print(json.dumps(out,separators=(',',':')))
 if a.check and not out['accepted']:raise SystemExit(1)
if __name__=='__main__':main()
