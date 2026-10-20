#!/usr/bin/env python3
"""Register quarter-score diagnostic helper as an explicit die source dependency.

Only valid-key arithmetic faults gain an existing sticky fault path. Every score
value/valid/last cycle is unchanged; error visibility +1 ctl edge after score.
"""
import argparse,gzip,json
from pathlib import Path
DEP='rtl/hbm_accel/index/quad_1017/ot_hbm_idx_score_fault_static.sv'

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('inp');ap.add_argument('out');ap.add_argument('--report',required=True);a=ap.parse_args()
 c=json.load(gzip.open(a.inp,'rt') if a.inp.endswith('.gz') else open(a.inp));done=[]
 for n,v in c['instances'].items():
  if v['master']=='ot_hbm_idx_score_quarter_static':
   v['rtl_deps']=sorted(set(v.get('rtl_deps',[])+[DEP]));
   if 'l16b:' not in (v.get('note') or ''):v['note']=(v.get('note') or '')+' | l16b: registered valid-key score arithmetic flags feed existing sticky fault; no score data cycles changed'
   done.append(n)
 assert len(done)==4,done
 r=dict(layer='l16b_score_fault',instances=done,dependency=DEP,successful_data_added_cycles=0,diagnostic_edges_after_registered_score=1,physical_obligation='quarter scorer source changes require fresh source-bound synthesis/qualification')
 Path(a.report).write_text(json.dumps(r,indent=1)+'\n')
 if a.out.endswith('.gz'):
  with gzip.open(a.out,'wt') as f:json.dump(c,f)
 else:Path(a.out).write_text(json.dumps(c)+'\n')
 print('L16B_OK four quarter score fault checkers; datapath unchanged')
if __name__=='__main__':main()
