#!/usr/bin/env python3
"""Exact full53-source/4quarter control4 comparison on all edges, illegal bursts and short/held reset witnesses."""
import argparse, hashlib, json, subprocess, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['tools/s81_vm/area_a2f.sv','tools/s81_vm/area_a2f_control_resetlocal.sv']
BENCH=r'''`timescale 1ns/1ps
module tb;
reg ck=0;always #5 ck=~ck;
reg rn=0;reg [52:0] v=0;reg [423:0] bank=0;reg[2:0] he=0;reg[11:0] pe=0;
wire[671:0] ai,bi;wire[31:0] av,bv;wire[63:0] as_,bs;wire[3:0] af,bf;
s81_a2f_control4 a(ck,rn,v,bank,he,pe,ai,av,as_,af);
s81_a2f_control4_resetlocal b(ck,rn,v,bank,he,pe,bi,bv,bs,bf);
integer n,s,seed=1,initseed,edges=0,bursts=0,resetedges=0;
initial begin
 if($value$plusargs("seed=%d",seed))begin end initseed=seed;
 repeat(8)@(negedge ck);
 for(n=0;n<1500;n=n+1)begin
  rn=!(n<5 || n==100 || (n>=200&&n<202) || (n>=300&&n<303) || (n>=400&&n<407) || n==800);
  if(!rn)resetedges=resetedges+1;
  v={$random(seed),$random(seed)};he=$random(seed);pe={$random(seed)};
  for(s=0;s<53;s=s+1)begin
   if(n%7==0)bank[8*s+:8]=0;else bank[8*s+:8]=$random(seed);
  end
  if(n%7==0)bursts=bursts+1;
  @(posedge ck);#1;
  if({ai,av,as_,af}!=={bi,bv,bs,bf})$fatal(1,"CONTROL_MISMATCH edge%0d ids%b valid%b slot%b fault%b",n,ai!==bi,av!==bv,as_!==bs,af!==bf);
  edges=edges+1;@(negedge ck);
 end
 $display("CONTROL_EQUIV PASS seed%0d edges%0d bursts%0d resetedges%0d",initseed,edges,bursts,resetedges);$finish;
end
endmodule
'''
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--bench',default=None);ap.add_argument('--out',default=str(ROOT/'results/arch/s81_vm_split4_2118/control_proof.json'));a=ap.parse_args()
 variants=[a.bench] if a.bench else ['gold','S81_A2C_MUT_IDBIT']
 rec=[]
 with tempfile.TemporaryDirectory(prefix='s81-control-resetlocal-') as d:
  p=Path(d);(p/'tb.sv').write_text(BENCH)
  for var in variants:
   cmd=['iverilog','-g2012','-s','tb','-o',str(p/'sim')]+([] if var=='gold' else ['-D'+var])+[str(ROOT/s) for s in SOURCES]+[str(p/'tb.sv')]
   subprocess.run(cmd,check=True)
   for seed in ([1] if a.bench else [1,2,3]):
    r=subprocess.run(['vvp','-n',str(p/'sim'),f'+seed={seed}'],text=True,capture_output=True);passed=r.returncode==0 and 'CONTROL_EQUIV PASS' in r.stdout
    print(r.stdout.strip());print('CONTROL_GATE '+('PASS' if passed else 'FAIL')+' '+var,flush=True)
    rec.append(dict(variant=var,seed=seed,rc=r.returncode,stdout=r.stdout,pass_=passed))
    if a.bench:raise SystemExit(0 if passed else 1)
    if var=='gold' and not passed:raise SystemExit('CONTROL_GOLD_FAIL')
    if var!='gold' and (passed or 'CONTROL_MISMATCH' not in r.stdout):raise SystemExit('CONTROL_MUTANT_NOT_OBSERVED')
 out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(dict(status='PASS_REACHABLE_STATE_ALL53_4QUARTERS_ALL_EDGES',sources={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SOURCES},records=rec,not_claimed='No native physical closure or production adoption'),indent=1)+'\n')
if __name__=='__main__':main()
