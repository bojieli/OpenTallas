#!/usr/bin/env python3
"""Smallest full-flit/full-depth storage exactness and checker-mutation gate."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PREFIX='rtl/hbm_accel/collective_full_20261007/'
FILES=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v',PREFIX+'ot_hbm_collective_packet_fifo.sv',PREFIX+'tb_packet_fifo.sv']
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 pins={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
 checks={}
 for name,depth in [('depth64',64),('depth256',256),('corrupt_output',64)]:
  inputs=[str(ROOT/f) for f in FILES]
  if name=='corrupt_output':
   src=(ROOT/FILES[2]).read_text();old='assign dout=decoded[544:0];';assert src.count(old)==1
   m=a.out/'mutant.sv';m.write_text(src.replace(old,"assign dout=decoded[544:0]^545'b1;"));inputs[2]=str(m)
  cmd=['iverilog','-g2012','-s','tb_packet_fifo',f'-Ptb_packet_fifo.DEPTH={depth}','-o',str(a.out/(name+'.vvp'))]+inputs
  build=subprocess.run(cmd,text=True,capture_output=True);(a.out/(name+'.build.log')).write_text(build.stdout+build.stderr)
  if build.returncode:raise RuntimeError(build.stderr)
  run=subprocess.run(['vvp',str(a.out/(name+'.vvp'))],text=True,capture_output=True)
  output=run.stdout+run.stderr;(a.out/(name+'.log')).write_text(output)
  correct=(run.returncode!=0 and 'DATA order mismatch' in output) if name=='corrupt_output' else (run.returncode==0 and 'PASS depth=' in output)
  checks[name]=dict(returncode=run.returncode,passed=correct,output=output)
 assert pins=={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
 record=dict(passed=all(c['passed'] for c in checks.values()),source_sha256=pins,checks=checks,scope='Single545bit queue at logicaldepth64/256 using actual compiledSRAM model. Does not qualify endpoint/calendar/physicaltiming/CDC.')
 (a.out/'record.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record));return not record['passed']
if __name__=='__main__':raise SystemExit(main())
