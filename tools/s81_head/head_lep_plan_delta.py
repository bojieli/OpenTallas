#!/usr/bin/env python3
"""Candidate source/fault-return delta for the ONE head infra-first event.
Does not overwrite the canonical plan. This is source/port preparation only;
no existing physical view, clock gate or whole-head bind is inherited.
"""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
from gen import latency_table
from schema import Plan


def apply(raw,closure):
 lp=raw['partition_types']['hd_lep0N'];ctl=raw['partition_types']['hd_ctl']
 if lp['contents'][0]['module'] not in ('dsdv_slice_lepw_mu.LP','ot_s81hd_lep0N_core'):
  raise ValueError('head LEP provider changed; re-compose explicitly')
 lp['contents']=[dict(inst='u_core',module='ot_s81hd_lep0N_core',status='new',
  params={'CH_B':"4'b1111"},bind={'ck':'clk','rst_n':'rst_n'},
  note='real current IDX/MU landing/four safe8+lnland, head-only no-repair memory; no fake nested module')]
 lp['sources']=closure['physical_sources']
 # Keep clocks, reset, all existing pins and data lanes untouched here; the
 # infra-first batch must re-evaluate source demand and deliver START/reset.
 common=dict(width=1,kind='ctl',window_um=[1074.432,1094.544],layers=['M4','M6'],order='lsb_low')
 for typ,name,direction,face,leaf in [(lp,'fault_o0','out','E','u_core.fault_o0'),
                                     (ctl,'lep_fault_i','in','W','u_core.lep_fault_i')]:
  bus=dict(name=name,dir=direction,face=face,leaf=leaf,**common)
  old=[b for b in typ['buses'] if b['name']==name]
  if old and old!=[bus]:raise ValueError('conflicting existing fault bus '+name)
  if not old:typ['buses'].append(bus)
 port=dict(id='head_lep_fault_return__0',src=dict(part='lep0N',bus='fault_o0'),
           dst=dict(part='ctl',bus='lep_fault_i'),width=1,kind='ctl')
 lane=dict(id='head_lep_fault_return',ports=[port['id']])
 for key,item in [('ports',port),('lanes',lane)]:
  old=[x for x in raw[key] if x['id']==item['id']]
  if old and old!=[item]:raise ValueError('conflicting existing '+item['id'])
  if not old:raw[key].append(item)
 raw['latency']=dict(lanes=latency_table(Plan(raw)))
 return raw

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--base',type=Path,required=True);ap.add_argument('--closure',type=Path,required=True)
 ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 if a.base.resolve()==a.out.resolve():raise SystemExit('refusing canonical in-place mutation')
 raw=apply(json.loads(a.base.read_text()),json.loads(a.closure.read_text()))
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(raw,indent=2)+'\n')
 print('HEAD_LEP_DELTA candidate written; +1live fault return, source provider replaced; memory cycles0, native internal ages require composition; no adoption')
