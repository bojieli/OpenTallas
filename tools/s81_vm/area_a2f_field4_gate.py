#!/usr/bin/env python3
"""Full53source,4quarter,3slot field16 vs four standardfield4 leaves: every bit/edge, reset and bad selections."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['tools/s81_vm/area_a2f.sv','tools/s81_vm/area_a2f_field4.sv']
TB=r'''`timescale 1ns/1ps
module tb;
reg ck=0;always #5 ck=~ck;reg rst=0;reg[847:0] data=0;reg[671:0] sel=0;reg[31:0] dv=0;reg[63:0] ds=0;
wire[31:0] av,bv;wire[511:0] ad,bd;wire[3:0] af,bf;
s81_a2f_field16 a(ck,rst,data,sel,dv,ds,av,ad,af);
s81_a2f_field16_split4 b({4{ck}},{4{rst}},data,sel,dv,ds,bv,bd,bf);
`ifdef S81_FIELD4_MUT_DATA
initial force b.bitslice[1].u_leaf.u_impl.o_data[0]=1'b0;
`endif
integer n,k,seed=1,initseed,edges=0;
initial begin
 if($value$plusargs("seed=%d",seed))begin end initseed=seed;
 repeat(8)@(negedge ck);
 for(n=0;n<400;n=n+1)begin
  rst=!(n<5 || (n>=160 && n<167) || n==300);
  for(k=0;k<27;k=k+1)data[32*k+:32]=$random(seed);
  for(k=0;k<96;k=k+1)sel[7*k+:7]={1'b1,6'($unsigned($random(seed))%64)};
  for(k=0;k<32;k=k+1)ds[2*k+:2]=$random(seed);
  dv=$random(seed);
  if(n<30)begin sel=0;for(k=0;k<96;k=k+1)sel[7*k+:7]=7'h40;data='1;ds=0;dv='1;end
  @(posedge ck);#1;
  if({av,ad,af}!=={bv,bd,bf})$fatal(1,"FIELD4_MISMATCH edge%0d valid%b data%b fault%b",n,av!==bv,ad!==bd,af!==bf);
  edges=edges+1;@(negedge ck);
 end
 $display("FIELD4_EQUIV PASS seed%0d edges%0d sources53 quarters4 slots3 outputbits512",initseed,edges);$finish;
end
endmodule
'''
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--bench',default=None);ap.add_argument('--out',default=str(ROOT/'results/arch/s81_vm_split4_2118/field4_component_proof.json'));a=ap.parse_args();rec=[]
 with tempfile.TemporaryDirectory(prefix='s81-field4-gate-') as d:
  p=Path(d);(p/'tb.sv').write_text(TB)
  for var in ([a.bench] if a.bench else ['gold','S81_FIELD4_MUT_DATA']):
   subprocess.run(['iverilog','-g2012','-s','tb','-o',str(p/'sim')]+([] if var=='gold' else ['-D'+var])+[str(ROOT/s) for s in SOURCES]+[str(p/'tb.sv')],check=True)
   for seed in ([1] if a.bench else [1,2,3]):
    r=subprocess.run(['vvp','-n',str(p/'sim'),f'+seed={seed}'],text=True,capture_output=True);ok=r.returncode==0 and 'FIELD4_EQUIV PASS' in r.stdout
    print(r.stdout.strip());print('FIELD4_GATE '+('PASS' if ok else 'FAIL')+' '+var,flush=True);rec.append(dict(variant=var,seed=seed,rc=r.returncode,stdout=r.stdout,pass_=ok))
    if a.bench:raise SystemExit(0 if ok else 1)
    if var=='gold' and not ok:raise SystemExit('FIELD4_GOLD_FAIL')
    if var!='gold' and (ok or 'FIELD4_MISMATCH' not in r.stdout):raise SystemExit('FIELD4_MUTANT_ESCAPED')
 out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(dict(status='PASS_ACTUAL53_SOURCE_4QUARTER_3SLOT_COMPONENT',sources={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SOURCES},records=rec,not_claimed='Full128-SRAM composition or native physical qualification'),indent=1)+'\n')
if __name__=='__main__':main()
