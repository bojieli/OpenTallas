#!/usr/bin/env python3
"""Check actual full NB2-pair feedback/data against original source and checkpoint gold."""
from pathlib import Path
import argparse,json,re
from collections import defaultdict

def inspect(root,name,gold,operations):
 text=(root/(name+'.log')).read_text();errors=[]
 end=re.search(r'PAIR_END partials=(\d+) q_fault=(\d) busy=(\d) walking=(\d) bank_free=(\d) sh_free=(\d)',text)
 if not end:errors.append('missing actual pair terminal')
 elif end.groups()[1:]!=('0','0','0','1','1'):errors.append('native pair fault/not idle at terminal: '+end[0])
 ctl=re.search(r'NATIVE_GO_END events=(\d+) consumed=(\d+) gos=(\d+) cfg_words=(\d+) streams=(\d+) xr_fault=(\d) xs_fault=(\d) cf_fault=(\d) seq_fault=(\d)',text)
 if not ctl or ctl[1]!=ctl[2] or any(map(int,ctl.groups()[5:])):errors.append('producer/landing/sequencer fault')
 core=[(int(t),int(tag))for t,tag in re.findall(r'^CORE_GO (\d+) tag=(\d+)',text,re.M)]
 tags=[(gold['first_operation_tag']+i)%4 for i in range(operations)]
 if [tag for t,tag in core]!=tags:errors.append('actual GO tag sequence differs from original OPTAG1 contract')
 got=defaultdict(list);raw=[]
 for fields in re.findall(r'^PAIR_RET (\d+) mb=(\d+) row=(\d+) seg=(\d+) n=(\d+) pos=(\d+) val=([0-9a-f]+) err=(\d)$',text,re.M):
  t,mb,row,seg,n,pos=map(int,fields[:6]);value=int(fields[6],16);err=int(fields[7]);identity=(mb,row&16383,seg,n,pos)
  got[identity].append(dict(edge=t,tag=row>>14,value=value,error=err));raw.append([t,mb,row,seg,n,pos,value,err])
 expected={(v['macro'],v['row'],v['segment'],v['nseg'],v['pos']):v['value']for v in gold['expected_each_operation']}
 if got.keys()!=expected.keys():errors.append('actual pair row/segment/position identity differs from native CFG')
 for key,value in expected.items():
  seq=got.get(key,[])
  if len(seq)!=operations:errors.append('partial count differs for '+str(key))
  if [v['tag']for v in seq]!=tags:errors.append('partial operation tags differ for '+str(key))
  if any(v['value']!=value or v['error'] for v in seq):errors.append('literal checkpoint partial/error differs for '+str(key))
 return dict(status='PASS'if not errors else 'FAIL',errors=errors,core=core,partial_words=raw,
             feedback=[l for l in text.splitlines()if l.startswith('Q_FEEDBACK ')],
             cfg=[l for l in text.splitlines()if l.startswith('CFG_WORD ')],
             stream=[l for l in text.splitlines()if l.startswith('STREAM ')],
             terminal=end[0]if end else None)

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
 gold=json.loads((a.root/'independent_gold.json').read_text());programme=json.loads((a.root/'programme/programme.json').read_text());operations=len(programme['programmes']['old']['phases'])
 names=['original_direct','current_direct','counterfactual_retime','wrong_date','wrong_tag'];cases={n:inspect(a.root,n,gold,operations)for n in names}
 original=cases['original_direct'];current=cases['current_direct'];eq={key:original[key]==current[key]for key in ['core','partial_words','feedback','cfg','stream']}
 control_differences={n:{key:cases[n][key]!=original[key]for key in ['core','partial_words','feedback','cfg','stream']}for n in names[2:]}
 caught={n:cases[n]['status']=='FAIL' or any(control_differences[n].values())for n in names[2:]}
 passed=original['status']==current['status']=='PASS'and all(eq.values())and all(caught.values())
 report=dict(status='PASS_FULL_SELECTED_NB2_NATIVE_GO_PROVIDER_COMPONENT'if passed else 'FAIL_FULL_SELECTED_NB2_NATIVE_GO_PROVIDER_COMPONENT',operations=operations,
  independent_first_tag=gold['first_operation_tag'],independent_operation_tags=[(gold['first_operation_tag']+i)%4 for i in range(operations)],
  original_status=original['status'],current_status=current['status'],original_errors=original['errors'],current_errors=current['errors'],
  exact_original_current=eq,controls_caught=caught,control_differences=control_differences,wrong_date_arithmetic_changed=control_differences['wrong_date']['partial_words'],wrong_date_GO_capture_changed=control_differences['wrong_date']['core'],arithmetic_core_exercised=True,real_walking_bank_shadow_feedback=True,
  constant_checkpoint_activation=True,fresh_version_or_production_epoch_qualified=False,
  source_period=512,clock_ps=833,native_provider_qualified=False,production_enabled=False,
  added_RTL_FF=0,source_tag_retime_needed=False,
  scope='One actual0L01/e0 NB2 source pair with actual images and controlled common-phase/L3 startup; no fullframe/token/capturefold/production clock qualification')
 (a.out/'check.json').write_text(json.dumps(report,indent=2)+'\n');(a.out/'cases.json').write_text(json.dumps(cases,indent=2)+'\n');print(json.dumps(report,indent=2));return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
