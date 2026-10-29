"""Map the old bind5 bench regional clocks to their measured physical base taps.
This diagnostic intentionally quantifies the unrepresented multi-tap spread.
"""
import json,re,sys
from pathlib import Path
base=Path(sys.argv[1]);out=Path(sys.argv[2]);top=(base/'tok-kv-1-1028/b48n/top_s/qwen_kvsys_bound_top.sv').read_text();regions=re.findall(r'input wire clk_region_(\w+);',top);assert len(regions)==128
rows={};summary={}
for corner in ('TT','FF'):
 proof=json.load(open(base/f'die-kv-15-1028/proofF_fb/tap_arrivals_{corner}.json'));taps={t['port']:t for t in proof['taps']}; rr=[]
 for region in regions:
  port=f'clk_region_{region}';tp=f't_{region}__clk';t=taps[tp];alltap=[v for k,v in taps.items() if k.startswith(f't_{region}__clk')];assert alltap
  phases={k:t[k] for k in ('late_ps','early_ps','fall_late_ps','fall_early_ps')}
  spread={k:dict(min=min(v[k] for v in alltap),max=max(v[k] for v in alltap),span=max(v[k] for v in alltap)-min(v[k] for v in alltap)) for k in phases}
  rr.append(dict(top_port=port,region=region,physical_base_tap=tp,phase_ps=phases,physical_tap_count=len(alltap),all_physical_taps=[v['port'] for v in alltap],unrepresented_physical_spread_ps=spread))
 rows[corner]=rr;summary[corner]=dict(regional_clocks=len(rr),physical_taps=sum(x['physical_tap_count'] for x in rr),max_region_rise_late_span_ps=max(x['unrepresented_physical_spread_ps']['late_ps']['span'] for x in rr),max_region_fall_late_span_ps=max(x['unrepresented_physical_spread_ps']['fall_late_ps']['span'] for x in rr))
 bench=(out/'tb_kvslice.sv').read_text()
 # Replace the existing 29 TT stage waveform constants with the same selected corner.
 stages=json.load(open(out/'phase_profile.json'))['profiles']
 if corner=='FF':
  for old,new in zip(stages['TT'],stages['FF']):
   assert old['clock_port']==new['clock_port']
   for edge in ('rise','fall'):
    a=old[f'{edge}_late_ps']/1000;b=new[f'{edge}_late_ps']/1000
    text=f"{old['clock_port']} <= #({a:.9f})";replace=f"{old['clock_port']} <= #({b:.9f})";assert bench.count(text)==1;bench=bench.replace(text,replace)
 decl=[]
 for x in rr:
  n='bench_'+x['top_port'];v=x['phase_ps'];decl.append(f"    reg {n}=0;\n    always @(ck_core) begin\n        if (ck_core) {n} <= #({v['late_ps']/1000:.9f}) 1'b1;\n        else {n} <= #({v['fall_late_ps']/1000:.9f}) 1'b0;\n    end\n")
  old=f".{x['top_port']}(ck_core)";assert bench.count(old)==1;bench=bench.replace(old,f".{x['top_port']}({n})")
 bench=bench.replace('    qwen_kvsys_bound_top dut (',f'    // Measured bind5 {corner} base-tap clock coupling; full multi-tap spread remains unrepresented.\n'+''.join(decl)+'    qwen_kvsys_bound_top dut (',1)
 (out/f'tb_kvslice_regional_{corner}.sv').write_text(bench)
doc=dict(form='old_bind5_regional_stage_clock_contract',basis='Matching proofF_fb measured base tap t_REGION__clk maps to existing top clk_region_REGION; full delays retained without period folding. Stage clocks retain matching-corner actual SDF A/Y phases.',qualification='Functional timing diagnostic only. One regional input clocks every physical tap of that partition in this old top, so its measured multi-tap spatial spread cannot be represented. Full physical G5 needs explicit physical clock pins and source windows, not a scalar regional phase.',no_compile=True,summary=summary,regions=rows)
(out/'regional_clock_contract.json').write_text(json.dumps(doc,indent=1));print(json.dumps(summary))
# Preserve the exact old top's many-to-one clock aliases in the contract.
physical_parts=sorted({t['part'] for t in proof['taps']});assert len(physical_parts)==160
aliases={};blocks={}
for part in physical_parts:
 m=re.search(r'^\s*(\w+)\s*(?:#\([^\n]*\)\s*)?'+re.escape(part)+r'\s*\((.*?)\);',top,re.S|re.M);assert m,part
 clock=re.search(r'\.clk\((clk_region_\w+)\)',m[2]);assert clock,part
 aliases[part]=clock[1];blocks[part]=m.group(0)
pc=[p for p in physical_parts if aliases[p]!='clk_region_'+p];assert len(pc)==32 and all(x.startswith('pc_') for x in pc)
joined=(out/'qwen_kvsys_bound_top.sv').read_text();mh=re.search(r'module qwen_kvsys_bound_top\s*\((.*?)\);',joined,re.S);newports=['clk_region_'+p for p in pc];joined=joined[:mh.end(1)]+', '+', '.join(newports)+joined[mh.end(1):];k=joined.index(';')+1;joined=joined[:k]+'\n'+''.join('    input wire '+n+';\n' for n in newports)+joined[k:]
for part in pc:
 old=blocks[part];new,n=re.subn(r'\.clk\('+aliases[part]+r'\)',f'.clk(clk_region_{part})',old);assert n==1
 assert joined.count(old)==1;joined=joined.replace(old,new)
(out/'qwen_kvsys_bound_top_regional160.sv').write_text(joined)
allrows={}
for corner in ('TT','FF'):
 pr=json.load(open(base/f'die-kv-15-1028/proofF_fb/tap_arrivals_{corner}.json'));taps={t['port']:t for t in pr['taps']};rr=[]
 for part in physical_parts:
  tp=f't_{part}__clk';t=taps[tp];group=[x for x in pr['taps'] if x['part']==part];keys=('late_ps','early_ps','fall_late_ps','fall_early_ps')
  rr.append(dict(physical_part=part,old_top_input=aliases[part],successor_top_input='clk_region_'+part,physical_base_tap=tp,phase_ps={k:t[k]for k in keys},physical_taps=len(group),unrepresented_spread_ps={k:max(v[k]for v in group)-min(v[k]for v in group)for k in keys}))
 allrows[corner]=rr
 bench=(out/f'tb_kvslice_regional_{corner}.sv').read_text();decl=[]
 for x in rr:
  if x['physical_part'] not in pc:continue
  n='bench_'+x['successor_top_input'];v=x['phase_ps'];decl.append(f"    reg {n}=0;\n    always @(ck_core) begin\n        if (ck_core) {n} <= #({v['late_ps']/1000:.9f}) 1'b1;\n        else {n} <= #({v['fall_late_ps']/1000:.9f}) 1'b0;\n    end\n")
 bench=bench.replace('    qwen_kvsys_bound_top dut (',''.join(decl)+'    qwen_kvsys_bound_top dut (\n'+''.join(f'        .clk_region_{p}(bench_clk_region_{p}),\n'for p in pc),1);(out/f'tb_kvslice_regional160_{corner}.sv').write_text(bench)
doc['actual_aliases']=aliases;doc['separated_pc_inputs']=newports;doc['all160physical_parts']=allrows;doc['physical_taps_covered']=sum(x['physical_taps']for x in allrows['TT']);assert doc['physical_taps_covered']==1920
(out/'regional_clock_contract.json').write_text(json.dumps(doc,indent=1));print('Actual32PC/PHYaliases separated in successor only;160basephases/1920tapinventory, no compile.')
