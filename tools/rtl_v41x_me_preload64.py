#!/usr/bin/env python3
"""Checkpoint-backed 64-wide FP32-to-BF16 ME preload boundary gate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ACC = Path('/tmp/opentallas-v41-fullshape-golden/results/rtl/v41_200k_l0_wo_a_acc_rank0.f32le.bin')
GOLDEN = Path('/tmp/opentallas-v41-fullshape-golden/results/rtl/hdc_v41x_fullshape_200k_l0_wo_a_vectors.json')
RTL = (ROOT/'rtl/hdc/v41x/ot_hdc_v41x_fp32_bf16_preload64.sv',)

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def cv(code):
    if (code >> 23) & 255 == 255:
        return 0, 1, 0
    lo = code & 65535
    hi = (code >> 16) & 65535
    hi = (hi + int(lo > 0x8000 or (lo == 0x8000 and (hi & 1)))) & 65535
    sat = int(((hi >> 7) & 255) == 255)
    if sat:
        hi = (code & 0x80000000) >> 16 | 0x7f7f
    if (hi & 0x7fff) == 0:
        hi = 0
    return hi, 0, sat

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, required=True)
    a=ap.parse_args()
    m=json.loads(GOLDEN.read_text())
    if m['acc']['sha256'] != sha(ACC):
        raise RuntimeError('checkpoint ACC hash mismatch')
    x=np.fromfile(ACC,dtype='<u4')
    if len(x)!=8192: raise RuntimeError('expected two 4096-element groups')
    edge=[0,0x80000000,0x3f808000,0x3f818000,0x7f7fffff,0xff7fffff,
          0x7f800000,0x7fc00000,0xff800000,0x00008000,0x00018000,0x80008000]
    x=np.concatenate((x,np.array((edge*6)[:64],dtype='<u4')))
    with tempfile.TemporaryDirectory(prefix='v41_me_preload64_') as td:
        t=Path(td)
        (t/'in.hex').write_text(''.join(f'{int(v):08x}\n' for v in x))
        expected=[cv(int(v)) for v in x]
        (t/'out.hex').write_text(''.join(f'{v[0]:04x}\n' for v in expected))
        (t/'fault.hex').write_text(''.join(f'{int(any(v[1] for v in expected[b*64:(b+1)*64])):01x}\n' for b in range(129)))
        (t/'sat.hex').write_text(''.join(f'{int(any(v[2] for v in expected[b*64:(b+1)*64])):01x}\n' for b in range(129)))
        tb=t/'tb.sv'
        tb.write_text('''`timescale 1ns/1ps
module tb;
  reg clk=0; always #5 clk=~clk;
  reg rst_n=0, in_v=0;
  reg [1:0] in_p=0;
  reg [12:0] in_e=0;
  reg [2047:0] in_d=0;
  wire out_v,out_fault,out_saturated;
  wire [1:0] out_p;
  wire [12:0] out_e;
  wire [1023:0] out_d;
  reg [31:0] xin[0:8255];
  reg [15:0] xout[0:8255];
  reg xf[0:128],xs[0:128];
  integer b,i;
  ot_hdc_v41x_fp32_bf16_preload64 dut(.*);
  initial begin
    $readmemh("in.hex",xin); $readmemh("out.hex",xout);
    $readmemh("fault.hex",xf); $readmemh("sat.hex",xs);
    repeat(2) @(negedge clk); rst_n=1;
    for(b=0;b<129;b=b+1) begin
      @(negedge clk);
      in_v=1; in_p=b>=64; in_e=(b%64)*64;
      for(i=0;i<64;i=i+1) in_d[i*32 +:32]=xin[b*64+i];
      @(posedge clk); #1;
      if(!out_v || out_p!==in_p || out_e!==in_e ||
         out_fault!==xf[b] || out_saturated!==xs[b])
        $fatal(1,"metadata/fault mismatch beat %0d",b);
      for(i=0;i<64;i=i+1)
        if(out_d[i*16 +:16]!==xout[b*64+i])
          $fatal(1,"value mismatch beat %0d lane %0d got %h exp %h",b,i,
                 out_d[i*16 +:16],xout[b*64+i]);
    end
    $display("PRELOAD64_PASS beats=129 exact=8256 checkpoint=8192 edges=64");
    $finish;
  end
endmodule
''')
        ver=str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
        cmd=[ver,'--binary','--timing','-O0','-Wno-fatal','-Wno-WIDTH','-Wno-UNUSED',
             '-Wno-TIMESCALEMOD','--top-module','tb','-Mdir',str(t/'obj'),
             *map(str,RTL),str(tb),'-CFLAGS','-O0','-j','4']
        build=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=600)
        if build.returncode: raise RuntimeError(build.stderr[-4000:])
        run=subprocess.run([str(t/'obj/Vtb')],cwd=t,capture_output=True,text=True,timeout=120)
        if run.returncode or not re.search(r'PRELOAD64_PASS beats=129 exact=8256',run.stdout):
            raise RuntimeError(run.stdout[-3000:]+run.stderr[-1000:])
    rec=dict(schema='opentallas.rtl.v41x_me_preload64.v1',status='pass',
             claim_scope='Standalone registered 64-wide FP32-to-BF16 preload conversion, not VM port or ME-rate gate',
             exact_elements=8256,checkpoint_elements=8192,edge_elements=64,beats=129,
             latency_cycles_after_registered_vm_data=1,
             fixture_sha256={str(ACC):sha(ACC),str(GOLDEN):sha(GOLDEN)},
             source_sha256={str(p.relative_to(ROOT)):sha(p) for p in (*RTL,Path(__file__))})
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps({k:rec[k] for k in ('status','exact_elements','checkpoint_elements','beats')}))

if __name__=='__main__': main()
