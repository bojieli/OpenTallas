#!/usr/bin/env python3
"""Additional nominal833ps independentphase CDC positive, no physicaltiming credit."""
import argparse,hashlib,json,subprocess
from pathlib import Path
import hbm_collective_cdc_gate as base

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 pins={f:hashlib.sha256((base.ROOT/f).read_bytes()).hexdigest() for f in base.FILES}
 src=(base.ROOT/base.FILES[-1]).read_text();old='always #512.3 rclk=~rclk;';new='initial begin #137.0; forever #416.666667 rclk=~rclk; end';assert src.count(old)==1
 bench=a.out/'nominal_phase_bench.sv';bench.write_text(src.replace(old,new).replace('endmodule',base.MONITOR+'endmodule'))
 cmd=['iverilog','-g2012','-s','tb_protected_cdc','-o',str(a.out/'positive.vvp')]+[str(base.ROOT/f) for f in base.FILES[:-1]]+[str(bench)]
 with (a.out/'build.log').open('w') as log:b=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 if b.returncode:raise RuntimeError('compile failed')
 with (a.out/'positive.log').open('w') as log:r=subprocess.run(['vvp',str(a.out/'positive.vvp')],stdout=log,stderr=subprocess.STDOUT)
 output=(a.out/'positive.log').read_text();passed=r.returncode==0 and 'PASS_CDC ' in output
 assert pins=={f:hashlib.sha256((base.ROOT/f).read_bytes()).hexdigest() for f in base.FILES}
 record=dict(passed=passed,returncode=r.returncode,output=output,source_sha256=pins,private_bench_sha256=hashlib.sha256(bench.read_bytes()).hexdigest(),private_replacement=dict(original=old,replacement=new,additional_monitor=base.MONITOR),clock_periods_ps=dict(write=833.333334,read=833.333334),read_phase_ps=137,compile_argv=cmd,scope='Singlefull545x64 protectedCDC; nominalperiod independentphase functionaltest only; noSTA/metastability proof')
 (a.out/'record.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(dict(passed=passed,returncode=r.returncode)));return not passed
if __name__=='__main__':raise SystemExit(main())
