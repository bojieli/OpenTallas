"""Build the real normal S81 head-spine kit RTL and smallest station exactness vehicle.

Usage: python3 tools/s81_head/spine_kit.py OUTPUT_DIRECTORY
Then submit OUTPUT_DIRECTORY/run.sh through ot-run. Internal delays come from
this checkout's plan; no plan fields are edited on disk. End-spine closure and
physical timing remain separate gates.
"""
from pathlib import Path
import json,sys,shutil,re,os
ROOT=Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0,'tools/die_plan');import gen_rtl as G,schema as S,kit_istations as I
out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
p=json.load(open('physical/die_plan/s81_head/die_plan.json'));t=p['partition_types']['hd_spn'];t['sources']=['rtl/dsrom_sys/s81_head/ot_s81hd_spo.sv','rtl/dsrom_sys/s81_head/ot_s81hd_spr.sv']
for c in t['contents']:c['bind']={'ck':'clk','rst_n':'rst_n'}
P=S.Plan(p);text=G.wrapper(P,'hd_spn',G.bus_epochs(P),str(Path('.').resolve()));mod=t['module'];(out/(mod+'.sv')).write_text(text);(out/'reference.sv').write_text(text.replace('module '+mod+' (','module reference (').replace('endmodule : '+mod,'endmodule : reference'))
(out/'plan.json').write_text(json.dumps(p));(out/'ot_dp_cells.sv').write_text(G.CELLS)
for f in ['rtl/lib/ot_reset_sync.sv']+t['sources']:shutil.copyfile(f,out/Path(f).name)
fl=[out/(mod+'.sv'),out/'ot_dp_cells.sv',out/'ot_reset_sync.sv',out/'ot_s81hd_spo.sv',out/'ot_s81hd_spr.sv']
(out/'kit_rtl.json').write_text(json.dumps({'bound_module':mod,'files':[str(f) for f in fl]}))
(out/'kit_rtl.f').write_text('\n'.join(str(f) for f in fl)+'\n')
I.main([str(out/'plan.json'),'hd_spn',str(out)])
mut=(out/(mod+'.sv')).read_text();old='.iw(bw_i_is6_q)';assert old in mut;mut=mut.replace(old,'`ifdef HD_SPINE_MUTANT\n        .iw(bw_i_is5_q)\n`else\n        '+old+'\n`endif\n',1);(out/(mod+'.sv')).write_text(mut)
ports=G.parse_leaf_ports(text,mod);buses={b['name']:b for b in t['buses']};delay={e['conn'][4:]:len(e['regs_um']) for e in t['internal_stations']}
def ident(n):return n
head=['`timescale 1ns/1ps','module tb;','reg clk=0; always #5 clk=~clk;','reg arst_n=0; integer cycle=0; integer mismatches=0; integer seed=117;']
con=[];refcon=[]
for n,(direction,w) in ports.items():
 if n.startswith('clk'):con.append('.'+n+'(clk)');refcon.append('.'+n+'(clk)');continue
 if n=='arst_n':con.append('.arst_n(arst_n)');refcon.append('.arst_n(arst_n)');continue
 W=int(re.search(r'\d+',w).group(0))+1 if w else 1
 if n in buses:
  b=buses[n];incoming=b['dir']=='in';head.append(('reg ' if incoming else 'wire ')+f'[{W-1}:0] {n};');con.append(f'.{n}({n})')
  d=delay.get(n,0)
  if incoming:
   if d:
    head.append(f'reg [{W-1}:0] ref_{n}_pipe [0:{d-1}]; integer k_{n}; always @(posedge clk) begin ref_{n}_pipe[0]<={n}; for(k_{n}=1;k_{n}<{d};k_{n}=k_{n}+1)ref_{n}_pipe[k_{n}]<=ref_{n}_pipe[k_{n}-1]; end')
    refcon.append(f'.{n}(ref_{n}_pipe[{d-1}])')
   else:refcon.append(f'.{n}({n})')
  else:
   head.append(f'wire [{W-1}:0] ref_{n};');refcon.append(f'.{n}(ref_{n})')
   if d:
    head.append(f'reg [{W-1}:0] ref_{n}_pipe [0:{d-1}]; integer k_{n}; always @(posedge clk) begin ref_{n}_pipe[0]<=ref_{n}; for(k_{n}=1;k_{n}<{d};k_{n}=k_{n}+1)ref_{n}_pipe[k_{n}]<=ref_{n}_pipe[k_{n}-1]; end')
 else:
  # Pure FT slots: same input words in both copies, no internal-station effect.
  incoming=direction=='input';head.append(('reg ' if incoming else 'wire ')+f'[{W-1}:0] {n};');con.append(f'.{n}({n})')
  if incoming:refcon.append(f'.{n}({n})')
  else:head.append(f'wire [{W-1}:0] ref_{n};');refcon.append(f'.{n}(ref_{n})')
head.append(mod+' dut('+','.join(con)+');');head.append('reference refdut('+','.join(refcon)+');')
head+=['integer bitn;','initial begin']
for n,(di,w) in ports.items():
 if di=='input' and not n.startswith('clk') and n!='arst_n':head.append(n+"='0;")
head+=['repeat(5) @(negedge clk); arst_n=1;','for(cycle=0;cycle<3000;cycle=cycle+1)begin','@(negedge clk);']
for n,(di,w) in ports.items():
 if di!='input' or n.startswith('clk') or n=='arst_n':continue
 W=int(re.search(r'\d+',w).group(0))+1 if w else 1
 head.append(f'for(bitn=0;bitn<{W};bitn=bitn+1){n}[bitn]=$urandom(seed);')
 if n in buses:
  head.append(f'{n}[565]=1; {n}[512]=(cycle%64==0); {n}[513]=1; {n}[514]=(cycle%9==0);')
head+=['@(posedge clk); #1; if(cycle>180)begin']
for n,(di,w) in ports.items():
 if di!='output':continue
 d=delay.get(n,0);ref=f'ref_{n}_pipe[{d-1}]' if d else f'ref_{n}'
 head.append(f'if({n} !== {ref})begin mismatches=mismatches+1; if(mismatches<5)$display("MISMATCH cycle=%0d port={n}",cycle);end')
head+=['end end','if(mismatches)$fatal(1,"SPINE_LOCKSTEP_FAIL mismatches=%0d",mismatches);','$display("SPINE_LOCKSTEP_PASS cycles=3000");$finish;','end','endmodule']
(out/'tb.sv').write_text('\n'.join(head)+'\n')
(out/'run.sh').write_text('''#!/bin/bash
set -uo pipefail
D=$(cd "$(dirname "$0")" && pwd)
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
cd "$D"
for mode in good mutant; do
 args=(); [ "$mode" = mutant ] && args=(-DHD_SPINE_MUTANT)
 verilator --binary --timing -Wno-fatal --top-module tb -j 8 --Mdir "obj_$mode" "${args[@]}" tb.sv ot_s81hd_spn.sv reference.sv ot_dp_cells.sv ot_reset_sync.sv ot_s81hd_spo.sv ot_s81hd_spr.sv > "build_$mode.log" 2>&1 || exit 2
 "./obj_$mode/Vtb" > "run_$mode.log" 2>&1; rc=$?
 tail -5 "run_$mode.log"
 if [ "$mode" = good ]; then [ "$rc" = 0 ] || exit 3; else [ "$rc" != 0 ] && grep -q SPINE_LOCKSTEP_FAIL "run_$mode.log" || exit 4; echo MUTANT_CAUGHT; fi
done
''')
print(out)
