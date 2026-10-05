#!/usr/bin/env python3
"""Audit c9's sole selected bank, literal supplies and signal escape obligations."""
import argparse, hashlib, json, re
from bisect import bisect_left, bisect_right
from pathlib import Path
import dsrom_capture_clock_selected_union as C
ROOT=Path(__file__).resolve().parents[1]
def overlap(a,b):
 return max(a[0],b[0])<min(a[2],b[2]) and max(a[1],b[1])<min(a[3],b[3])
def contained(a,b):
 return b[0]<=a[0] and b[1]<=a[1] and b[2]>=a[2] and b[3]>=a[3]
def shapes(lef,name):
 block=re.search(r'  PIN '+name+r'\n(.*?)  END '+name,lef,re.S)[1]
 return [[round(float(v)*1000) for v in row.split()] for row in re.findall(r'RECT ([^;]+);',block)]
def transform(r,cell):
 x,y=cell['bbox_DBU'][:2]
 if cell['orientation']=='MX':r=[r[0],270-r[3],r[2],270-r[1]]
 elif cell['orientation']!='R0':raise ValueError('Unbound orientation')
 return [x+r[0],y+r[1],x+r[2],y+r[3]]
def audit(cells,rails,lef):
 # Index same-net literal rails by centre; never infer external supply connectivity.
 rail_index={}
 for r in rails:
  b=r['bbox_DBU'];rail_index.setdefault((r['net'],(b[1]+b[3])/2),[]).append(b)
 centers={net:sorted(k[1] for k in rail_index if k[0]==net) for net in ('VDD','VSS')}
 pins={n:shapes(lef,n) for n in ('VDD','VSS','A','Y')}
 signal_shapes=0;supply_shapes=0
 for c in cells:
  for n in ('VDD','VSS'):
   for s in pins[n]:
    b=transform(s,c);rr=rail_index.get((n,(b[1]+b[3])/2),[])
    if not any(contained(b,r) for r in rr):raise ValueError('Literal supply gap '+c.get('instance',c.get('proposed_site_ID',''))+' '+n)
    supply_shapes+=1
  for n in ('A','Y'):
   for s in pins[n]:
    b=transform(s,c)
    for net in ('VDD','VSS'):
     yy=centers[net]
     for center in yy[bisect_left(yy,b[1]-9):bisect_right(yy,b[3]+9)]:
      if any(overlap(b,r) for r in rail_index[(net,center)]):raise ValueError('Signal pin overlaps literal supply')
    signal_shapes+=1
 return dict(cells=len(cells),literal_supply_shapes_covered=supply_shapes,signal_pin_shape_count=signal_shapes,signal_ports_requiring_named_escape=2*len(cells),M1_supply_contact_union=True,signal_pin_supply_overlap=False,external_PG_feed_via_or_signal_escape_proven=False)
def build():
 d=C.inputs();m=C.build();hd,_=C.H.H.inputs();lef=hd['cell_LEF.json']['BUFx4_ASAP7_75t_R']
 bank=d['model.json']['selector_additional_core_clock_bank'];cells=d['selector_core_clock_cells.jsonl.gz']
 if len(cells)!=70406:raise ValueError('Selected bank changed')
 if len({c['instance'] for c in cells})!=len(cells):raise ValueError('Duplicate bank instance')
 for c in cells:
  if not contained(c['bbox_DBU'],bank['named_site_bank_bbox_DBU']):raise ValueError('Bank site outside reservation')
 ordered=sorted(cells,key=lambda c:(c['bbox_DBU'][1],c['bbox_DBU'][0]))
 for a,b in zip(ordered,ordered[1:]):
  if overlap(a['bbox_DBU'],b['bbox_DBU']):raise ValueError('Bank cell collision')
 if bank['conflicts_with_known_field_service_cfg_band_selector_rectangles']:raise ValueError('Bank region collision')
 out=dict(schema='DS_C9_SELECTED_BANK_LITERAL_PIN_PG_AUDIT_1',candidate=m['candidate'],source_commit='c9d19ed598077e4a4941c8548273f15deefb8c1a',single_bank=True,unselected_annex_charge_mm2=0,selected_bank_bbox_DBU=bank['named_site_bank_bbox_DBU'],bank=audit(cells,bank['PG_M1_literal_rails'],lef),raw=[])
 for s,inv in enumerate(m['raw_empty_row_correction_site_inventories']):
  raw=d['model.json']['physical_shards'][str(s)]
  out['raw'].append(dict(shard=s,**audit(inv['proposed_sites'],raw['PG_M1_literal_rails'],lef),remaining_cell_sites=inv['remaining_free_sites']))
 out.update(selected_bank_reserved_mm2=m['selected_selector_clock_construction']['reserved_bank_mm2'],whole_reticle_screen_mm2=m['whole_selector_replacement_screen_mm2'],reticle_screen_margin_mm2=858-m['whole_selector_replacement_screen_mm2'],common_colocation_counterfactual_deficit_mm2=m['common_if_all_correction_colocated_deficit_mm2'],selected_raw_rows_eliminate_this_colocation_requirement=True,island_lower_area_remaining_before_tokens_ingress_routes_mm2=m['capture_island_remaining_lower_screen_after_clock_and_identity_before_tokens_VM_routes_mm2'],remaining_proven_global_fit_deficit_mm2=None,
  pin_template_DBU={n:shapes(lef,n) for n in ('A','Y','VDD','VSS')},pin_template_source_sha256=hashlib.sha256(lef.encode()).hexdigest(),
  contextual_PR_prerequisites=['Assign each of the 68614 raw clock relay/pad cells to its source branch and legal station; cell inventory is not a routed tree','Assign 70406 selector-bank buffers to actual core clock sinks and source reset/clock ingress','Construct named M1-to-M8/M9 signal escapes including vias, OBS, PG and mutual occupancy; use actual RC/load/slew and <=25ps matched-clock skew','Bind PG upfeeds/vias and supply current to bank and raw rails; literal abutment coverage alone does not power them','Join full169 identity, scalar ROM slot0 ingress ownership/mux, typed forward hold and consumer-visible positive-credit endpoints to reserved cells','Price resulting cycle changes against accepted source calendar before selected contextual build'],
  scalar_ROM_slot0_ingress_cost_not_yet_contained=True,actual_consumer_deadline=None,physical_fit=False,contextual_PR_admitted=False,SSFF=False,new_jobs=[])
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(),sort_keys=True,indent=2)+'\n')
