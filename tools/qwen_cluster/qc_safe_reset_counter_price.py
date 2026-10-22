#!/usr/bin/env python3
"""Price replacing co-located final reset pads with static epoch counters.
Diagnostic release-only model. No reset assertion equivalence/adoption claim.
"""
import argparse,json,math
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('plan');p.add_argument('--out',required=True);a=p.parse_args();d=json.loads(Path(a.plan).read_text());rows=[]
for v in d['consumers']:
 n=2*v.get('pad_hops',0)
 if not n:continue
 ff=2 if n==2 else 3+max(1,(n-3).bit_length())
 rows.append(dict(inst=v['inst'],release_edges=n,serial_padding_ff=n,counter_ff=ff,save_ff=n-ff,source_reset_driver=v['driver'],aligned_new_pin_depth=v['aligned_new_pin_depth']))
old=sum(v['serial_padding_ff']for v in rows);new=sum(v['counter_ff']for v in rows)
o=dict(schema='opentallas.cb16.reset_counter_price.v1',diagnostic_only=True,reset_plan_source=d['source'],forward_hops_unchanged=d['mapped_forward_hops'],serial_padding_ff=old,counter_padding_ff=new,padding_ff_saved=old-new,forward_plus_counter_ff=2*d['mapped_forward_hops']+new,added_reset_ff_vs_original=2*d['mapped_forward_hops']+new-d['logical_reset_nodes'],A0_xstn_release_edges=d['A0_xstn_reset_pin_depth'],latest_landing_epoch=d['latest_landing_epoch'],rows=rows,blockers=['release-only equivalence requires long reset transactions and matching clock epochs','counter asserts reset within3edges unlike long shift padding; full cancel/MUT8 semantics unproved','forward relay placement and315um routes are mapped targets, not legalized','counter native timing/clock/reset fanout not physically qualified'])
Path(a.out).write_text(json.dumps(o,indent=1)+'\n');print('RESET_COUNTER_PRICE',old,'->',new,'paddingFF; total',o['forward_plus_counter_ff'],'delta',o['added_reset_ff_vs_original'])
