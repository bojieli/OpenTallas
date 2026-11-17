#!/usr/bin/env python3
"""Collect actual one-private-HEAD MEM44 dates; never retag legacy ages."""
import argparse,hashlib,json,re
from pathlib import Path

def collect(root,run_log='run.log'):
 prep=json.loads((root/'preparation.json').read_text());text=(root/run_log).read_text()
 if 'MEM44_ONE_HEAD_PROFILE_PASS'not in text:raise ValueError('actual native MEM44 profile run has not passed')
 want={'MIF':1,'MEMORY_ALIGNMENT':3,'MEMORY_READ_EXTRA':44,'SEGMENTED_MEMORY_DELAY':1,'KV_WR_PIPE':1}
 if prep['profile']!=want or prep['external_read_packet']['request']!=22 or prep['external_read_packet']['reply']!=21:raise ValueError('wrong actual memory/source profile')
 rows=[{k:int(v)for k,v in re.findall(r'([A-Za-z_][A-Za-z_0-9]*)=(-?\d+)',line)}for line in text.splitlines()if line.startswith('PROFILE_DATES ')]
 head=[r for r in rows if r['mode']==0];sfu=[r for r in rows if r['mode']==1]
 if {r['case']for r in head}!=set(range(len(prep['cases'])))or len(head)!=len(prep['cases']):raise ValueError('incomplete actual genuine HEAD case dates')
 if len(sfu)!=4 or {r['op']for r in sfu}!=set(range(4)):raise ValueError('incomplete actual COPY/SILU/RSQ case dates')
 profiles={};samples=[]
 for r in head:
  meta=prep['cases'][r['case']];n=meta['FP32_words_in_cohort'];ages={k:v-r['cmd']for k,v in r.items()if k not in ('mode','case','op','logical','count','retires','beats')and v>=0}
  if r['count']!=n//8 or r['retires']!=n//8 or r['beats']!=n//64:raise ValueError('actual case coverage differs')
  if ages['LRLYlastwrite']-ages['LRLYwrite']!=n//8-1:raise ValueError('actual output vectors are not continuously one/cycle')
  if ages['lastBF16']-ages['BF16']!=(n//64-1)*8:raise ValueError('actual pack count and endpoint dates do not establish native cadence8')
  if r['gain_read']<=r['first_gain_store']:raise ValueError('actual native CROM read did not follow publication')
  # A complete beat needs8 distinct 8-word input cohorts. Measured continuous
  # input vectors, all beat addresses/payloads, count and first/last dates force
  # every intermediate beat spacing to8; no unobserved faster beat is possible.
  beats=[{'eaddr':(meta['dbase']&0x3fffff)+(i//2)*meta['dso']+(i%2)*64,'receiver_age':ages['BF16']+8*i}for i in range(n//64)]
  stable={k:ages[k]for k in ['emit','req','vm_bound','gain_read','operand_visible','head_write','head_lastwrite','LRLYwrite','LRLYlastwrite','head_retire','head_lastretire','BF16','lastBF16']}
  key=str(n)
  if key in profiles and profiles[key]['ages']!=stable:raise ValueError('actual user/logical projection ages differ within native row shape')
  profiles.setdefault(key,{'FP32_words_in_full_packer_cohort':n,'actual_private_HEAD_words':n//8,'ages':stable,'BF16_receiver_beats':beats,'beat_dates':'analytical reconstruction forced by measured continuous vector cadence1, complete payload/address/count checks and measured endpoints; no prior age file'})
  samples.append({'case':r['case'],'source_case':meta,'raw_receiver_dates':r,'command_input_ages':ages,'ready_field':'first observed actual SU8.ready AND inflight==0 after data; not earliest same-class ready'})
 sfuprofiles=[]
 for r in sfu:
  count=1 if r['op']==3 else 16
  if r['count']!=count or r['retires']!=count:raise ValueError('actual SFU finite word/retire coverage differs')
  sfuprofiles.append({'operation':['COPY128','FUSED_SILU_UP128','RSQ128_SHAPE_STRESS','PRODUCTION_RSQ1'][r['op']],'raw_receiver_dates':r,'command_input_ages':{k:v-r['cmd']for k,v in r.items()if k not in ('mode','case','op','logical','count','retires','beats','programme_store','first_gain_store','last_gain_store')and v>=0},'numeric_reference':'independent hdc_golden FP32 source contract, varying2/4/8 for continuous operations; fused SILU is mul(mul(sigmoid(A),C),B), both rounds retained','ready_field':'actual SU8.ready AND inflight==0; extra retire transport0 only'})
 return {'schema':'opentallas.qwen.private-head-mem44-profile.v1','status':'PASS_COMPONENT_ONLY','source_head_commit':prep['head_source_commit'],'source_head_sha256':prep['head_sha256'],'genuine_stage_sha256':prep['genuine_stage_sha256'],'golden_sha256':prep['golden_library_sha256'],'qualified_preparation_sha256':hashlib.sha256((root/'preparation.json').read_bytes()).hexdigest(),'memory_profile':want,'external_memory_transport':prep['external_read_packet'],'command_origin':'actual delivered cmd_i of native SUVM adapter; no FDN/TT transport','extra_retire_transport':0,'shape_profiles':profiles,'actual_case_samples':samples,'SFU_profiles':sfuprofiles,'packer_companions':prep['packer_companions'],'table_publication':'actual native CROM macro stores observed, with stable preloaded data; external STM/RP table transport and load-overlap window NOT qualified','remaining':['actual coherent global command/pd1/write/retire tuple','complete source-selected TT frontend/native construction','all48 actual source-selected loader windows and exclusive WK/TW arbitration','final physical memory/group/source binding'],'global_enable':False,'physical_adoption':False}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--run-log',default='run.log');a=ap.parse_args();v=collect(a.root,a.run_log);a.out.write_text(json.dumps(v,indent=2)+'\n');print(v['status'],{k:r['ages']for k,r in v['shape_profiles'].items()})
if __name__=='__main__':main()
