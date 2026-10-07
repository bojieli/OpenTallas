#!/usr/bin/env python3
"""Exact fixed-PC in-band fence mechanism on actual 54/55-hop native hubs."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--codec',type=Path);p.add_argument('--identity',type=Path);p.add_argument('--shim',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 rtl=ROOT/'rtl/physical/ot_qwen_kvc_write_link_bridge_fenced.sv';bench=ROOT/'rtl/test/tb_qwen_kvc_write_bridge_fenced.sv'
 deps=[a.source_root/f for f in ['rtl/physical/ot_qwen_die_cdc_ch.sv','rtl/physical/ot_qwen_die_link_fwd_full_tmr.sv','rtl/lib/ot_async_fifo.sv','rtl/lib/ot_reset_sync.sv']]
 deps += [a.codec or a.source_root/'rtl/physical/ot_qwen_kvc_packet_codec_fence.sv',a.identity or a.source_root/'rtl/physical/ot_qwen_die_hub_identity.sv',a.shim or a.source_root/'rtl/physical/ot_qwen_kvc_hub_cdc.sv']
 cases=[]
 with tempfile.TemporaryDirectory(prefix='qwen-fence-') as tmp:
  def run(key,hops,neg,source):
   c=subprocess.run(['iverilog','-g2012','-s','tb_qwen_kvc_write_bridge_fenced',f'-Ptb_qwen_kvc_write_bridge_fenced.HOPS={hops}',f'-Ptb_qwen_kvc_write_bridge_fenced.NEG={neg}','-o',tmp+'/sim',str(bench),str(source),*map(str,deps)],capture_output=True,text=True)
   (a.out/(key+'.compile.log')).write_text(c.stdout+c.stderr)
   if c.returncode:raise RuntimeError(c.stderr)
   r=subprocess.run(['vvp',tmp+'/sim'],capture_output=True,text=True);log=r.stdout+r.stderr;(a.out/(key+'.log')).write_text(log);return r,log
  for hops,neg in [(54,0),(55,0)]+[(54,n) for n in range(1,16)]:
   key=f'h{hops}_n{neg}';r,log=run(key,hops,neg,rtl)
   expected=f'PASS fenced_bridge HOPS={hops} NEG={neg} writes=96 canceled=4 checks=196 epochs=2 control_flits=1/1' if neg in [0,7] else 'PASS_FENCE_FFFF' if neg==11 else f'PASS_FENCE_NEGATIVE kind={neg}'
   cases.append(dict(case=key,qualified=r.returncode==0 and expected in log,returncode=r.returncode,log_sha256=hashlib.sha256(log.encode()).hexdigest()))
  mutant=Path(tmp)/'mutant.sv';original=rtl.read_text();changed=original.replace('&& tx_ready && count<=5','&& count<=5');assert changed!=original;mutant.write_text(changed)
  r,log=run('startup_room_mutant',54,0,mutant)
  cases.append(dict(case='startup_room_mutant',qualified=r.returncode!=0 and 'UNEXPECTED_FAULT' in log,returncode=r.returncode,mutated_source_sha256=sha(mutant),meaning='Removing TX FIFO rendezvous from native room must fail immediate-start cold reset test.'))
 result=dict(schema='opentallas.qwen_inband_fence.gate.v1',pass_all=all(c['qualified'] for c in cases),cases=cases,source_sha256={str(p):sha(p) for p in [rtl,bench,*deps]},tool_sha256=sha(Path(__file__)),scope='Actual fullNL4 identity hubs,one selected lane,54/55actualTMRhops,distinct0.9/1.2/0.9765625GHz domains at1fs precision.96writes+4typedcancels, exact inband cancellation set, continued newepoch traffic and unchanged native CDC/credit counters. Ledger-ready is an explicit readiness environment, not actual controller recovery.',negative_meanings={'1':'unsolicited ACK','2':'duplicate old ACK','3':'foreign canceled identity','4':'duplicate canceled identity','5':'wrong target epoch','6':'wrong watermark with matching wiretag','7':'early readiness cannot pass handed ownership','8':'same-edge invalid done vetoes ACK enqueue/epoch commit','9':'same-edge invalid cancellation vetoes ACK enqueue/epoch commit','10':'old completion after newepoch rejected','11':'seededFFFE/FFFF acceptance and exhausted watermark thennewseq0','12':'wrong ACK epoch','13':'wrong ACK PC','14':'wrong ACK source','15':'readiness withdrawal at ACK enqueue vetoescommit'},adoption=False,remaining=['actual authoritative controller refresh/read-quarantine readiness','mutable decoder/handoff/owner/credit protection','all physical SS/FF/DRC/reset gates','all-PC/global enrollment'])
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 if not result['pass_all']:raise SystemExit(1)
if __name__=='__main__':main()
