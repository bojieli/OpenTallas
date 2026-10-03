#!/usr/bin/env python3
"""Typed primary record wiring; no storage, arbitration, codec or release policy."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/w2_nc6_primary_record_helper_20261003'
RTL=ROOT/'rtl/experimental/w2_nc6_primary_record_helper_20261003/ot_w2_nc6_primary_record_view.sv'
MAP=json.loads((OUT/'inputs/canonical_map.json').read_text())
ROWS=MAP['rows']
# Source names, output names and exact total record widths, in low-to-high chunk order.
RECORDS=[('request_holder','held_request',335,1),('read_query','held_read_query',297,1),('write_query','held_write_query',41,1),('read_delivery','held_read_delivery',300,1),('prepared_write','journal',87,9),('correction_context','correction',96,8),('query_pipeline','query_pipeline',65,6),('write_selection','write_selection',5,6),('protected_scheduler','scheduler',79,1),('round_robin','round_robin',3,1)]

def slots(name,instance):
 return [r for r in ROWS if r['record']==name and r['instance']==instance]

def check_mapping():
 assert len(ROWS)==219 and [r['index'] for r in ROWS]==list(range(219))
 assert len(MAP['primary'])==182 and len(MAP['secondary'])==37
 assert set(MAP['primary']).isdisjoint(MAP['secondary']) and set(MAP['primary'])|set(MAP['secondary'])==set(range(219))
 for name,_,width,count in RECORDS:
  for i in range(count):assert sum(r['payload_bits'] for r in slots(name,i))==width and all(r['index'] in MAP['primary'] for r in slots(name,i))

def values(payload,clean,ce,bad,enabled=True):
 if len(payload)!=219 or any(type(p)!=int or p<0 or p>=1<<44 for p in payload):raise ValueError('219 current44 payloads required')
 for x in [clean,ce,bad]:
  if type(x)!=int or not 0<=x<1<<219:raise ValueError('219 status bits')
 outputs={};qualified=clean&~(ce|bad)
 for name,out,width,count in RECORDS:
  v=ok=0
  for i in range(count):
   acc=shift=0;good=True
   for r in slots(name,i):
    acc|=(payload[r['index']]&((1<<r['payload_bits'])-1))<<shift;shift+=r['payload_bits'];good &= bool((qualified>>r['index'])&1)
   v|=acc<<(width*i);ok|=int(good)<<i
  outputs[out]=v if enabled else 0;outputs[out+'_clean']=ok if enabled else 0
 mask=sum(1<<i for i in MAP['primary'])
 outputs['primary_clean']=int(enabled and (qualified&mask)==mask)
 outputs['primary_ce']=int(enabled and bool(ce&mask))
 outputs['primary_bad']=int(enabled and bool(bad&mask))
 return outputs

def source():
 check_mapping();ports=['input wire [9635:0] current_payload','input wire [218:0] current_clean,current_ce,current_bad']
 for _,name,width,count in RECORDS:ports.extend([f'output wire [{width*count-1}:0] {name}',f'output wire [{count-1}:0] {name}_clean'])
 ports.append('output wire primary_clean,primary_ce,primary_bad')
 lines=['`timescale 1ps/1ps','// Default-off typed wire view of existing 182/219 sealed primary records.', '// CURRENT status comes from same-word codec seal/padding checks; no cached clean.', '// No new state, normal release, repair, count credit or owner retirement is implemented.', 'module ot_w2_nc6_primary_record_view #(parameter bit OPT_PROTECTION=0) (',',\n'.join(' '+p for p in ports),');','generate if (OPT_PROTECTION) begin:g_enabled','wire [218:0] qualified = current_clean & ~(current_ce | current_bad);']
 for name,out,width,count in RECORDS:
  for i in range(count):
   rs=slots(name,i);pieces=[f'current_payload[{44*r["index"]} +: {r["payload_bits"]}]' for r in reversed(rs)]
   rhs=pieces[0] if len(pieces)==1 else '{'+', '.join(pieces)+'}'
   lines.extend([f'// {name}[{i}] global words '+','.join(str(r['index']) for r in rs),f'assign {out}[{width*i} +: {width}] = {rhs};',f'assign {out}_clean[{i}] = '+ ' & '.join(f'qualified[{r["index"]}]' for r in rs)+';'])
 mask=sum(1<<i for i in MAP['primary']);lines.extend([f"localparam [218:0] PRIMARY_MASK = 219'h{mask:055x};",'assign primary_clean = (qualified & PRIMARY_MASK) == PRIMARY_MASK;','assign primary_ce = |(current_ce & PRIMARY_MASK);','assign primary_bad = |(current_bad & PRIMARY_MASK);','end else begin:g_disabled'])
 for _,name,_,_ in RECORDS:lines.extend([f"assign {name} = '0;",f"assign {name}_clean = '0;"])
 lines.extend(["assign primary_clean=1'b0; assign primary_ce=1'b0; assign primary_bad=1'b0;",'end endgenerate','endmodule'])
 return '\n'.join(lines)+'\n'

def model():
 check_mapping()
 return {'schema':'w2.nc6.primary_record_wire_helper.v1','source_commit':MAP['source_commit'],'canonical_source_sha256':MAP['source_sha256'],'canonical_map_sha256':hashlib.sha256((OUT/'inputs/canonical_map.json').read_bytes()).hexdigest(),'default_off':True,'scope':'combinational typed record reconstruction/current integrity reduction; no primary controller, normal/exceptional FSM or hardware adoption','total_words':219,'primary_words':182,'secondary_words':37,'coded_inventory_bits':15768,'new_state_bits':0,'new_memory_ports':0,'new_handshakes':0,'new_queued_debts':0,'added_pipeline_edges':0,'wire_records':[{'source':n,'output':o,'width':w,'instances':c,'global_indices':[[r['index'] for r in slots(n,i)] for i in range(c)]} for n,o,w,c in RECORDS],'status':'same decoder CURRENT release_clean plus no CE/bad; caller joins secondary37 before normal permit','cost':'Existing primary wire aliases/integrity reduction refactored. No free timing claim: physical loaded182-input clean/CE/bad and per-record fanout remain part of10cb current clean gate, not duplicate allocation. No added state or macro architecture. Contextual SSFF unqualified.','integration':'Nash sole primary owner; replace generic get_record reads by exact width views, wire current codec P/clean/CE/invalid. OPT_PROTECTION follows existing OPT_EXACT. Keep all state/writers/held-ready/utility repair FSM unchanged. No source install by Hubble.'}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--emit-rtl',type=Path);p.add_argument('--model',type=Path);a=p.parse_args()
 if a.model:a.model.write_text(json.dumps(model(),indent=2)+'\n')
 if a.emit_rtl:a.emit_rtl.write_text(source())
 if not a.emit_rtl and not a.model:print(json.dumps(model(),indent=2))
