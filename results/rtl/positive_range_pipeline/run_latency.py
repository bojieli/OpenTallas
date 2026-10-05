"""Measure matched positive-engine active cycles and range-fixup attempts."""
from pathlib import Path
import concurrent.futures
import hashlib
import json
import re
import subprocess
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'results/rtl/positive_range_pipeline'
BUILD=ROOT/'build/positive_range_latency'
BUILD.mkdir(exist_ok=True)
bench=(ROOT/'rtl/test/tb_a3_exp_pos.sv').read_text().replace('module tb_a3_exp_pos;', '''module tb_a3_exp_pos;
    reg [63:0] active_cycles=0, fixup_attempts=0;
    always @(posedge clk) if(rst_n)begin
        if(!in_ready)active_cycles<=active_cycles+1;
        if(dut.state==dut.S_FIXUP)fixup_attempts<=fixup_attempts+1;
    end''').replace('        if (errors == 0)', '        $display("LATENCY active_cycles=%0d fixup_attempts=%0d",active_cycles,fixup_attempts);\n        if (errors == 0)')
(BUILD/'tb.sv').write_text(bench)
common=['rtl/lib/ot_wide_mul_seq.sv','rtl/lib/ot_wide_div_small_seq.sv']
variants={'baseline':'rtl/abi3/ot_a3_fp32_exp_pos_cr_rne.sv','pipeline':'results/rtl/positive_range_pipeline/candidate.sv'}
def run(item):
 name,source=item;obj=BUILD/name
 cmd=[str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'),'--binary','--timing','-j','2','-Wno-fatal','--top-module','tb_a3_exp_pos','--Mdir',str(obj),*[str(ROOT/f) for f in common],str(ROOT/source),str(BUILD/'tb.sv')]
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=240)
 (BUILD/(name+'_build.log')).write_text(p.stdout+p.stderr)
 assert p.returncode==0,p.stderr
 p=subprocess.run([str(obj/'Vtb_a3_exp_pos')],cwd=ROOT/'build/series_divisor_positive_vectors',capture_output=True,text=True,timeout=300)
 (OUT/(name+'_latency.log')).write_text(p.stdout+p.stderr)
 assert p.returncode==0 and 'PASS a3_exp_pos: 2201 arguments' in p.stdout and 'FAIL' not in p.stdout
 m=re.search(r'LATENCY active_cycles=(\d+) fixup_attempts=(\d+)',p.stdout);assert m
 return name,dict(active_cycles=int(m[1]),fixup_attempts=int(m[2]))
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 results=dict(pool.map(run,variants.items()))
b=results['baseline'];c=results['pipeline']
assert c['fixup_attempts']==b['fixup_attempts']
assert c['active_cycles']-b['active_cycles']==2*b['fixup_attempts']
files=[*common,*variants.values(),'rtl/test/tb_a3_exp_pos.sv','build/series_divisor_positive_vectors/cases.txt','results/rtl/positive_range_pipeline/run_latency.py']
results['source_sha256']={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}
results['cycle_increase_percent']=100*(c['active_cycles']/b['active_cycles']-1)
results['scope']='Active cycles for 2201 numerical cases and four refusal/overflow requests; same fixed corpus, not model throughput or whole-engine clock.'
(OUT/'latency.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({k:v for k,v in results.items() if k!='source_sha256'},indent=2))
