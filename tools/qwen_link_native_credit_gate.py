#!/usr/bin/env python3
"""Minimum real-hub Gray-credit gate; no qfd_kvc binding or protection claim."""
import argparse,hashlib,json,re,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCES=['rtl/physical/ot_qwen_die_hub.sv','rtl/physical/ot_qwen_die_cdc_ch.sv','rtl/physical/ot_qwen_die_link_fwd_full_tmr.sv','rtl/lib/ot_async_fifo.sv','rtl/lib/ot_reset_sync.sv']
BENCH='rtl/test/tb_qwen_link_native_credit.sv'
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 cases=[]
 with tempfile.TemporaryDirectory(prefix='qwen-credit-') as tmp:
  for hops,neg in [(54,0),(55,0),(54,1),(54,2),(54,3)]:
   key=f'h{hops}_n{neg}'
   cmd=['iverilog','-g2012','-s','tb_qwen_link_native_credit',f'-Ptb_qwen_link_native_credit.HOPS={hops}',f'-Ptb_qwen_link_native_credit.NEG={neg}','-o',tmp+'/bench',str(ROOT/BENCH),*[str(a.source_root/s) for s in SOURCES]]
   comp=subprocess.run(cmd,capture_output=True,text=True);(a.out/(key+'.compile.log')).write_text(comp.stdout+comp.stderr)
   if comp.returncode:raise RuntimeError(comp.stderr)
   r=subprocess.run(['vvp',tmp+'/bench'],capture_output=True,text=True);log=r.stdout+r.stderr;(a.out/(key+'.log')).write_text(log)
   expected={1:'NATIVE_FAULT',2:'CREDIT_CONSERVATION',3:'CREDIT_RANGE'}.get(neg)
   qualified=(r.returncode==0 and f'PASS native_credit HOPS={hops} checks=384 epochs=2' in log) if not neg else (r.returncode!=0 and expected in log)
   cases.append(dict(case=key,HOPS=hops,negative=neg,qualified=qualified,returncode=r.returncode,expected_failure=expected,log_sha256=hashlib.sha256(log.encode()).hexdigest(),epochs=[dict(zip(['epoch','hops','received_a','received_b','credit_seen_rtt_a','credit_seen_rtt_b','window_restart_a','window_restart_b','cycles','stalls_a','stalls_b','wraps_a','wraps_b'],map(int,x))) for x in re.findall(r'EPOCH (\d+) hops=(\d+) delivered=(\d+)/(\d+) first_credit_rtt=(\d+)/(\d+) window_restart=(\d+)/(\d+) cycles=(\d+) stalls=(\d+)/(\d+) wraps=(\d+)/(\d+)',log)]))
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 result=dict(schema='opentallas.qwen_native528_credit.gate.v1',pass_all=all(c['qualified'] for c in cases),cases=cases,source_sha256={s:sha(a.source_root/s) for s in SOURCES},bench_sha256=sha(ROOT/BENCH),tool_sha256=sha(Path(__file__)),scope='Actual dualNL4 hubs one active lane,54/55actualTMRhops,phase-independentclocks,96bidirectionalwordsperdrainedepoch×2. BadGray andunilateralresetnegatives expose silent nativecreditfailures; passing external detection does NOT qualify nativeprotection. No productionqfd_kvcendpoint here.',adoption=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 if not result['pass_all']:raise SystemExit(1)
if __name__=='__main__':main()
