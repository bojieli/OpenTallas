import sys,json,copy
from pathlib import Path
r=Path(__file__).resolve().parent;sys.path.insert(0,str(r/'src/tools/die_plan'))
import schema as S,reset_tree as RT,taps
_original_grid=RT._S_TAP_GRID
RT._S_TAP_GRID=lambda P,tn:taps.explicit_tap_sites(P,tn) if P.types[tn].get('clock',{}).get('tap_mode')=='explicit' else _original_grid(P,tn)
out=r/'reset_r6w7_miter';out.mkdir(exist_ok=True);text=[];ns=[]
for j,tn in enumerate(('kv3_sys_SD','kv3_sys_SD_v1')):
 pp=r/'plan_of_record/plan_c_sd_r6w7_candidate.json';p=json.load(open(pp));P=S.Plan(p,str(pp));t=RT.for_type(P,tn)
 tapsout=['rst_n_t'+str(i) for i in range(RT.consumer_count(t))]
 locals=p['partition_types'][tn]['clock']['landing_local_resets']
 for mode,T in [('dut',t),('mut',copy.deepcopy(t))]:
  if mode=='mut':next(n for n in T['relays'] if n['q']=='rst_n_t0')['d']='rst_root_n'
  text+=['module '+mode+str(j)+'(input wire clk,arst_n,start_i,output wire['+str(len(tapsout)+len(locals)-1)+':0] o);']+RT.rtl_lines(T)
  for i,n in enumerate(locals):text+=['wire local'+str(i)+';ot_dp_rrelay copy'+str(i)+'(.clk(clk),.d('+n['raw']+'),.q(local'+str(i)+'));']
  text+=['assign o={'+','.join(tapsout+['local'+str(i) for i in range(len(locals))])+'};endmodule']
 ns.append(len(tapsout)+len(locals))
tb=['module tb;reg clk=0;always #5 clk=~clk;reg rst=0,st=0;integer i,m=0,seen=0;reg[31:0] rng=32\'h13579bdf;']
for j,n in enumerate(ns):
 for mode in ('dut','mut'):tb+=['wire['+str(n-1)+':0] '+mode+str(j)+'q;'+mode+str(j)+' u'+mode+str(j)+'(clk,rst,st,'+mode+str(j)+'q);']
tb+=['initial begin repeat(20)@(negedge clk);for(i=0;i<12000;i=i+1)begin rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};rst=(i%107<13)?0:rng[4];st=rng[7];@(posedge clk);#1;']
for j,n in enumerate(ns):tb+=['if(dut'+str(j)+'q !== {'+str(n)+'{dut'+str(j)+'q[0]}})m=m+1;if(dut'+str(j)+'q!==mut'+str(j)+'q)seen=seen+1;']
tb+=['@(negedge clk);end $display("R6W7_RAW_EQUAL cycles=%0d mismatches=%0d mutant=%0d",i,m,seen);if(m||!seen)$fatal(1,"raw copy epoch mismatch");$finish;end endmodule']
(out/'trees.sv').write_text('\n'.join(text));(out/'tb.sv').write_text('\n'.join(tb))
