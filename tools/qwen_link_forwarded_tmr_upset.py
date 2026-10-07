#!/usr/bin/env python3
"""All release-storage single-bit upsets in full NL2, startup and active."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RTL=ROOT/'rtl/physical/ot_qwen_die_link_fwd_full_tmr.sv'
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 cases=[]
 with tempfile.TemporaryDirectory(prefix='qwen-tmr-upset-') as scratch:
  d=Path(scratch)
  for mutation in ['none','missing_vote','shared_vote']:
   source=RTL.read_text()
   if mutation=='missing_vote':source=source.replace('(release1[0]&release1[1]) |\n                       (release1[0]&release1[2]) | (release1[1]&release1[2])','release1[0]')
   if mutation=='shared_vote':source=source.replace('(release1[0]&release1[1]) |\n                       (release1[0]&release1[2]) | (release1[1]&release1[2])','(release1[0]&release1[0]) |\n                       (release1[0]&release1[2]) | (release1[0]&release1[2])')
   (d/'dut.sv').write_text(source)
   # Both hold polarities, all24storagebits,3 injection phases:144positivecases.
   shapes=[(stream,bit,phase,value) for stream in range(4) for bit in range(6) for phase in range(3) for value in range(2)] if mutation=='none' else [(0,3,2,0)]
   for stream,bit,phase,value in shapes:
    target=f'dut.active.link[{stream%2}].'+('ab' if stream<2 else 'ba')+f'.release{bit//3}[{bit%3}]'
    bench='''`timescale 1ns/1ps
module tb;
 reg rst_n=1;reg [3:0] clk=0;
 wire[1:0] coab,coba;wire[1055:0] ao,bo;
 ot_qwen_die_link_fwd_full_tmr #(.NL(2),.ENABLE(1)) dut(.rst_n(rst_n),.fclk_ab_i(clk[1:0]),.fclk_ba_i(clk[3:2]),.fclk_ab_o(coab),.fclk_ba_o(coba),.a_i({1056{1'b1}}),.b_i({1056{1'b1}}),.a_o(ao),.b_o(bo));
 genvar g;generate for(g=0;g<4;g=g+1)begin:stream
   integer edges=0;
   wire[15:0] control=(g<2)?bo[(g%2)*528+:16]:ao[(g%2)*528+:16];
   initial begin #(1+g*0.7);forever #5 clk[g]=~clk[g];end
   always @(negedge rst_n) edges=0;
   always @(posedge clk[g]) begin
    if(rst_n)edges=edges+1;
    #0.1;if(control!==((edges>=3)?16'hffff:16'h0000))$fatal(1,"upset changed exact release stream=%0d edge=%0d",g,edges);
   end
 end endgenerate
 initial begin #0.2 rst_n=0;#3.1 rst_n=1;
 INJECT
 #65;$display("PASS release upset");$finish;
 end
endmodule
'''
    # Injection between edges before first release, after first edge, and active.
    delay=[0.5,7.5,37.5][phase]
    bench=bench.replace('INJECT',f'#{delay} force {target}=1\'b{value}; #23 release {target};')
    (d/'tb.sv').write_text(bench)
    key=f'{mutation}_s{stream}_b{bit}_p{phase}_v{value}'
    comp=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(d/'bench'),str(d/'dut.sv'),str(d/'tb.sv')],capture_output=True,text=True)
    if comp.returncode:raise RuntimeError(comp.stderr)
    r=subprocess.run(['vvp',str(d/'bench')],capture_output=True,text=True)
    (a.out/(key+'.log')).write_text(r.stdout+r.stderr)
    ok=(r.returncode==0 and 'PASS release upset' in r.stdout) if mutation=='none' else (r.returncode!=0 and 'upset changed exact release' in r.stdout)
    cases.append(dict(case=key,qualified=ok,source_sha256=hashlib.sha256(source.encode()).hexdigest(),testbench_sha256=hashlib.sha256(bench.encode()).hexdigest(),log_sha256=hashlib.sha256((a.out/(key+'.log')).read_bytes()).hexdigest(),returncode=r.returncode))
 result=dict(schema='opentallas.qwen_forwarded_link_tmr.upset.v1',pass_all=all(x['qualified'] for x in cases),positive_cases=sum(x['case'].startswith('none_') for x in cases),negative_cases=2,cases=cases,source_sha256=hashlib.sha256(RTL.read_bytes()).hexdigest(),tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope='Single forced release-storage bit only; all24NL2bits,three phases,both polarities. No voter/transient/metastability/multiupset or whole-link protection claim.',adoption=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['pass_all','positive_cases','negative_cases']}))
 if not result['pass_all']:raise SystemExit(1)
if __name__=='__main__':main()
