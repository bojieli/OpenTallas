#!/usr/bin/env python3
"""Full64-depth protectedCDC component gate with source-pinned progress monitor."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PREFIX='rtl/hbm_accel/collective_cdc_20261007/'
FILES=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv','rtl/hbm_accel/collective_clock_entry_20261007/ot_hbm_collective_reset_entry.sv',PREFIX+'ot_hbm_collective_protected_cdc.sv',PREFIX+'tb_protected_cdc.sv']
MONITOR='''
 integer read_edges=0;
 always @(posedge rclk)begin
  read_edges=read_edges+1;
  if(read_edges%128==0)$display("CDC_PROGRESS edges=%0d writes=%0d reads=%0d fault=%b wb=%0d rb=%0d hp=%0d reset=%b%b por=%b%b inv=%b inr=%b",read_edges,writes,reads,fault,dut.g_on.wb,dut.g_on.rb,dut.g_on.hp,wrst_n,rrst_n,por_stream,por_link,in_v,in_r);
  // 512 flits: serialized upper budget <3*512 retirement edges +3*512
  // producer edges at these periods +reset/repair/stall allowance <8*512.
  if(read_edges>8*512)$fatal(1,"CDC_PROGRESS_FAIL exceeded source/calendar bound writes=%0d reads=%0d fault=%b",writes,reads,fault);
 end
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--prepare-only',action='store_true');a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 pins={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
 bench=a.out/'monitored_bench.sv';s=(ROOT/FILES[-1]).read_text();assert s.count('endmodule')==1;bench.write_text(s.replace('endmodule',MONITOR+'endmodule'))
 cmds={};checks={}
 for name in ['positive','corrupt_output']:
  inputs=[str(ROOT/f) for f in FILES];inputs[-1]=str(bench)
  if name=='corrupt_output':
   src=(ROOT/FILES[-2]).read_text();old='assign out_d=hq[W-1:0];';assert src.count(old)==1
   mutated=a.out/'mutant.sv';mutated.write_text(src.replace(old,"assign out_d=hq[W-1:0]^{{(W-1){1'b0}},1'b1};"));inputs[-2]=str(mutated)
  cmd=['iverilog','-g2012','-s','tb_protected_cdc','-o',str(a.out/(name+'.vvp'))]+inputs;cmds[name]=cmd
  if a.prepare_only:continue
  with (a.out/(name+'.build.log')).open('w') as log:b=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
  if b.returncode:raise RuntimeError('Compilation failed '+name)
  with (a.out/(name+'.log')).open('w') as log:r=subprocess.run(['vvp','-v',str(a.out/(name+'.vvp'))],stdout=log,stderr=subprocess.STDOUT)
  output=(a.out/(name+'.log')).read_text();passed=(r.returncode==0 and 'PASS_CDC ' in output) if name=='positive' else (r.returncode!=0 and 'CDC_DATA mismatch' in output)
  checks[name]=dict(returncode=r.returncode,passed=passed,output=output)
 manifest=dict(source_sha256=pins,private_bench_sha256=hashlib.sha256(bench.read_bytes()).hexdigest(),commands=cmds)
 (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 if a.prepare_only:print('PREPARED_ONLY CDC proof not executed');return 0
 assert pins=={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
 record=dict(passed=all(c['passed'] for c in checks.values()),checks=checks,manifest=manifest,scope='One full545x64 protectedCDC with actual die resetentry; not nativeendpoint/physicaltiming adoption')
 (a.out/'record.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record));return not record['passed']
if __name__=='__main__':raise SystemExit(main())
