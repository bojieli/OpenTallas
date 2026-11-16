#!/usr/bin/env python3
"""Check native SEG placement and AR framing from an actual compiled fragment."""
import argparse,copy,hashlib,json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[4];sys.path.insert(0,str(R/'tools/qwen_layerbench'))
import dv_layer as L
import segment_calendar as S
import dv_lower_mat as M

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--compile-receipt',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 j=json.loads(a.compile_receipt.read_text());r=L.ctlm_rec(j['stage']);C,V=r['constants'],r['relay'];plan=r['plan']
 occupied={e['edge_w5']-V['R_CMD'] for e in j['events'] if not e['label'].startswith('SEG base')}
 placements=S.place_segments(plan,C,V,occupied);assert placements==j['calendar']['segment_placements']
 moved=copy.deepcopy(plan)
 for x in placements:
  for q in moved:
   if q['kind']=='SEG' and q['base']==x['base']:q['at']=q['done']=x['pulse']
 before=L.CI.me_rows(plan,C);after=L.CI.me_rows(moved,C);assert before==after
 controls={}
 for x in placements:
  try:S.validate_segment_pulse(x,x['latest_pulse']+1)
  except S.SegmentCalendarError:controls[f'late_SEG{x["base"]}']='CAUGHT'
  else:raise AssertionError('late segment accepted')
 all_busy=set(occupied)
 for x in placements:all_busy.update(range(x['earliest_pulse']-C['LOC_EDGES'],x['latest_pulse']-C['LOC_EDGES']+1))
 try:S.place_segments(plan,C,V,all_busy)
 except S.SegmentCalendarError:controls['no_free_segment_slot']='CAUGHT'
 else:raise AssertionError('full legal interval accepted')
 messages=[];raw_tag_mismatch=raw_last_mismatch=0
 for x in j['ar_framing']['messages']:
  xc={'cc_word':(1<<49)|(x['words']<<32)|x['tag'],'cc_edge':x['first']-M.XC_TO_WORD0}
  raw=[{'edge':x['first']+i,'tag':16*i,'last':int(i%8==7)} for i in range(x['words'])]
  framed=M.ar_framed(raw,xc)
  raw_tag_mismatch+=sum(z['tag']!=w['tag'] for z,w in zip(raw,framed));raw_last_mismatch+=sum(z['last']!=w['last'] for z,w in zip(raw,framed))
  assert sum(z['last'] for z in framed)==1
  try:M.ar_framed(raw[:-1],xc)
  except L.D.LowerError:controls[f'AR_wrong_count_tag{x["tag"]}']='CAUGHT'
  else:raise AssertionError('wrong AR word count accepted')
  messages.append((xc,framed))
 assert M.ar_framer_order(messages);bad=copy.deepcopy(messages);bad[1][0]['cc_edge']=bad[0][1][-1]['edge']-1
 try:M.ar_framer_order(bad)
 except L.D.LowerError:controls['AR_overlapping_message']='CAUGHT'
 else:raise AssertionError('overlapping AR message accepted')
 assert raw_tag_mismatch and raw_last_mismatch;controls['AR_without_framer_tag_last']='CAUGHT'
 rec={'status':'PASS_SOURCE_MODEL','segment_placements':placements,'fixed_ME_END_rows_identical':True,
      'fixed_rows_sha256':hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest(),
      'controls':controls,'raw_AR_tag_mismatches':raw_tag_mismatch,'raw_AR_last_mismatches':raw_last_mismatch,
      'FDN_framer':j['ar_framing'],'source_contract':'Decode later nonzero segments continue base0 fixed calendar; SEG only advances controller before unchanged next ME/END issue. No RTL or tile date changed.'}
 if a.out.exists():raise FileExistsError(a.out)
 a.out.write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps({'status':rec['status'],'controls':controls,'SEG22':next(x for x in placements if x['base']==22)}))
if __name__=='__main__':main()
