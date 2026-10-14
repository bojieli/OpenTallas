#!/usr/bin/env python3
"""Bind candidate ACK source pins to actual CTS rectangles in reserved local slots."""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[2];O=R/'results/arch/s81_hrow_reset_ack_1014/physical_candidate';p=json.loads((O/'packet.json').read_text());pins=json.loads((O/'ack_pins.json').read_text());epochs=json.loads((O/'new_epoch_pins.json').read_text());inst={x['instance']:x['reserved_slot'] for x in pins}
def bind(item,key):
 master=item['master'];d=O/'actual_cts'/master
 if not (d/'receipt.json').exists():return False
 receipt=json.loads((d/'receipt.json').read_text());actual=json.loads((d/'pins.json').read_text());name=item[key].rsplit('/',1)[-1];boxes=actual['pins'][name]['boxes'];z=inst[item['instance']];w,h=actual['outline_um'];out=[]
 for b in boxes:
  x0,y0,x1,y1=b['rect_um'];xy=[]
  for x,y in [(x0,y0),(x0,y1),(x1,y0),(x1,y1)]:
   if z['orient']=='MX':y=h-y
   elif z['orient']=='MY':x=w-x
   else:assert z['orient']=='R0'
   xy.append((z['x']+x,z['y']+y))
  out.append({'layer':b['layer'],'master_rect_um':b['rect_um'],'reserved_slot_rect_um':[min(x for x,y in xy),min(y for x,y in xy),max(x for x,y in xy),max(y for x,y in xy)]})
 item.update(actual_cts_contact_rectangles=out,actual_pin_odb_sha256=actual['odb_sha256'],actual_gate_manifest_sha256=receipt['source_binding_manifest_sha256'],actual_successor_mapped_sequential_cells=receipt['mapped_sequential_cells'],actual_successor_distinct_ack_ff=receipt['mapped_distinct_ack_witness_ff'],geometry_status='actual CTS contacts on reserved historical slot, successor route/adoption OPEN',production_clock_driver=None,production_reset_driver=None,global_die_rectangles=None)
 return True
n=sum(bind(x,'source_module_pin') for x in pins);e=sum(bind(x,'source_pin') for x in epochs)
(O/'actual_ack_slot_pin_bindings.json').write_text(json.dumps(pins,indent=2)+'\n');(O/'actual_epoch_slot_pin_bindings.json').write_text(json.dumps(epochs,indent=2)+'\n')
summary={'source_ack_outputs':94,'actual_cts_ACK_contacts_bound':n,'actual_cts_epoch_contacts_bound':e,'total_new_signal_contacts':121,'remaining_new_contacts':121-n-e,'physical_instances_with_cts_receipts':len({x['instance'] for x in pins if 'actual_cts_contact_rectangles' in x}),'status':'Source-bound candidate CTS geometry only; no global producer, route cut inheritance or timing qualification'}
(O/'actual_pin_binding_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(summary)
