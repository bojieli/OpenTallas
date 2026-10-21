"""Pure log-parser mutants. Synthetic text is never a hardware receipt."""
import argparse,json
from pathlib import Path
from hbm_layer_vehicle.collect_pv_minimum_run import check_rows

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--scoreboard',type=Path,required=True);a=p.parse_args()
 s=json.loads(a.scoreboard.read_text());lines=[]
 for row in range(64):
  value=sum(int(s['expected_words'][row*8+c],16)<<(32*c) for c in range(8))
  lines.append(f"SLICE_SM_ROW cyc={s['begin_edge']+row+1} row={row} data={value:064x}")
 summary=f"SLICE_SM_SUMMARY total=64 unique=64 first={s['begin_edge']+1} last={s['begin_edge']+64}"
 log='\n'.join(lines+[summary]);r=check_rows(log,s)
 assert r['passed'] and r['word_comparisons']==512
 mutants=dict(missing='\n'.join(lines[:-1]+[summary]),extra='\n'.join(lines+[lines[-1],summary]),duplicate='\n'.join([lines[0]]+lines[:-1]+[summary]),mismatch=log.replace(lines[0],lines[0][:-1]+('0' if lines[0][-1]!='0' else '1')),bad_address=log.replace('row=0 ','row=64 ',1),outside_window=log.replace(f"cyc={s['begin_edge']+1}",f"cyc={s['end_edge']+1}",1),missing_summary='\n'.join(lines),bad_summary=log.replace('unique=64','unique=63'))
 for name,text in mutants.items():assert not check_rows(text,s)['passed'],name
 print(json.dumps(dict(status='PURE_PARSER_CHECKS_PASS_SYNTHETIC_TEXT_ONLY',hardware_executed=False,exact_words=512,rejected_mutants=list(mutants)),indent=1))
