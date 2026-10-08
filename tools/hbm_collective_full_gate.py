#!/usr/bin/env python3
"""One full PF384 endpoint; separate committed source, no full-die simulation."""
import argparse,hashlib,json,subprocess
from pathlib import Path
import ha2_hub_credit_gate as base
ROOT=Path(__file__).resolve().parents[1]
P='rtl/hbm_accel/collective_full_20261007/'
TOP='tb_hbm_collective_full_candidate'
END=P+'ot_hbm_collective_full_candidate.sv'
FILES=list(dict.fromkeys([s for s in base.PARENT if s!='rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_owner.sv']+base.HALF+['rtl/hbm_accel/ha2_ar/ot_ha2_truecredit.sv','rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v']+[P+x for x in ['ot_hbm_collective_packet_fifo.sv','ot_hbm_collective_fifo_adapter.sv','ot_hbm_collective_full_candidate.sv',TOP+'.sv']]))
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--threads',type=int,default=4);p.add_argument('--prepare-only',action='store_true');p.add_argument('--packet-sram',type=int,choices=[0,1],default=1);a=p.parse_args()
 a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 pins={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
 text=(ROOT/END).read_text();old='!invalid_partial_port[p] && owner_p_r[p]) rb_pop[p]';assert text.count(old)==1
 mutant=a.out/'endpoint_mutation.sv';mutant.write_text(text.replace(old,'!invalid_partial_port[p] && (owner_p_r[p] || $test$plusargs("IGNORE_PEER_CREDIT"))) rb_pop[p]'))
 cmd=['verilator','--binary','--timing','-O0','-Wno-fatal','-Wno-WIDTH','--top-module',TOP,f'-GPACKET_SRAM={a.packet_sram}','--Mdir',str(a.out/'obj'),'--build-jobs',str(a.threads)]+[str(mutant if f==END else ROOT/f) for f in FILES]
 (a.out/'source_pins.json').write_text(json.dumps(pins,indent=2));(a.out/'command.json').write_text(json.dumps(cmd,indent=2))
 if a.prepare_only:print('PREPARED_ONLY: exactness and latency unmeasured');return 0
 with (a.out/'build.log').open('w') as log:b=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
 (a.out/'build.exit').write_text(str(b.returncode));
 if b.returncode:return b.returncode
 checks={}
 for mode in ['baseline','CORRUPT_GOLDEN','IGNORE_PEER_CREDIT']:
  cmd=[str(a.out/'obj'/('V'+TOP))]+([] if mode=='baseline' else ['+'+mode])
  with (a.out/(mode+'.log')).open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,cwd=a.out)
  output=(a.out/(mode+'.log')).read_text()
  passed=(r.returncode==0 and 'PASS_HA2_TRUECREDIT_ENDPOINT ' in output) if mode=='baseline' else (r.returncode!=0 and ('ENDPOINT_FAIL numerical or identity mismatch' if mode=='CORRUPT_GOLDEN' else 'ENDPOINT_CREDIT_VIOLATION ') in output)
  checks[mode]=dict(returncode=r.returncode,passed=passed,output=output)
 assert pins=={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
 record=dict(packet_sram=a.packet_sram,traffic_calendar='contributor-major hot-column; matched0/1 runs required for latency delta',passed=all(x['passed'] for x in checks.values()),checks=checks,source_sha256=pins,scope='One native truecredit PF384 endpoint with full protected packetSRAM queues; PHYbench1000ps/core833ps CDC functional only; no signoff/tokenrate claim.')
 (a.out/'record.json').write_text(json.dumps(record,indent=2));print(json.dumps(record));return not record['passed']
if __name__=='__main__':raise SystemExit(main())
