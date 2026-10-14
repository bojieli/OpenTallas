#!/usr/bin/env python3
"""Exact native/reference gate for default-off selected-entry CDC successor."""
import argparse,hashlib,json,sys
from pathlib import Path
import s81_vm_gate as g
ROOT=Path(__file__).resolve().parents[2]
for label,base,enabled in [('default_gold','be_hard_h_gold_s1',False),('default_tp','be_hard_h_tp',False),('gray_gold','be_hard_h_gold_s1',True),('gray_tp','be_hard_h_tp',True),('gray_wrong_entry','be_hard_h_gold_s1',True)]:
 c=dict(g.CASES[base]);c['defines']=list(c.get('defines',[]))+(['OT_BE_RCDC_GRAY'] if enabled else [])
 if label=='gray_wrong_entry':c.update(defines=c['defines']+['OT_BE_RCDC_MUT_WRONG_ENTRY'],expect='fail',regex='FAIL')
 g.CASES['rcdc_'+label]=c
def main():
 ap=argparse.ArgumentParser();ap.add_argument('case',choices=['default_gold','default_tp','gray_gold','gray_tp','gray_wrong_entry']);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 result=g.one('rcdc_'+a.case,a.out)
 files=[ROOT/p for p in g.SRCS]+[ROOT/g.FEH_SRC]
 receipt=dict(case=a.case,source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},gate=result,physical_qualified=False,old_CLOSED_replaced=False)
 (a.out/('receipt_'+a.case+'.json')).write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt['gate'],indent=2));sys.exit(0 if result.get('pass',result.get('ok',False)) else 1)
if __name__=='__main__':main()
