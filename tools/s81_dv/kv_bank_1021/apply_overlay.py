#!/usr/bin/env python3
"""Bind the off-default KV bank to one actual die slice/leaf without a view alias.
Run on a successor plan/table after the existing G8 overlays. Changes s_3N only.
No physical fit or closure claim: the added bank's slot and regional clocks remain
model obligations before any physical gate/adoption.
"""
import argparse,copy,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--table',type=Path,required=True);p.add_argument('--source-ref',required=True);a=p.parse_args()
plan=json.loads(a.plan.read_text());t=json.loads(a.table.read_text())
b=next(b for b in plan['blocks'] if b['name']=='s_3N');old=b['master'];m=copy.deepcopy(t['masters'][old])
assert m['module']=='ot_s81sl_slice' and not m.get('view'),(old,m.get('view'))
key='dsdv_slice_kv512';assert key not in t['masters']
m.setdefault('params',{})['KV_ENABLE']=1
m['view_note']='UNBOUND successor: actual production D512 KV bank on leaf0; no legacy slice view alias; physical slot/clock/model qualification pending'
m['ref']=a.source_ref;t['masters'][key]=m;b['master']=key
files=['rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_kv_leaf.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_kv_bank.sv']
for f in files:
 t.setdefault('rtl_refs',{}).setdefault(a.source_ref,[]).append(f)
 t.setdefault('prefer',[]).append(a.source_ref+'/'+f)
plan['facts']['kv_bank_source_binding']=dict(instance='s_3N.lf[0].u_lf.g_kv.u_kv',master='ot_s81sl_kv_leaf',source_ref=a.source_ref,parameter='KV_ENABLE=1',status='SOURCE_ONLY_NOT_PHYSICALLY_QUALIFIED',producer='existing leaf VM RD writes; lowering/producer transport must establish actual a_proj rows',row_region=[672,991])
a.plan.write_text(json.dumps(plan,indent=1)+'\n');a.table.write_text(json.dumps(t,indent=1)+'\n')
print('KV_BANK_SOURCE_BIND s_3N leaf0 KV_ENABLE1; all other slices default0; no aliased view')
