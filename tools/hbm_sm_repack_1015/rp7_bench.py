#!/usr/bin/env python3
"""Emit a production-width retiming miter against the actual landed r6 half."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/landed_parent'))
import lp

def emit(h,v):
    s=json.loads((ROOT/f'results/arch/hbm_smh_r7_1021/lp_spec_{h}_{v}.json').read_text())
    old=json.loads((ROOT/f'results/arch/hbm_smh_r6_1021/lp_spec_{h}_{v}.json').read_text())
    p=lp.Parent(s); ports=p.mod['ports']; off=s['r7']['output_offsets']
    top=s['top_lp']; out=ROOT/s['out_dir']; out.mkdir(parents=True,exist_ok=True)
    olds=f'rtl/hbm_accel/sm/repack/h2a6/lp_{h}_{v}/{old["top_lp"]}.sv'
    src=list(dict.fromkeys(s['child_sources']+[
        'rtl/common/landed_parent/ot_pl_land.sv',
        'rtl/common/landed_parent/ot_pl_land_field_copies.sv',
        'rtl/hbm_accel/sm/repack/h2a5/ot_rp5_land_reset_split.sv',
        olds,f'{s["out_dir"]}/{top}.sv']))
    lines=['`timescale 1ns/1ps',f'module tb_{top}_retime #(parameter integer MUT=0);',
           'reg clk=0; always #5 clk=~clk; reg rst_n=0; integer cyc,bad=0,nc=0;']
    ins=[x for x in ports if x['dir']=='in' and x['name'] not in ('clk','rst_n')]
    outs=[x for x in ports if x['dir']=='out']
    for x in ins: lines.append(f'reg {x["range"] or ""} {x["name"]}=0;')
    for x in outs:
        n=x['name']; r=x['range'] or ''; k=off[n]
        lines.extend([f'wire {r} old_{n},new_{n};',f'reg {r} expected_{n}[0:{k}];',
                      f'always @(posedge clk) begin expected_{n}[0]<=old_{n}; for(integer j=1;j<={k};j=j+1) expected_{n}[j]<=expected_{n}[j-1]; end'])
    for name,sp,prefix in [(old['top_lp'],old,'old'),(top,s,'new')]:
        cs=[f'.ck_{r["name"]}(clk)' for r in sp['regions']]+['.rst_n(rst_n)']
        cs += [f'.{x["name"]}({x["name"]})' for x in ins]
        cs += [f'.{x["name"]}({prefix}_{x["name"]})' for x in outs]
        lines.append(f'{name} #(.MUT({"0" if prefix=="old" else "MUT"})) u_{prefix} ('+', '.join(cs)+');')
    lines.append('initial begin for(cyc=0;cyc<3000;cyc=cyc+1) begin @(negedge clk); if(cyc==32) rst_n=1;')
    for x in ins:
        n=x['name']; width=lp.eval_width(x['range'],p.env)
        expr="5'd13" if n=='attn' else '{'+','.join(['$urandom']*((width+31)//32))+'}'
        lines.append(f'{n}<={expr};')
    lines.append('if(cyc>256) begin')
    for x in outs:
        n=x['name']; k=off[n]; expected=f'expected_{n}[{k-1}]' if k else f'old_{n}'
        lines.append(f'nc=nc+1; if(new_{n} !== {expected}) begin bad=bad+1; if(bad<6) $display("R7_MISMATCH {n} cyc=%0d old=%h new=%h",cyc,{expected},new_{n}); end')
    lines += ['end end',f'$display("R7_RETIME %s h={h} v={v} MUT=%0d compared=%0d mismatches=%0d",bad==0 ? "PASS":"FAIL",MUT,nc,bad);',
              'if(bad) $fatal(1,"retiming mismatch"); $finish; end endmodule']
    tb=f'{s["out_dir"]}/tb_{top}_retime.sv';(ROOT/tb).write_text('\n'.join(lines)+'\n')
    defs=' '.join('-D'+d for d in s['defines'])
    shell=f'''#!/bin/bash
set -euo pipefail
OUT=$1; MUT=${{2:-0}}; mkdir -p "$OUT"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary -j 8 -I. -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT -O1 --top-module tb_{top}_retime -GMUT="$MUT" {defs} {' '.join(src)} {tb} -Mdir "$OUT/obj" > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_{top}_retime" > "$OUT/run.log" 2>&1
'''
    (out/'retime.sh').write_text(shell)
    return src+[tb,str((out/'retime.sh').relative_to(ROOT))]

if __name__=='__main__':
    paths=[]
    for h in 'ns':
        for v in 'mf':
            paths+=emit(h,v)
    (ROOT/'results/arch/hbm_smh_r7_1021/runtime_files.json').write_text(json.dumps(sorted(set(paths)),indent=1)+'\n')
