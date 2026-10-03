#!/usr/bin/env python3
"""Separate L0 four-rank numerical/source receipts from immutable return FAIL."""
import argparse,gzip,json,re
from pathlib import Path
from qwen_rom_program_identity import ROOT,decoded,sha
from qwen_rom_source_observer_replay import file_sha256

def numerical(out,cap):
 checks={}
 for rank in range(4):
  name=f'L0_die{rank}_x.hex';got=(out/name).read_bytes();want=decoded(cap['files']['actual/'+name])
  if got.split()!=want.split():raise ValueError('all-rank retained exact checkpoint: '+name)
  checks[name]={'sha256':sha(got),'retained_sha256':sha(want),'words':len(got.split())}
 log=(out/'token.log').read_text()
 reference=decoded(cap['files']['token.log']).decode()
 expected=re.search(r'^STAGE L0 done (.*)$',reference,re.M).group(1)
 stages=re.findall(r'^STAGE (\S+) done (.*)$',log,re.M)
 if len(stages)!=1 or stages[0][0]!='L0':raise ValueError('L0-only terminal stage aperture')
 parts=dict(v.split('=',1) for v in stages[0][1].split() if '=' in v)
 ref=dict(v.split('=',1) for v in expected.split() if '=' in v)
 for name in ('cycles','start_cyc','end_cyc','seq_fault','core_fault','coll_fault'):
  if parts.get(name)!=ref[name]:raise ValueError('exact L0 cycle/fault contract: '+name)
 if any(parts[name]!='0' for name in ('seq_fault','core_fault','coll_fault')):raise ValueError('L0 terminal fault')
 if not re.search(r'^QWEN_ROM_TOKEN_TP2 PASS stages=1 token=0 val=00000000 die1_token=0 cycles='+ref['end_cyc']+r' edges='+ref['end_cyc']+r'\b',log,re.M):raise ValueError('source-bound L0 terminal marker')
 return {'status':'PASS_L0_FOUR_RANK_NUMERICAL_CHECKPOINTS_ONLY','checkpoints':checks,'stage_fields':parts,'head_executed':False,'whole_token_repeated':False}

def stable(before,after):
 if before['pins']!=after['pins'] or len(before['pins'])!=142:raise ValueError('all142 pre/post pins')
 if before['exclusive_payload_links']!=after['exclusive_payload_links'] or len(before['exclusive_payload_links'])!=20:raise ValueError('all20 payload links')
 for k in ('preload_sha256','stage_sha256','original_capture_sha256','runtime_command','runtime_environment'):
  if before[k]!=after[k]:raise ValueError('pre/post exact input contract '+k)
 return {'pins':142,'payload_links':20,'status':'PASS_EXACT_PRE_POST_SOURCE_ARCHIVE_INPUT_PINS'}

def gate(out,requests):
 cap=json.loads((ROOT/'results/rtl/qwen_rom_TP4_terminal_20261002/capture.json').read_text())
 n=numerical(out,cap);before=json.loads((out/'runtime-preflight-before.json').read_text());after=json.loads((out/'runtime-preflight-after.json').read_text());s=stable(before,after)
 term=json.loads((out/'runtime-terminal.json').read_text())
 base='/home/ubuntu/w12/qrom-observer-host-9d7-20261003-r1/'
 for name,want in {'qwen_rom_rt_observed':'9d024fc9ae60507bccc339be0dada6af01a0b92abdca12b2bee5c54eb7255ba3','qwen_rom_rt_observed.cpp':'d42a775f630831d3f7640e1b439902f1d3ee07d1b92629375f090a5e4b93b6ad','qwen_rom_observer.hpp':'6c37db03c5fb524bd86a3b63621cdef2dc63e37bd626b6a5ea715d6b42245fcd'}.items():
  if before['pins'][base+name]['sha256']!=want:raise ValueError('exact reviewed binary/host/header '+name)
 if before!=term['preflight_before'] or after!=term['preflight_after']:raise ValueError('supervisor embedded pre/post receipts')
 if term['returncode']!=0 or term['status']!='TERMINAL_ZERO_EXIT_PENDING_INDEPENDENT_LAYERS1_VERIFIER':raise ValueError('zero native terminal')
 if term['scope']!={'head':False,'layers':1,'position':0,'provider_PHY_rate_credit':False,'ranks':4}:raise ValueError('retained position0 L0 scope')
 for name,item in term['outputs'].items():
  p=out/name
  if p.stat().st_size!=item['bytes'] or file_sha256(p)!=item['sha256']:raise ValueError('terminal output pin '+name)
 if requests['raw_sha256']!=term['outputs']['accepted-state.raw']['sha256'] or requests['status']!='PASS_SOURCE_REQUEST_HEADERS_AND_PRODUCER_STATE_ONLY':raise ValueError('source-only request replay receipt')
 if requests['returned_payload_qualified'] or requests['provider_PHY_rate_credit'] or requests['provider_ACK_drained_retired'] is not None:raise ValueError('no fabricated provider lifecycle credit')
 collection=json.loads((out/'collection-terminal.json').read_text())
 if collection['verification_returncode']==0 or 'actual16lane source KV read width' not in (out/'verification.log').read_text():raise ValueError('preserved strict return-record FAIL prerequisite')
 states=requests['source_program_states'];summary={}
 if set(states)!={f'L0/die{r}' for r in range(4)}:raise ValueError('all four journal ranks')
 for key,state in states.items():
  life=state['source_lifetimes']
  if len(life['committed_writes'])!=512 or len(life['source_request_deadlines'])!=512:raise ValueError('all actual current-row writes/deadlines')
  summary[key]={'producer_completions':life['producer_completions'],'consumer_accepts':life['KV_consumer_accepts'],'source_request_profiles':{k:v for k,v in requests['source_request_profiles'].items() if k.startswith(key.split('/')[1]+'/')},'actual_committed_scalar_writes':512,'actual_snapshot_scalar_members':512,'actual_source_request_deadlines':512,'snapshot_edge':life['snapshot_edge'],'source_ME_idle_after_last_consumer_edge':life['first_source_ME_idle_after_last_KV_consumer'],'host_K_hex':state['K_hex'],'host_V_hex':state['V_hex'],'host_state_sha256':state['state_sha256'],'physical_residence':None,'provider_reader_debt':None,'provider_ACK_count':None,'provider_credit_release_count':None,'provider_tag_retire_count':None}
 return {'schema':'QROM_L0_TERMINAL_SOURCE_ONLY_R1','status':'PASS_L0_NUMERICAL_AND_SOURCE_REQUESTS_ONLY_FULL_RETURN_GATE_FAIL','numerical':n,'source_stability':s,'native_returncode':0,'raw_sha256':requests['raw_sha256'],'wall_s':term['ended_epoch']-term['started_epoch'],'child_maxrss_KiB':term['child_maxrss_KiB'],'ranks':summary,'original_strict_return_gate':'FAIL_INTERLEAVED_RECORDS_PRESERVED','physical_or_provider_adoption':False,'whole36_calendar_qualified':False,'ownership_scope':'stage/rank observed; user0/epoch0 observer labels, no runtime provider owner instantiated','source_model_scope':'retained SU64/SMIN7/BD41 TP4pos0 L0 only; no current SMIN6/+55 physical transfer','source_ready_or_ME_idle_is_provider_ACK':False}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True);p.add_argument('--requests',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 r=gate(a.archive,json.loads(a.requests.read_text()))
 with a.out.open('x') as f:json.dump(r,f,sort_keys=True,indent=2);f.write('\n')
if __name__=='__main__':main()
