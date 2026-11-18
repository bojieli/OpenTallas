#!/usr/bin/env python3
"""Small RTL proof of literal reset branch equivalence at both clock edges."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from landing_raw_branches import RawBranches


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).with_name('gen_rtl.py').read_text()
    cells = []
    for name in ('ot_dp_rrelay', 'ot_dp_rrelay_nl'):
        m = re.search(r'\bmodule '+name+r'\s*\(.*?\bendmodule', source, re.S)
        if not m: raise ValueError('missing actual cell '+name)
        cells.append(m.group(0))
    body = '''wire r0,r1,r2;
ot_dp_rrelay u0 (.clk(clk),.d(raw),.q(r0));
ot_dp_rrelay_nl u1 (.clk(clk),.d(r0),.q(r1));
ot_dp_rrelay u2 (.clk(clk),.d(r1),.q(r2));'''
    g = RawBranches('mixed', [dict(name='copy',base='r0',stages=[dict(original=n,xy_um=[2,2]) for n in ('r1','r2')],consumers=['origin'])],body,[10,10])
    g.raw_for('origin','r2'); generated='\n'.join(g.rtl)
    accounting=g.validate(body+'\n'+generated)
    tb='''module tb;
reg clk=0, raw=0; reg[31:0] rng=32'h73ce19a5;
integer edges=0, checks=0, pulses=0;
always #5 clk=~clk;
BODY
GENERATED
// Quarter-edge stimulus includes single-half-cycle and multi-cycle pulses.
initial begin
  repeat(8000) begin
    #2.5;
    rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
    if(rng[2:0]==0) begin raw=~raw; pulses=pulses+1; end
  end
  #1; $display("PASS half_edges=%0d checks=%0d pulses=%0d",edges,checks,pulses); $finish;
end
always @(posedge clk or negedge clk) begin
  edges=edges+1;
  #0.01;
  if(edges>20) begin
    if(r1 !== cland_raw_copy_0 || r2 !== cland_raw_copy_1)
      $fatal(1,"PHASE_MISMATCH edge=%0d clk=%0d original=%b%b copy=%b%b",edges,clk,r1,r2,cland_raw_copy_0,cland_raw_copy_1);
    checks=checks+1;
  end
end
endmodule
'''.replace('BODY',body).replace('GENERATED',generated)
    rtl='`timescale 1ns/1ps\n'+'\n'.join(cells)+'\n'+tb
    results={}
    for label,text in [('candidate',rtl),('posedge_mutant',rtl.replace('ot_dp_rrelay_nl u_cland_raw_copy_0','ot_dp_rrelay u_cland_raw_copy_0'))]:
        f=a.out/(label+'.sv'); f.write_text(text); v=a.out/(label+'.vvp')
        subprocess.run(['iverilog','-g2012','-s','tb','-o',str(v),str(f)],check=True,capture_output=True,text=True)
        r=subprocess.run(['vvp',str(v)],capture_output=True,text=True); (a.out/(label+'.log')).write_text(r.stdout+r.stderr)
        results[label]={'returncode':r.returncode,'output':r.stdout.strip(),'rtl_sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
    assert results['candidate']['returncode']==0 and 'PASS half_edges=4000' in results['candidate']['output'],results
    assert results['posedge_mutant']['returncode']!=0 and 'PHASE_MISMATCH' in results['posedge_mutant']['output'],results
    report={'status':'PASS','scope':'actual generated plain/posedge-negedge/plain branch; both-edge RTL comparison under quarter-edge reset pulses; replacement of copied two-phase stage is rejected','accounting':accounting,'actual_cell_sha256':hashlib.sha256('\n'.join(cells).encode()).hexdigest(),'runs':results}
    (a.out/'proof.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
