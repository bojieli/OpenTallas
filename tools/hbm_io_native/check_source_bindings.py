#!/usr/bin/env python3
"""Fail-closed source ABI gate for actual HBM host and nine SerDes candidates."""
import argparse,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/s81_ftok'))
from die_port_bind import header,evalw

def ports(rel,master):
 text=(ROOT/rel).read_text()
 # Header terminators inside comments must never truncate the real module.
 text=re.sub(r'/\*.*?\*/','',text,flags=re.S);text=re.sub(r'//[^\n]*','',text)
 p,raw=header(text,master)
 assert raw,f'missing actual module/ports {master}'
 out={n:(d,evalw(w,p)) for n,(d,w) in raw.items()}
 assert all(w is not None for d,w in out.values()),f'unresolved widths {master}'
 return out

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--mutant',choices=['none','width','reset'],default='none');a=ap.parse_args()
 plan=json.loads((ROOT/'results/arch/hbm_io_native_1014/source_plan.json').read_text());errors=[];checks=0
 ld=ports(plan['source_loader'],'ot_hfd_loader_hgi');ctl=ports('rtl/hbm_accel/io_native_20261014/ot_hbm_host_packet.sv','ot_hbm_host_packet');sd=ports('rtl/hbm_accel/io_native_20261014/hfd_serdes487.sv','hfd_serdes487');ep=ports('rtl/hbm_accel/tu/lk_ep_20261010/hfd_lk_ep.sv','hfd_lk_ep')
 if a.mutant=='width':plan['loader_ports'][0]['width']+=1
 if a.mutant=='reset':sd.pop('rst_n')
 used=set()
 for row in plan['loader_ports']:
  n=row['name'];w=row['width'];d=row['loader_direction'];checks+=3
  if ld.get(n)!=(d,w):errors.append(f'loader source ABI {n}')
  if ctl.get(n)!=('output' if d=='input' else 'input',w):errors.append(f'controller source ABI {n}')
  hi,lo=row['h_slice'];bits=set(range(lo,hi+1))
  if hi-lo+1!=w or used&bits:errors.append(f'host packing {n}')
  used|=bits
 checks+=1
 if used!=set(range(787)):errors.append('host h does not cover exact787bits')
 expected={'clk':('input',1),'rst_n':('input',1),'tx':('input',487),'rx':('output',487),'st':('output',2),'padding_fault':('output',1),'pma_tx':('output',544),'pma_tck':('output',1),'pma_rx':('input',544),'pma_rck':('input',1)}
 for n,p in expected.items():
  checks+=1
  if sd.get(n)!=p:errors.append(f'SerDes actual source ABI {n}')
 checks+=1
 if ep.get('phy')!=('inout',974):errors.append('endpoint actual487TX+487RX phy')
 lanes=plan['serdes']['instance_map'];checks+=1
 if len(lanes)!=9 or len({x['serdes'] for x in lanes})!=9:errors.append('nine distinct real lanes')
 sourcefiles=[plan['source_loader'],'rtl/hbm_accel/io_native_20261014/ot_hbm_host_packet.sv','rtl/hbm_accel/io_native_20261014/hfd_host_packet_face.sv','rtl/hbm_accel/io_native_20261014/hfd_host_native.sv','rtl/hbm_accel/io_native_20261014/ot_hbm_host_landing256.sv','rtl/hbm_accel/io_native_20261014/hfd_serdes487.sv','rtl/hbm_accel/io_native_20261014/hbm_link_bank9_native.sv','rtl/hbm_accel/tu/lk_ep_20261010/hfd_lk_ep.sv']+plan['serdes']['digital_sources']
 result={'status':'PASS' if not errors else 'FAIL','checks':checks,'mutant':a.mutant,'errors':errors,'source_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in sourcefiles},'qualification':'Source ABI and packing only. Actual die producer wiring, elaboration, native physical clocks/reset/pins and slots remain separate required gates.'}
 Path(a.out).write_text(json.dumps(result,indent=2)+'\n');print('HBM_IO_SOURCE_BIND',result['status'],f'checks{checks}',errors);return bool(errors)
if __name__=='__main__':sys.exit(main())
