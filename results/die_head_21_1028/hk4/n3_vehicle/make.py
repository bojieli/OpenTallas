import copy,json,sys
from pathlib import Path
W=Path(__file__).resolve().parents[4];sys.path[:0]=[str(W/'tools/die_plan'),str(W/'tools/s81_head')]
import schema as S,gen_rtl as G
from head_n3_split_delta import split
p=json.load(open(W/'results/die_head_21_1028/hk4/plan_hk4.json'));q,r=split(p)
out=Path(__file__).parent
orig=copy.deepcopy(p['partition_types']['hd_st_n3']);orig['module']='n3_reference'
q['partition_types']['original']=orig
q['reset']={'release':'local','sync_stages':2};q['clock'].pop('landing_network',None)
texts=[];mods={}
for tn in ['original','hd_st_n3_transit','hd_st_n3_turn']:
 t=q['partition_types'][tn];w,h=t['outline_um'];t['clock']={'tap_um':[w/2,h/2],'tap_pitch_um':100000,'insertion_ps':450};t.pop('count_straps',None)
 # Same local reset in all wrappers, testing the unchanged FT pipeline mechanism.
 t['reset']={'sync_stages':2};P=S.Plan(q);text=G.wrapper(P,tn,G.bus_epochs(P),str(W));mods[tn]=G.parse_leaf_ports(text,t['module']);texts.append(text)
(out/'dut.sv').write_text('\n'.join(texts));(out/'ot_dp_cells.sv').write_text(G.CELLS)
import shutil
shutil.copy(W/'rtl/lib/ot_reset_sync.sv',out/'ot_reset_sync.sv')
head=['`timescale 1ns/1ps','module tb; reg clk=0; always #5 clk=~clk; reg arst_n=0; integer cycle,bitn,seed=73,errors=0;']
for f in orig['ft_slots']:
 n=f['name'];width=f['width'];head += [f'reg [{width}:0] {n}_i;',f'wire [{width}:0] {n}_o, ref_{n}_o;']
for tn,ports in mods.items():
 t=q['partition_types'][tn];conn=[]
 for n,(di,width) in ports.items():
  if n=='clk' or n.startswith('clk_t'):v='clk'
  elif n=='arst_n':v='arst_n'
  elif n.endswith('_o') and tn=='original':v='ref_'+n
  else:v=n
  conn.append(f'.{n}({v})')
 head.append(t['module']+' u_'+tn+'('+','.join(conn)+');')
head+=['initial begin']
for f in orig['ft_slots']:head.append(f"{f['name']}_i='0;")
head+=['repeat(5) @(negedge clk); arst_n=1;', 'for(cycle=0;cycle<400;cycle=cycle+1)begin @(negedge clk);']
for f in orig['ft_slots']:head.append(f"for(bitn=0;bitn<={f['width']};bitn=bitn+1){f['name']}_i[bitn]=$urandom();")
head+=['@(posedge clk); #1; if(cycle>20) begin']
for f in orig['ft_slots']:head.append(f"if({f['name']}_o!==ref_{f['name']}_o)errors=errors+1;")
head+=['end end if(errors)$fatal(1,"N3_SPLIT_FAIL errors=%0d",errors);$display("N3_SPLIT_PASS cycles=400 four_fullwidth_paths=4");$finish;end endmodule']
(out/'tb.sv').write_text('\n'.join(head))
s=(out/'dut.sv').read_text();i=s.index('module ot_s81hd_st_n3_turn')
tail=s[i:];needle='.d(u1_s4_q), .ea(u1_s4_eq)'
assert needle in tail
s=s[:i]+tail.replace(needle,'.d(u1_s3_q), .ea(u1_s3_eq)',1)
(out/'mutant.sv').write_text(s)
