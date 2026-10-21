#!/usr/bin/env python3
"""Full 4x8 gather fields through selected root RTL and actual ownership observer.

A mechanism bench: does not qualify unprovided production enter/leave deadlines.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--mut', type=int, default=0, choices=(0, 1))
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    root = ROOT / 'rtl/qwen_sys/static_kv_die_20261017/qkd_kv_hroot_land.sv'
    obs = ROOT / 'rtl/qwen_sys/static_kv_20261014/qkd_kv_ownership_obs.sv'
    text = root.read_text()
    sub = re.search(r'module qkd_kv_stack_relays_l .*?endmodule', text, re.S)[0]
    if a.mut:
        if sub.count('g <= g_c;') != 1:
            raise ValueError('missing actual gather landing mutation site')
        sub = sub.replace('g <= g_c;', 'g <= g_i;')
    (a.out / 'root.sv').write_text(sub)
    (a.out / 'observer.sv').write_bytes(obs.read_bytes())
    (a.out / 'identity.json').write_text(json.dumps(dict(mut=a.mut, source={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (root, obs)}), indent=2))
    sv = r"""
module tb;
reg ck=0; always #1 ck=~ck;
reg rst_n=0;
reg [31:0] src_dr=0,src_ft=0;
wire [31:0] dr,ft;
wire kd,kf;
reg [31:0] dh[0:3],fh[0:3];
integer n,s,g,bad=0,checks=0;
generate for(genvar st=0;st<4;st=st+1) begin: roots
  wire [143:0] gi,go_;
  for(genvar gr=0;gr<8;gr=gr+1) begin: groups
    assign gi[18*gr+:18]={src_ft[8*st+gr],src_dr[8*st+gr],16'b0};
    assign dr[8*st+gr]=go_[18*gr+16];
    assign ft[8*st+gr]=go_[18*gr+17];
  end
  qkd_kv_stack_relays_l #(.HW(784),.FW(1),.GW(144),.RW(1)) r
  (.ck(ck),.dn(785'b0),.g_i(gi),.r_i(1'b0),.g(go_));
end endgenerate
qkd_kv_ownership_obs #(.QUIET_WIN(1)) o(.ck(ck),.rst_n(rst_n),
 .stage_start(1'b0),.stage(6'b0),.word_valid(1'b0),.es_sv(4'b0),.es_wv(4'b0),
 .host_launch_quiet(1'b1),.host_upstream_quiet(6'b111111),.own_active(1'b0),.own_fault(1'b0),
 .group_drained(dr),.group_fault(ft),.kv_drained_local(kd),.kv_flush_local(kf));
initial begin
 for(n=0;n<4;n=n+1)begin dh[n]=0;fh[n]=0;end
 repeat(8) @(negedge ck);
 rst_n=1;
 for(n=0;n<256;n=n+1)begin
   @(negedge ck);
   // Full group inventory, repeated busy->quiet and fault->clear boundaries.
   src_dr=(n%7<4)?32'hffffffff:~(32'b1 << (n%32));
   src_ft=(n%11==0)?(32'b1 << (n%32)):32'b0;
   for(s=3;s>0;s=s-1)begin dh[s]=dh[s-1];fh[s]=fh[s-1];end
   dh[0]=src_dr;fh[0]=src_ft;
   @(posedge ck); #0.1;
   if(n>10)begin
     checks=checks+1;
     if(kd !== ((&dh[3]) && !(|fh[3])) || kf !== (|fh[3])) bad=bad+1;
   end
 end
 if(bad)begin $display("HROOT_OBSERVATION FAIL checks=%0d bad=%0d",checks,bad);$fatal;end
 $display("HROOT_OBSERVATION PASS groups=32 checks=%0d",checks);$finish;
end
endmodule
"""
    (a.out / 'tb.sv').write_text('`timescale 1ns/1ps\n'+sv)
    cmd=['verilator','--binary','--timing','-Wno-fatal','--top-module','tb','-Mdir',str(a.out/'obj'),'-o','sim',str(a.out/'root.sv'),str(a.out/'observer.sv'),str(a.out/'tb.sv')]
    with (a.out/'build.log').open('w') as log:
        subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
    r=subprocess.run([str(a.out/'obj/sim')],capture_output=True,text=True)
    (a.out/'witness.log').write_text(r.stdout+r.stderr)
    print(r.stdout+r.stderr)
    return 0 if r.returncode==0 else 1

if __name__=='__main__':
    raise SystemExit(main())
