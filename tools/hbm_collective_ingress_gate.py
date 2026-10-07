#!/usr/bin/env python3
"""Actual full-width ingress/credit/CDC mechanism, immutable snapshots."""
import argparse,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
FILES=[
 'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',
 'rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv',
 'physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v',
 'rtl/hbm_accel/collective_credit_20261007/ot_hbm_credit_secded_pkg.sv',
 'rtl/hbm_accel/collective_credit_20261007/ot_hbm_credit_rx.sv',
 'rtl/hbm_accel/collective_credit_20261007/ot_hbm_credit_source.sv',
 'rtl/hbm_accel/collective_full_20261007/ot_hbm_collective_packet_fifo.sv',
 'rtl/hbm_accel/collective_cdc_20261007/ot_hbm_collective_protected_cdc_refill.sv',
 'rtl/hbm_accel/collective_flight_20261007/ot_hbm_collective_protected_flight.sv',
 'rtl/hbm_accel/collective_ingress_20261007/ot_hbm_collective_protected_ingress.sv',
 'rtl/hbm_accel/collective_ingress_20261007/tb_protected_ingress.sv']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();out=pathlib.Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
 snapshot=out/'source';snapshot.mkdir();pins={};inputs=[]
 for f in FILES:
  src=ROOT/f;data=src.read_bytes();dst=snapshot/src.name;dst.write_bytes(data);pins[f]=hashlib.sha256(data).hexdigest();inputs.append(dst)
 (out/'source_sha256.json').write_text(json.dumps(pins,indent=2)+'\n')
 runs={}
 for name in ['positive','negative']:
  d=out/name;d.mkdir();sources=list(inputs)
  if name=='negative':
   i=FILES.index('rtl/hbm_accel/collective_flight_20261007/ot_hbm_collective_protected_flight.sv');src=sources[i].read_text()
   old='assign out_d=corrected_output[W-1:0];';new="assign out_d=corrected_output[W-1:0] ^ {{(W-1){1'b0}},1'b1};"
   assert src.count(old)==1;mut=d/'mutant.sv';mut.write_text(src.replace(old,new));sources[i]=mut
   (d/'mutation.json').write_text(json.dumps({'original_sha256':pins[FILES[i]],'mutant_sha256':sha(mut),'old':old,'new':new},indent=2)+'\n')
  cmd=['iverilog','-g2012','-s','tb_protected_ingress','-o',str(d/'test.vvp'),*[str(x) for x in sources]]
  with (d/'build.log').open('w') as log:b=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
  if b.returncode:runs[name]={'build_returncode':b.returncode,'pass':False};continue
  with (d/'simulation.log').open('w') as log:r=subprocess.run(['vvp',str(d/'test.vvp')],stdout=log,stderr=subprocess.STDOUT)
  output=(d/'simulation.log').read_text();passed=(r.returncode==0 and 'PASS ingress' in output) if name=='positive' else (r.returncode!=0 and 'DATA order mismatch' in output)
  runs[name]={'returncode':r.returncode,'pass':passed,'command':cmd,'output':output}
 verdict={'pass':all(x['pass'] for x in runs.values()),'runs':runs,'source_sha256':pins,
  'scope':'Actual single full545 ingress path with landing64, protectedCDC64, protectedflight14, RX256, real credit producer/source and protected72bit grant/ACK CDCs. 384 ordered payloads.',
  'fixture':{'clock_period_ps':833.334,'requested_clock_period_ps':833.333334,'independent_clock_phase_ps':137,'simulation_precision_fs':1,'forward_flight_edges':3,'forward_flight_is_physical_claim':False,'cold_start_and_reset':'Fixture supplied; actual lifecycle provider integration remains separate'},
  'physical_qualified':False,'holds':['aggregate fatal fault crosses clock domains directly: functional quarantine only; physical fault distribution requires implementation/signoff','actual PHY/control transport flight and reset lifecycle integration','full native PF384 calendar/endpoint timing','mapped area and SS/FF physical closure']}
 (out/'verdict.json').write_text(json.dumps(verdict,indent=2)+'\n');print(json.dumps(verdict));return 0 if verdict['pass'] else 1
if __name__=='__main__':sys.exit(main())
