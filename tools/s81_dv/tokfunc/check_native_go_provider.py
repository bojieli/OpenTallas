#!/usr/bin/env python3
"""Check a counterfactual retime mechanism; native architectural tag authority is unresolved."""
from pathlib import Path
import argparse,json,re

def check(root,out):
 root,out=map(Path,(root,out));assert not out.exists();out.mkdir(parents=True)
 programme=json.loads((root/'programme/programme.json').read_text());cases={}
 for name,images in [('reference','old'),('current','advance1'),('candidate','advance1'),('wrong_date','old'),('wrong_tag','advance1')]:
  text=(root/(name+'.log')).read_text()
  source=[(int(t),int(v,16))for t,v in re.findall(r'^SOURCE_CTL (\d+) ([0-9a-f]+)$',text,re.M)]
  issuer=[(int(t),int(v,16))for t,v in re.findall(r'^ISSUER_PIN (\d+) ([0-9a-f]+)$',text,re.M)]
  want=sorted((int(t),int(v,16))for t,v in programme['programmes'][images]['expected_issuer_pin'].items())
  assert issuer==want,(name,'actual XRT issuer dates/words differ from booked producer programme')
  assert len(source)==len(issuer)
  for (s,w),(t,v)in zip(source,issuer):
   assert t-s==3 and (w>>47)&((1<<160)-1)==v
   assert (w>>(21+16))&31==2 and (w>>21)&65535==1
  end=re.search(r'NATIVE_GO_END events=(\d+) consumed=(\d+) gos=(\d+) cfg_words=(\d+) streams=(\d+) xr_fault=(\d) xs_fault=(\d) cf_fault=(\d) seq_fault=(\d)',text)
  assert end and end[1]==end[2] and list(map(int,end.groups()[5:]))==[0,0,0,0],name
  core=[(int(t),int(tag))for t,tag in re.findall(r'^CORE_GO (\d+) tag=(\d+)',text,re.M)]
  seq=[(int(t),int(tag))for t,tag in re.findall(r'^SEQUENCER_GO (\d+) tag=(\d+)',text,re.M)]
  raw=[(int(t),int(tag))for t,tag in re.findall(r'^RAW_Q_GO (\d+) direct_tag=(\d+)',text,re.M)]
  cfg=[(int(t),int(v,16))for t,v in re.findall(r'^CFG_WORD (\d+) ([0-9a-f]+)$',text,re.M)]
  stream=[(int(t),v)for t,v in re.findall(r'^STREAM (\d+) ([0-9a-f]+)$',text,re.M)]
  assert len(core)==len(seq)==len(raw)==2 and len(cfg)==50 and len(stream)==160,name
  assert [v for t,v in seq]==[0,1], 'sequencer-port preincrement hypothesis only; not architectural oracle'
  assert [b[0]-a[0]for a,b in zip(seq,raw)]==[2,2]
  cases[name]=dict(core=core,sequencer=seq,raw_Q=raw,issuer=issuer,cfg_words=cfg,streams=stream,faults=0,producer_stage_edges=3)
 reference=cases['reference'];candidate=cases['candidate'];current=cases['current']
 assert [v for t,v in reference['core']]==[0,1]
 assert candidate['core']==reference['core']
 assert [v for t,v in current['core']]==[1,2]
 assert [t for t,v in current['core']]==[t for t,v in reference['core']]
 assert cases['wrong_date']['core']==[(t+1,v)for t,v in reference['core']]
 assert cases['wrong_tag']['core']!=reference['core']
 for name,row in cases.items():
  assert row['cfg_words']==reference['cfg_words'],(name,'CFG timing/data changed')
  assert row['streams']==reference['streams'],(name,'XS timing/data changed')
  row['preincrement_hypothesis_status']='PASS'if row['core']==reference['core']else 'FAIL_PREINCREMENT_HYPOTHESIS_ONLY'
  row['native_semantic_status']='UNQUALIFIED_ARCHITECTURAL_TAG_ORACLE'
 summary=dict(status='PASS_RETIME_MECHANISM_NATIVE_TAG_AUTHORITY_UNQUALIFIED',
  current_source_status='UNQUALIFIED_ARCHITECTURAL_TAG_ORACLE',architectural_bug_established=False,
  assumed_preincrement_tags=[0,1],native_observed_tags=[1,2],candidate_tags=[0,1],
  expected_GO_edges=[t for t,v in reference['core']],producer_stage_edges=3,
  native_qbank_GO_edges=2,GB_capture_edges=1,parallel_tag_edges=2,
  candidate_new_reset_free_FF=4,candidate_new_clock_pin_loads=4,candidate_new_reset_pin_loads=0,
  added_GO_CFG_XS_cycles=0,CFG_words=50,XS_stream_words=160,
  wrong_date_control_caught=True,wrong_tag_control_caught=True,
  source_programme_period=512,under_TEST_guard_used=False,native_provider_qualified=False,
  arithmetic_core_exercised=False,EF_assumed_idle_free=True,
  clock_ps=833,clock_scope='controlled common phase/L3 forwarded-clock startup; production clock/reset phases unqualified',
  production_enabled=False,scope='one actual0L01/e0 producer/boundary cut; no whole-frame, legal Q-bank cadence, capture fold or global epoch qualification')
 (out/'check.json').write_text(json.dumps(summary,indent=2)+'\n')
 (out/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
 print(json.dumps(summary,indent=2))
 return summary
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True);a=p.parse_args();check(a.root,a.out)
