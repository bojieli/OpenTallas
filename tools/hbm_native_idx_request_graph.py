#!/usr/bin/env python3
"""Actual retained/port/macro graph; requests only, no invented die slots."""
import argparse,collections,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--census',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
r=json.loads((a.census/'receipt.json').read_text());m=json.loads((a.census/'retained.json').read_text())['modules'];masters={}
for name,x in m.items():
 if name.startswith('$') and not 'ot_hbm_idx_' in name and not 'ot_hdc_v41x_sel_' in name:continue
 ports={k:{'direction':v['direction'],'bits':len(v['bits'])} for k,v in x.get('ports',{}).items()}
 masters[name]={'logical_ports':ports,'logical_pin_count':sum(v['bits'] for v in ports.values()),'physical_view_accepted':False}
mac={}
for f in r['source_sha256']:
 if not f.startswith('physical/asap7_memory_macros') or not f.endswith('.v'):continue
 lef=Path(f).with_suffix('.lef');s=lef.read_text();size=re.search(r'SIZE\s+(\S+)\s+BY\s+(\S+)\s*;',s)
 name=Path(f).stem;w,h=map(float,size.groups());mac[name]={'catalog_lef':str(lef),'width_um':w,'height_um':h,'outline_um2':w*h,'instances':sum(x['type']==name for x in r['blackbox_macros'])}
state={k:v+r['inferred_memory_bits_by_write_clock'].get(k,0) for k,v in r['clock_ff_bits'].items()}
per_scorer={}
for q in range(4):
 prefix=f'ot_hbm_idx_parent_cut_native/gstack[{q}].scorer/'
 bb=[x for x in r['blackbox_macros'] if x['instance'].startswith(prefix)]
 per_scorer[str(q)]={'ready_leaves':sum(x['type']=='ot_hbm_idx_hslice_ready_native' for x in bb),'line_sram_macros':sum(x['type']!='ot_hbm_idx_hslice_ready_native' for x in bb)}
x={'source_sha256':r['source_sha256'],'profile':'native4scorers NS4/NK4/IH32/NB4; selectorK512; orderedmax8/newest','per_scorer':per_scorer,'source_clock_entries':sorted(set(state)|{v for x in r['blackbox_macros'] for v in x['clock']}),'retained_bits_including_inferred_buffers_by_clock':state,'actual_blackbox_instances':r['blackbox_macros'],'masters':masters,'catalog_macros':mac,'macro_outline_sum_um2':sum(v['outline_um2']*v['instances'] for v in mac.values()),'related_legacy_hslice_outline_um':[172.8,103.68],'ready_leaf_required_count':2048,'related_leaf_outline_lower_bound_um2':36691771.392,'scorer_leaf_only_rectangle_request_um':[2764.8,3317.76],'fresh_ready_leaf_nominal_sinks':15335,'fresh_ready_leaf_physical_accepted':False,'actual_driver_abi_assigned':False,'assigned_slots':[],'physical_period_or_slew_proven':False,'functional_bench_period_reference_ps':832,'functional_clock_scope':'commonphase only; coherent external entries need actual CTS/seam/reset/lease proof','reset_scope':'single parent rst_n; actual leaf reset acknowledgments and internal per-consumer synchronization; no parent active-clock-stop/drain lease qualification','physical_parent_closed':False}
a.out.write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({'clock_entries':len(x['source_clock_entries']),'macro_outline_sum_um2':x['macro_outline_sum_um2'],'per_scorer':per_scorer}))
