#!/usr/bin/env python3
"""Source-owned released hash -> 2 x 24 actual eight-home RTL descriptors."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import random
import subprocess
import hbm_engram_partition as E
import hdc_v41_engram_shipped as S
ROOT=Path(__file__).resolve().parents[1]


def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    t=S.shipped_tables();rng=random.Random(20261015);hist=[];cases=[]
    for i in range(64):
        first=(i%11)==0;cid=[0,1,2,99091][i] if i<4 else rng.randrange(99092)
        if first:hist=[]
        hist.append(cid)
        cases.append((first,cid,S.hashes(t,hist)))
    lines=['''`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,in_valid=0,in_first=0;reg[16:0]in_cid=0;
wire[1:0]request_valid;wire[13:0]request_rank;wire[73:0]request_address;
wire[51:0]request_local_row;wire[9:0]request_staging_slot,request_list_index;
wire[39:0]gather_slot_id;wire done,fault;
ot_hbm_engram_hash_home_native #(.MUTANT_RANK(`MUTANT_RANK)) dut(.*);
reg[6:0]rank[0:1][0:23];reg[25:0]loc[0:1][0:23];
reg[4:0]slot[0:1][0:23];reg[19:0]sid[0:1][0:23];
integer age,l,j,checks=0;
task tick;begin @(posedge clk);#1;end endtask
initial begin repeat(2)tick;@(negedge clk);rst_n=1;''']
    for first,cid,rows in cases:
        for li in range(2):
            counts=[0]*8;rph=(E.RELEASED_ROWS[li]+7)//8
            for j,row in enumerate(rows[li]):
                h,local=divmod(row,rph);rank=li*8+h;slot=counts[h];counts[h]+=1
                sid=(slot//8)*768+rank*8+slot%8
                lines.append(f'rank[{li}][{j}]={rank};loc[{li}][{j}]={local};slot[{li}][{j}]={slot};sid[{li}][{j}]={sid};')
        lines.append(f'@(negedge clk);in_valid=1;in_first={int(first)};in_cid={cid};tick;')
        lines.append('''if(fault || request_valid || done)$fatal(1,"bad input edge");
@(negedge clk);in_valid=0;
for(age=1;age<=36;age=age+1) begin
 tick;
 if(fault || request_valid!==((age>=13)?2'b11:2'b00) || done!==(age==36))$fatal(1,"native calendar age%0d v%b done%b fault%b",age,request_valid,done,fault);
 if(age>=13)begin
  j=age-13;
  for(l=0;l<2;l=l+1)begin
   if(request_rank[l*7+:7]!==rank[l][j] || request_local_row[l*26+:26]!==loc[l][j] || request_address[l*37+:37]!==(37'd103079215104+37'(loc[l][j])*288) || request_staging_slot[l*5+:5]!==slot[l][j] || gather_slot_id[l*20+:20]!==sid[l][j] || request_list_index[l*5+:5]!==j)
    $fatal(1,"hash/home mismatch layer%0d col%0d rank%0d want%0d row%0d want%0d",l,j,request_rank[l*7+:7],rank[l][j],request_local_row[l*26+:26],loc[l][j]);
   checks=checks+1;
  end
 end
end
tick;if(fault || request_valid || done)$fatal(1,"bad drain edge");''')
    lines.append('$display("PASS actual hash to home descriptors=%0d tokens=64 exact ages13..36",checks);$finish;end endmodule')
    tb=out/'tb.sv';tb.write_text('\n'.join(lines))
    sources=[ROOT/'rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv',ROOT/'rtl/hdc/v41/ot_hdc_engram_hash_shipped.sv',ROOT/'rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_home_dispatch.sv',ROOT/'rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_hash_home_native.sv']
    runs=[]
    for name,mutant in [('baseline',0),('rank_mutant',1)]:
        exe=out/name
        cp=subprocess.run(['iverilog','-g2012',f'-DMUTANT_RANK={mutant}','-s','tb','-o',str(exe),*[str(p) for p in sources],str(tb)],text=True,capture_output=True)
        (out/f'{name}.build.log').write_text(cp.stdout+cp.stderr)
        assert cp.returncode==0,cp.stdout+cp.stderr
        rp=subprocess.run(['vvp',str(exe)],text=True,capture_output=True)
        (out/f'{name}.run.log').write_text(rp.stdout+rp.stderr)
        assert (rp.returncode==0)==(mutant==0),rp.stdout+rp.stderr
        runs.append(dict(name=name,returncode=rp.returncode,stdout=rp.stdout.strip()))
    receipt=dict(schema='opentallas.hbm.engram.native_hash_home.v1',status='pass',tokens=64,actual_descriptors=3072,
        calendar=dict(first_request_age=13,last_request_done_age=36,assumed_clock='common functional clock only; physical delivery unproved'),
        actual_rtl=runs,native_full_layer_qualified=False,physical_qualified=False,
        boundaries='Compressed CID boundary and HBM request descriptors. Raw-token mapped producer, actual DMA/read returns, collectives and decode consumer not joined.',
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources+[Path(__file__)]})
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);args=ap.parse_args()
    print(json.dumps(run(args.out),indent=2))
