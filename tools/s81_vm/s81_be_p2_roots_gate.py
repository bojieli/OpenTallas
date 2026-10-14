#!/usr/bin/env python3
"""Fresh native current-source default/Gray/split-clock numerical and mutant gates."""
import argparse,hashlib,json,sys
from pathlib import Path
import s81_vm_gate as g
ROOT=Path(__file__).resolve().parents[2]
for label,base,flags in [('default_gold','be_hard_h_gold_s1',[]),('default_tp','be_hard_h_tp',[]),('gray_gold','be_hard_h_gold_s1',['OT_BE_RCDC_GRAY']),('split_gold','be_hard_h_gold_s1',['OT_BE_RCDC_GRAY','OT_BE_P2_SPLIT_ROOTS']),('split_tp','be_hard_h_tp',['OT_BE_RCDC_GRAY','OT_BE_P2_SPLIT_ROOTS']),('split_early_mvc','be_hard_h_gold_s1',['OT_BE_RCDC_GRAY','OT_BE_P2_SPLIT_ROOTS','OT_BE_P2_MUT_MVC_EARLY'])]:
 c=dict(g.CASES[base]);c['defines']=list(c.get('defines',[]))+flags
 if label=='split_early_mvc':c.update(expect='fail',regex='FAIL')
 g.CASES['p2roots_'+label]=c
def main():
 ap=argparse.ArgumentParser();ap.add_argument('case',choices=['default_gold','default_tp','gray_gold','split_gold','split_tp','split_early_mvc']);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 files=[ROOT/p for p in g.SRCS]+[ROOT/g.FEH_SRC];before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files};result=g.one('p2roots_'+a.case,a.out);after={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files};assert before==after,'LIVE_SOURCE_DRIFT'
 receipt=dict(case=a.case,source_sha256=after,gate=result,physical_qualified=False,source_clock_producers_bound=False,old_CLOSED_replaced=False)
 (a.out/('receipt_'+a.case+'.json')).write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt['gate'],indent=2));sys.exit(0 if result.get('pass',result.get('ok',False)) else 1)
if __name__=='__main__':main()
