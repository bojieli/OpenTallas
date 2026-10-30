"""Selected-consumer KV measured clock provider preparation. No RTL/data/K rewriting."""
import json,re,sys,math,hashlib
from pathlib import Path
R=Path(__file__).parent;sys.path.insert(0,str(R/'tools/die_plan'));import die_sta_related as D
B=json.load(open(R/'nativeB_full.json'));T=833.;assert B['period_ps']==T
V=(R/'ctree.v').read_text();drv={};aliases=dict(re.findall(r'\bassign\s+(\S+)\s*=\s*(\S+)\s*;',V))
for master,name,body in re.findall(r'^\s*(\w+)\s+(\S+)\s*\((.*?)\);',V,re.M|re.S):
 pins=dict(re.findall(r'\.(\w+)\s*\(\s*(\S+?)\s*\)',body))
 if 'A'in pins and 'Y'in pins:
  assert master.startswith(('CKINV','INV','BUF')),master
  assert pins['Y'] not in drv
  drv[pins['Y']]=(pins['A'],int('INV'in master),name,master)
cache={}
def graph(net,seen=()):
 if net=='root':return (0,0,0)
 if net in cache:return cache[net]
 assert net not in seen,('cycle',net)
 if net in aliases:ans=graph(aliases[net],seen+(net,))
 else:
  assert net in drv,('missing driver',net)
  src,inv,name,master=drv[net];p,n,b=graph(src,seen+(net,));ans=(p^inv,n+inv,b+1-inv)
 cache[net]=ans;return ans
# Preserve immutable bind JSON insertion order, as the existing fixture does.
order=list(B['regions']);index={p:i for i,p in enumerate(order)}
TB=(R/'tb.sv').read_text();records=[];cases={}
for c,mode in [('TT','late'),('FF','early')]:
 meta,taps=D.load_taps(R,c);meta,taps=D.apply_clock_cal(meta,taps,c,'inv','spice_cell',proof=R);cases[c]={}
 for i,reg in enumerate(order):
  z=B['regions'][reg]
  if z['virtual']:
   tap='__st__'+reg[3:];actual=taps[tap]['measured_port']
   # Exactly both literal stage instances must have the same current clk.
   assert len(re.findall(r'\b[rs]_v'+str(i)+r'\s*\(\.clk\(clk\)',TB))==2,(i,reg)
   parent=z['parent'];ip=index[parent];ps=('v'+str(ip)+'_start') if B['regions'][parent]['virtual'] else 'rs_'+parent;pr=('v'+str(ip)+'_raw') if B['regions'][parent]['virtual'] else 'rraw_'+parent
   assert re.search(r'\bs_v'+str(i)+r'\([^;]*\.p_start\('+re.escape(ps)+r'\)',TB),(i,'START graph mismatch')
   assert re.search(r'\br_v'+str(i)+r'\([^;]*\.d\('+re.escape(pr)+r'\)',TB),(i,'RAW graph mismatch')
  else:
   tap=B['start_ports'][z['tree_port']]['capture'] if z['tree_port'] else 't_'+reg+'__clk';actual=tap
   assert '.clk_region_'+reg+'(clk)' in TB,reg
  q=taps[tap];parity,ni,nb=graph(actual)
  assert parity==0,('non-true clock provider cannot assume root-positive',tap,actual,ni,nb)
  rise=float(q[mode+'_ps']);fall=float(q['fall_'+mode+'_ps'])
  assert 0<T/2+fall-rise<T,(reg,'invalid duty',rise,fall)
  cases[c][reg]=dict(rise_delay_ps=rise,fall_delay_ps=fall,source=tap,measured_port=actual,inverters=ni,buffers=nb,polarity='root-positive',sta_mode=mode)
  if c=='TT':records.append(dict(index=i,region=reg,virtual=z['virtual'],native_port=None if z['virtual'] else 'clk_region_'+reg,expected_origin=B['regions'][reg]['n_nominal'],edge_fall=z['edge_fall']))
for c,case in cases.items():
 bad=[]
 for reg,z in B['regions'].items():
  if z['parent'] is None:continue
  a=case[z['parent']];b=case[reg]
  step=(math.ceil((a['rise_delay_ps']-b['fall_delay_ps']-T/2)/T-1e-10)+3 if z['edge_fall'] else math.ceil((a['rise_delay_ps']-b['rise_delay_ps'])/T-1e-10)+2)+z['pad']
  want=z['n_nominal']-B['regions'][z['parent']]['n_nominal']
  if step!=want:bad.append(dict(region=reg,step=step,wanted=want,parent=z['parent'],rise_a=a['rise_delay_ps'],rise_b=b['rise_delay_ps'],fall_b=b['fall_delay_ps']))
 assert not bad,(c,'measured clockcase does not reproduce actual bind START steps',bad[:3])
 print(c,'clockcase',len(case),'J mismatches',len(bad),bad[:2])
