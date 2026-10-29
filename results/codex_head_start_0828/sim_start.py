#!/usr/bin/env python3
"""Ideal-clock structural sim of emitted START provider vs its own JSON.

All clock ports share one ideal clock; each local reset port releases at its
recorded raw_release cycle. Expected first-high cycle of every die output is
derived independently from start_stages.json (root R+SETTLE, +3+PAD per edge
under zero skew). Checks RTL wiring/PAD/settle/reset binding, not J or phase.
"""
import json,subprocess,sys,re
from pathlib import Path
d=Path(sys.argv[1]);rtl=Path(sys.argv[2]);w=Path(sys.argv[3]);w.mkdir(exist_ok=True)
st=json.load(open(d/'start_stages.json'));sv=(d/'start_stages.sv').read_text()
I={s['region']:s for s in st['stages']}
root=next(s for s in st['stages'] if s['root'])
arr={}
def a(s):
    if s['region'] in arr:return arr[s['region']]
    v=s['reset_source']['raw_release']+s['settle']+1 if s['root'] else a(I[s['parent']])+3+s['pad']
    arr[s['region']]=v;return v
exp={o['net']:a(I[next(x['region'] for x in st['stages'] if x['id']==o['stage'])])+3+0 for o in st['die_outputs']}
# die outputs leave the last stage directly (stage output = start of that stage); recompute exactly:
exp={o['net']:a(next(x for x in st['stages'] if x['id']==o['stage'])) for o in st['die_outputs']}
hdr=re.search(r'module ot_die_start_stages \((.*?)\);',sv,re.S)[1]
ins=re.findall(r'input\s+wire\s+(\w+)',hdr);outs=re.findall(r'output\s+wire\s+(\w+)',hdr)
rel={n:v['raw_release'] for n,v in st['reset_ports'].items()}
tb=['`timescale 1ns/1ps','module tb;','reg clk=0; always #5 clk=~clk; integer cyc=0; always @(posedge clk) cyc<=cyc+1;']
tb+=[f'reg {n}=0;' for n in ins if n in rel]+[f'wire {n};' for n in outs]+[f'integer f_{n}=-1;' for n in outs]
con=[f'.{n}(clk)' if n not in rel else f'.{n}({n})' for n in ins]+[f'.{n}({n})' for n in outs]
tb.append('ot_die_start_stages dut('+','.join(con)+');')
# reset port high from posedge index R onward: set just after negedge before posedge R
tb+=[f'always @(negedge clk) if (cyc=={r}) {n}<=1;' for n,r in rel.items()]
tb+=[f'always @(posedge clk) if ({n} && f_{n}<0) f_{n}=cyc;' for n in outs]
tb.append('initial begin #4000 ; '+' '.join(f'$display("O {n} %0d",f_{n});' for n in outs)+' $finish; end endmodule')
(w/'tb.sv').write_text('\n'.join(tb))
r=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(w/'a.out'),str(w/'tb.sv'),str(d/'start_stages.sv'),str(rtl)],capture_output=True,text=True)
if r.returncode:print(r.stderr[:3000]);sys.exit(1)
o=subprocess.run(['vvp','-n',str(w/'a.out')],capture_output=True,text=True).stdout
got={m[0]:int(m[1]) for m in re.findall(r'^O (\w+) (-?\d+)',o,re.M)}
# sim value is cycle index sampled at posedge after rise -> constant offset vs model; report diff histogram
import collections
diff=collections.Counter(got[n]-exp[n] for n in exp)
print(json.dumps(dict(outputs=len(exp),sim_outputs=len(got),never_high=sum(v<0 for v in got.values()),diff_hist=dict(diff),
    model_min=min(exp.values()),model_max=max(exp.values()))))
