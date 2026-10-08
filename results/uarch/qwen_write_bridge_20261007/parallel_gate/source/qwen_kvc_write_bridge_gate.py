#!/usr/bin/env python3
"""Minimum per-PC bridge gate using actual NL4 hubs and priced 54/55-hop lane."""
import argparse, hashlib, json, subprocess, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--codec',type=Path);p.add_argument('--identity',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 local=['rtl/physical/ot_qwen_kvc_hub_cdc.sv','rtl/physical/ot_qwen_kvc_write_link_bridge.sv','rtl/test/tb_qwen_kvc_write_bridge.sv']
 deps=['rtl/physical/ot_qwen_die_cdc_ch.sv','rtl/physical/ot_qwen_die_link_fwd_full_tmr.sv','rtl/lib/ot_async_fifo.sv','rtl/lib/ot_reset_sync.sv']
 src=[ROOT/f for f in local]+[a.source_root/f for f in deps]+[a.codec or a.source_root/'rtl/physical/ot_qwen_kvc_packet_codec_parallel.sv',a.identity or a.source_root/'rtl/physical/ot_qwen_die_hub_identity.sv']
 cases=[]
 with tempfile.TemporaryDirectory(prefix='qwen-write-bridge-') as t:
  for hops,neg in [(54,0),(55,0)]+[(54,n) for n in range(1,8)]:
   key=f'h{hops}_n{neg}'
   c=subprocess.run(['iverilog','-g2012','-s','tb_qwen_kvc_write_bridge',f'-Ptb_qwen_kvc_write_bridge.HOPS={hops}',f'-Ptb_qwen_kvc_write_bridge.NEG={neg}','-o',t+'/bench',*map(str,src)],capture_output=True,text=True)
   (a.out/(key+'.compile.log')).write_text(c.stdout+c.stderr)
   if c.returncode:raise RuntimeError(c.stderr)
   r=subprocess.run(['vvp',t+'/bench'],capture_output=True,text=True);log=r.stdout+r.stderr;(a.out/(key+'.log')).write_text(log)
   expected=f'PASS_EXPECTED_NEGATIVE kind={neg}' if neg else f'PASS write_bridge HOPS={hops} issued=100 completed=96 canceled=4 checks=192 epochs=2'
   cases.append({'case':key,'qualified':r.returncode==0 and expected in log,'returncode':r.returncode,'log_sha256':hashlib.sha256(log.encode()).hexdigest()})
 result={'schema':'opentallas.qwen_write_bridge.gate.v1','pass_all':all(c['qualified'] for c in cases),'cases':cases,'source_sha256':{str(f):sha(f) for f in src},'tool_sha256':sha(Path(__file__)),'scope':'Actual dualNL4 identity hubs and54/55TMRstages one lane. Native service registered room-emission and modeled ledger17tickcompletion,96exactwrites+4canceledownedrequests across coordinatedepoch fence. Actual controller ledger not instantiated yet.','negative_meanings':{'1':'packet CRC corruption','2':'source identity mismatch','3':'wrong true completion tag','4':'stale/wrong epoch with valid CRC','5':'duplicate true completion','6':'unsafe epoch fence','7':'native producer ignores room'},'adoption':False,'blockers':['actual commitledger binding','full mutable state and native Gray-credit protection','all physical setup/hold/CDC/CRC gates','global epoch fence owner beyond explicit qualified input contract']}
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 if not result['pass_all']:raise SystemExit(1)
if __name__=='__main__':main()
