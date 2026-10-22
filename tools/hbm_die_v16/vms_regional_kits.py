#!/usr/bin/env python3
"""Project the existing three-root VM glue into native-first physical kits.

No hardware or schedule change. Existing registered reach hops cross the
lane-aligned seams; all three roots remain related and all paths are timed.
"""
import copy,json,re
from pathlib import Path
import vms_glue_kit_specs as K
import gen_vms_glue_tiles as G
ROOT=Path(__file__).resolve().parents[2]
RTL='rtl/hbm_accel/generic/vm/static/'

def make(k):
 s=copy.deepcopy(K.spec(k,K.M[k],'_g7s'))
 m=G.rmap(k); c=G.M[k]
 def reg(*keys):
  return next((m[x] for x in keys if x in m),1)
 top=f'hfd_hgi_vms_glue_{k}_t3'; name=f'hfd_hgi_vms_glue_{k}_g8r'
 s.update(name=name,top=top,clock='multiple_cts_roots',clock_port='clk',clock_ports=['clk','clk_s','clk_n'],orfs_vars={})
 s['sources']=[RTL+'hfd_hgi_vms_glue_tiles_r3.sv',RTL+'hfd_hgi_vms_glue_lr.sv']+s['sources']
 face=K.M[k]['ring']; items=[(p,dict(K.ports(K.M[k]['top']))[p]) for p in s['pins'][face]]
 for clock,target in [('clk_s',290.0),('clk_n',1265.0)]:
  total=sum(w for _,w in items); cumulative=K.MARGIN; candidates=[]
  for i,(_,width) in enumerate(items):
   candidates.append((abs(cumulative-target),i));cumulative+=(K.H-2*K.MARGIN)*width/total
  items.insert(min(candidates)[1],(clock,1))
 ranges,density=K.lay(K.H,items);s['pins'][face]=[p for p,_ in items];s['pin_ranges'].update(ranges);s['pin_density_per_um'][face]=round(density,3)
 domains={key:dict(ratio=[1,1],ports=[port],inputs=[],outputs=[]) for key,port in [('core','clk'),('s','clk_s'),('n','clk_n')]}
 def put(p,d,r):domains[['s','core','n'][r]]['inputs' if d=='input' else 'outputs'].append(p)
 for p,d,w in G.ports(k,c):
  if p=='clk':continue
  if p=='rst_n':r=reg('T:rst_l0')
  elif (mch:=re.fullmatch(r'b([0-7])_(\w+)',p)):
   bank,n=mch.groups();dep=G.bank_depth(n)
   r=reg(f'T:{n}_s0:b{bank}') if d=='input' else reg(f'T:{n}_pin:b{bank}',f'T:{n}_s{dep-1}:b{bank}')
  elif (mch:=re.fullmatch(r'(?:c?cw)_(?:in|out)_l([0-7])',p)):r=reg('S:band:l'+mch[1])
  elif p.endswith('_h') or p in ('ring_tx_enable','ring_tx_source'):r=1
  elif p in dict(G.client_ins(c)):r=reg(f'T:{p}_g_s0','T:bank_enable_g_s0')
  elif p in dict(G.client_outs(c)):r=reg(f'T:{p}',f'T:{p}_g_s{G.DC-2}')
  else:raise ValueError('Unassigned boundary port '+p)
  put(p,d,r)
 s['clock_entry_domains']=domains
 s['pin_hook_before_flops']=['tools/hbm_die_v16/vms_relay_lattice.tcl','tools/hbm_die_v16/vms_regional_fence.tcl']
 s['pre_dpl_extra']=['tools/hbm_die_v16/vms_relay_lattice_release.tcl','tools/hbm_die_v16/vms_regional_fence_release.tcl']
 s['structural_change']='Three related geometric roots with existing registered seam hops. No data or reset edge change; unchanged 648 x 1555.2 outline.'
 s['safe_design_checklist']={
 '1_pins':'Existing pin flops and per-port relay chains retained; boundary domains follow actual first/last RTL clock.',
 '2_reach':'Original g7 relay lattice retained; measured lane-aligned seams at 580.1 and 976 um. Existing registered hops cross seams; placed reach remains required.',
 '3_fanout':'Original bounded g7 kept copies and reset forest retained; mandatory native max 32 and role audit before layout.',
 '4_depth':'No combinational arithmetic or decode changes.',
 '5_storage':'Original finite rings and landing/relay registers retained; no added storage.',
 '6_floorplan':'Unchanged 648 x 1555.2 pin-bound outline and bank/lane port ordering; no squeeze.',
 '7_clock':'Three related roots, all inter-region paths timed with canonical hook; actual TT/FF pin spread <=80 ps required.',
 '8_schedule':'Zero added edges, identical static calendar. Actual full-width positive and missing-root causal evidence required.'}
 benches=[]
 for mut in ['pos','cks','ckn']:
  b=dict(name=f'{k}_{mut}',cmd=f'VMS_KEEP_OBJECTS=1 bash tools/hbm_die_v16/run_vms_glue_t3_equiv.sh {k.upper()} {mut} {{RUN}}/bench',expect='pass' if mut=='pos' else 'fail',threads=8,peak_ram_gb=32)
  witness=f'results/rtl/vm_glue_1018/g8r/bench/{k.upper()}{mut}.sim.log'
  if mut=='pos':b.update(pass_regex=f'^VMS_GLUE_T3_EQUIV {k.upper()} PASS checks=[1-9][0-9]* errors=0$',pass_witness=witness)
  else:b.update(fail_regex=f'^VMS_GLUE_T3_EQUIV {k.upper()} FAIL checks=[1-9][0-9]* errors=[1-9][0-9]*$',fail_witness=witness)
  benches.append(b)
 s['job'].update(owner='CODEX-HBM-SVGSMH-2000',branch='codex/hbm-vm-regions-2225-1021',tag='g8r',benches=benches,record_to=f'results/rtl/ref_tile/{name}',views_to=f'physical/ref_tile/{name}/views')
 return s

if __name__=='__main__':
 out=ROOT/'physical/ref_tile_specs/vm_regions';out.mkdir(parents=True,exist_ok=True)
 for k in ['sw','nw']:
  s=make(k);p=out/(s['name']+'.json');p.write_text(json.dumps(s,indent=1)+'\n');print(p.relative_to(ROOT))
