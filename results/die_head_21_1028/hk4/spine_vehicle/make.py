import copy,json,sys,shutil,re
from pathlib import Path
W=Path(__file__).resolve().parents[4];sys.path[:0]=[str(W/'tools/die_plan'),str(W/'tools/s81_head')]
import schema as S,gen_rtl as G,kit_istations as I
from head_spine_strip_delta import run
raw=json.load(open(W/'results/die_head_21_1028/hk4/plan_n3_raw.json'));new,_,_=run(raw)
out=Path(__file__).parent
for end in [False,True]:
 tag='end' if end else 'normal';D=out/tag;D.mkdir(exist_ok=True)
 base='hd_spn_end' if end else 'hd_spn';q=copy.deepcopy(new);orig=copy.deepcopy(raw['partition_types'][base]);orig['module']='spine_reference';q['partition_types']['reference']=orig
 q['reset']={'release':'local','sync_stages':2};q['clock'].pop('landing_network',None)
 mods={};texts=[]
 for tn in ['reference',base,'hd_spn_wshim','hd_spn_eshim']:
  t=q['partition_types'][tn];w,h=t['outline_um'];t['clock']={'tap_um':[w/2,h/2],'tap_pitch_um':100000,'insertion_ps':450};t['reset']={'sync_stages':2}
  P=S.Plan(q);text=G.wrapper(P,tn,G.bus_epochs(P),str(W));mod=t['module'];F=D/(mod+'.sv');F.write_text(text)
  (D/'kit_rtl.json').write_text(json.dumps({'bound_module':mod,'files':[str(F)]}));(D/'plan.json').write_text(json.dumps(q));I.main([str(D/'plan.json'),tn,str(D)])
  text=F.read_text();mods[tn]=G.parse_leaf_ports(text,mod);texts.append(text)
 (D/'dut.sv').write_text('\n'.join(texts));(D/'ot_dp_cells.sv').write_text(G.CELLS)
 for f in ['rtl/lib/ot_reset_sync.sv','rtl/dsrom_sys/s81_head/ot_s81hd_spo.sv','rtl/dsrom_sys/s81_head/ot_s81hd_spr.sv']:shutil.copy(W/f,D/Path(f).name)
 head=['`timescale 1ns/1ps','module tb; reg clk=0; always #5 clk=~clk; reg arst_n=0; integer cycle,bitn,errors=0;']
 ports=mods['reference']
 for n,(di,width) in ports.items():
  if n=='arst_n' or n.startswith('clk'):continue
  bits=int(re.search(r'\d+',width).group())+1 if width else 1
  head.append(('reg ' if di=='input' else 'wire ')+f'[{bits-1}:0] {n};')
  if di=='output':head.append(f'wire [{bits-1}:0] ref_{n};')
 for n in ['xw_o','xe_o','bw_i','be_i']:head.append(f'wire [565:0] inner_{n};')
 for tn in ['reference',base]:
  conn=[]
  for n,(di,width) in mods[tn].items():
   if n.startswith('clk'):v='clk'
   elif n=='arst_n':v='arst_n'
   elif tn=='reference':v='ref_'+n if di=='output' else n
   elif n in ['xw_o','xe_o','bw_i','be_i']:v='inner_'+n
   else:v=n
   conn.append(f'.{n}({v})')
  head.append(q['partition_types'][tn]['module']+' u_'+tn+'('+','.join(conn)+');')
 for bus,side,direction in [('xw_o','w','out'),('bw_i','w','in'),('xe_o','e','out'),('be_i','e','in')]:
  head.append('ot_s81hd_spn_'+side+'shim u_shim_'+bus+'(.clk(clk),.arst_n(arst_n),.link_i('+('inner_'+bus if direction=='out' else bus)+'),.link_o('+(bus if direction=='out' else 'inner_'+bus)+'));')
 head+=['initial begin']
 for n,(di,width) in ports.items():
  if di=='input' and n!='arst_n' and not n.startswith('clk'):head.append(n+"='0;")
 head+=['repeat(5) @(negedge clk); arst_n=1;','for(cycle=0;cycle<1000;cycle=cycle+1)begin @(negedge clk);']
 buses={b['name'] for b in orig['buses']}
 for n,(di,width) in ports.items():
  if di!='input' or n=='arst_n' or n.startswith('clk'):continue
  bits=int(re.search(r'\d+',width).group())+1 if width else 1
  head.append(f'for(bitn=0;bitn<{bits};bitn=bitn+1){n}[bitn]=$urandom();')
  if n in buses:head.append(f'{n}[565]=1; {n}[512]=(cycle%64==0); {n}[513]=1; {n}[514]=(cycle%9==0);')
 head+=['@(posedge clk);#1;if(cycle>180)begin']
 for n,(di,width) in ports.items():
  if di=='output':head.append(f'if({n}!==ref_{n})begin errors=errors+1;if(errors<5)$display("MISMATCH {n} cycle=%0d",cycle);end')
 head+=['end end if(errors)$fatal(1,"SPINE_STRIP_FAIL errors=%0d",errors);$display("SPINE_STRIP_PASS cycles=1000");$finish;end endmodule']
 (D/'tb.sv').write_text('\n'.join(head))
 text=(D/'dut.sv').read_text();i=text.index('module ot_s81hd_spn_wshim');tail=text[i:]
 needle='.d(link_s0_q), .ea(link_s0_eq)';assert needle in tail
 text=text[:i]+tail.replace(needle,'.d(link_i[564:0]), .ea(link_i[565])',1)
 (D/'mutant.sv').write_text(text)
print(out)
