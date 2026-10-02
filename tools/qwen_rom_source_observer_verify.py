#!/usr/bin/env python3
"""Validate a reviewed historical observation replay, including all144 saved Xs."""
import argparse,gzip,json,re
from pathlib import Path
from qwen_rom_program_identity import ROOT,decoded,sha
from qwen_rom_source_observer_replay import replay
CAP=ROOT/'results/rtl/qwen_rom_TP4_terminal_20261002/capture.json'

def verify(out,bundle):
 cap=json.loads(CAP.read_text());checks={}
 for layer in range(36):
  for rank in range(4):
   name=f'L{layer}_die{rank}_x.hex';want=decoded(cap['files']['actual/'+name]);got=(out/name).read_bytes()
   if got.split()!=want.split():raise ValueError('retained bitexact layer X: '+name)
   checks[name]={'actual_sha256':sha(got),'retained_sha256':sha(want),'words':len(got.split())}
 log=(out/'token.log').read_text()
 if not re.search(r'QWEN_ROM_TOKEN_TP2 PASS stages=36 token=0 val=00000000 die1_token=0 cycles=168091\b',log):raise ValueError('actual original36layer-prefix terminal/config/cycle contract')
 done=re.findall(r'^STAGE (L\d+) done (.*)$',log,re.M)
 if [name for name,_ in done]!=[f'L{i}' for i in range(36)]:raise ValueError('all36 source-stage completions')
 for name,fields in done:
  parts=dict(p.split('=',1) for p in fields.split() if '=' in p)
  if any(parts[k]!='0' for k in ('seq_fault','core_fault','coll_fault')):raise ValueError('source terminal fault')
 raw=(out/'accepted-state.raw').read_bytes();joined=replay(bundle,raw.decode())
 joined.update(retained_X_checks=checks,raw_sha256=sha(raw),capture_sha256=sha(CAP.read_bytes()),status='PASS_HISTORICAL144_SOURCE_PRODUCER_STATE_OBSERVATION_ONLY',current_source_physical_qualified=False,full_token_repeated=False)
 # Archive/header/source pins must separately be verified before/after by supervisor.
 joined['external_source_archive_stability_receipt_required']=True
 return joined

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workdir',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 b=json.loads(gzip.decompress(a.bundle.read_bytes()));result=verify(a.workdir,b)
 with a.out.open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
if __name__=='__main__':main()