(R/'clock_provider_map_prep.json').write_text(json.dumps(dict(scope='Measured physical clock INPUT-tap provider; selected canonical per-master spice_cell, not internal COREclock/PMA closure',period_ps=T,records=records,cases=cases,phase_formula='all absolute measured delays retained; idealfall833/2, actualgraph true polarity proved; no modulo phase orKchange',case_global=True),indent=1)+'\n')
# Immutable adapter; the replay owner changes clock INPUT connections only.
lines=['`timescale 1ps/1fs','module kv_nativeB_clock_provider #(parameter integer CASE=0) (input wire root, output reg [1687:0] clocks);',"initial begin clocks='0; if(CASE!=0 && CASE!=1) $fatal(1,\"clock provider CASE must be whole TTlate0 or FFearly1\"); end"]
for q in records:
 i=q['index'];reg=q['region'];tt=cases['TT'][reg];ff=cases['FF'][reg]
 lines.extend([f'// {i}: {reg}',f'generate if(CASE==0) begin: g_tt_{i}',f"always @(posedge root) clocks[{i}] <= #({tt['rise_delay_ps']:.6f}) 1'b1;",f"always @(negedge root) clocks[{i}] <= #({tt['fall_delay_ps']:.6f}) 1'b0;",f'end else begin: g_ff_{i}',f"always @(posedge root) clocks[{i}] <= #({ff['rise_delay_ps']:.6f}) 1'b1;",f"always @(negedge root) clocks[{i}] <= #({ff['fall_delay_ps']:.6f}) 1'b0;",'end endgenerate'])
lines.extend(['endmodule',''])
(R/'kv_nativeB_clock_provider.sv').write_text('\n'.join(lines))
# Integration text is isolated from the original fixture and does not touch
# ports, K, original fclk/fstart assigns, native control or raw/reset wiring.
patched=TB.replace('`timescale 1ps/1ps','`timescale 1ps/1fs').replace('always begin #416 clk=1;#417 clk=0;end','always begin #416.5 clk=1;#416.5 clk=0;end')
assert patched!=TB
patched=patched.replace('module tb;','module tb;\nwire [1687:0] physical_clocks; kv_nativeB_clock_provider #(.CASE(0)) physical_clock_provider(.root(clk),.clocks(physical_clocks));\n',1)
counts=dict(native=0,virtual=0)
for q in records:
 i=q['index']
 if q['virtual']:
  for prefix in ['r_v','s_v']:
   old=prefix+str(i)+'(.clk(clk)';new=prefix+str(i)+f'(.clk(physical_clocks[{i}])';assert patched.count(old)==1,(i,prefix);patched=patched.replace(old,new)
  counts['virtual']+=1
 else:
  old='.'+q['native_port']+'(clk)';new='.'+q['native_port']+f'(physical_clocks[{i}])';assert patched.count(old)==1,q['native_port'];patched=patched.replace(old,new);counts['native']+=1
(R/'tb_physical_clock_inputs_only.sv').write_text(patched)
meta=json.load(open(R/'clock_provider_map_prep.json'));meta['schema']='opentallas.nativeB.measured_clock_provider.v1';meta['binding_order']='nativeB_full.regions immutable insertion order (not sorteddepth, not3*depth)';meta['adapter_clock_connections']=counts;meta['forwarded_clock']='Original bound assign fclk_out=clk untouched; inherits sender native input provider waveform';meta['forwarded_start']='Original bound FSTART wires and original native+virtual START/raw RTL unchanged, regenerated by exact source clocks';meta['unmapped_upstream_inputs']=['clk_core original root clock; no fabricated tap delay','clk_clk_phy original fixture clock assumption, no new PHY/seven-root physical qualification','new SD seven primary roots may replicate original region waveform only as explicit replay assumption'];meta['source_cohort']='KV nativeB_full portable POR f1ba+SDR52/R6W7/seven-root controls; old measured clockprovider cohort mapping only, not newer E0/AHUB/currentseven-root physical qualification';meta['input_source']='exact833ps period and50%duty416.5ps TBsource; outputs retain absolute flight delay, no modulo';meta['consumer']='authority src/tools/die_plan/die_sta_related.py load_taps/apply_clock_cal(inv,spice_cell)';meta['cohort_files']={n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ['nativeB_full.json','tap_arrivals_TT.json','tap_arrivals_FF.json','mesh.json','ctree.v','tools/die_plan/die_sta_related.py','tb.sv','controls.sv']};meta['guards']=dict(all1687_exact_source_J_steps_match_bind_both_cases=True,all1688_ctree_positive_polarity=True,all1528_original_virtual_RAW_START_parents_match_bind=True,independent_phase_or_K_changes=False,internal_core_tree_or_new_SD_physical_qualification=False)
(R/'clock_provider_map.json').write_text(json.dumps(meta,indent=1)+'\n')
print('PROVIDER_READY',counts,'allcasesJ0/parity0/sourcegraphmatch')
