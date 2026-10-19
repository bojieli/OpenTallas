#!/usr/bin/env python3
"""Opt in the IDX-only source-bound256-row collar. No view is admitted here."""
import argparse,copy,gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OLD='ot_hbm_static_cfg_collar'
NEW='ot_hbm_static_cfg_collar_idx256'
SRC='rtl/hbm_accel/host_static_20261015/'+NEW+'.sv'
CAN='rtl/hbm_accel/host_static_20261015/'+OLD+'.sv'

def apply(original):
 c=copy.deepcopy(original);v=c['instances']['col_idx']
 if v['master'] not in (OLD,NEW):raise ValueError('unexpected IDX collar master')
 if any(v['params'].get(k)!=x for k,x in [('PAGE_W',1),('NS',1),('XSER',0)]):raise ValueError('guard only supports actual single stream IDX256 programme space')
 if v['params'].get('AW',12)!=12 or v['ports']['pw_addr']['bits']!=12:raise ValueError('unexpected collar address ABI')
 sinks=[e for e in c['edges'] if e['source'][:2]==['col_idx','pw_addr']]
 expected={'hb_idx__ctl'}|{'hb_idx__qctl_'+q for q in ('SW','SE','NW','NE')}
 if {e['sink'][0] for e in sinks}!=expected or len(sinks)!=5:raise ValueError('all five physical programme consumers must be explicit')
 if any(e['source'][2:]!=[0,8] or e['sink'][3]-e['sink'][2]!=8 for e in sinks):raise ValueError('programme depth is not the proved256-row ABI')
 changed=v['master']!=NEW
 v.update(master=NEW,source=SRC,rtl_deps=[])
 if changed:v['note']+=' | l19: physical programme rows256; page0 and need<=256; out-of-range writes/selection/counts stickyfault without aliased writes; no successful edge changes'
 for s in c['straps']:
  if s.get('inst')=='col_idx':s['master']=NEW
 # No grant/master view substitution: the new source must get independent physical qualification.
 r=dict(layer='l19_idx_collar256',changed=changed,instance='col_idx',master=NEW,source=SRC,
  actual_programme_rows=256,allowed_page=0,maximum_need_rows=256,programme_consumers=[e['sink'] for e in sinks],
  successful_data_added_edges=0,successful_install_added_edges=0,state_bits_added=0,
  canonical_sha256=hashlib.sha256((ROOT/CAN).read_bytes()).hexdigest(),
  successor_sha256=hashlib.sha256((ROOT/SRC).read_bytes()).hexdigest(),
  qualification='SOURCE_ONLY_NEEDS_SYNTH_NATIVE_TTFF_PHYSICAL_REGRANT',
  no_hard_view_admitted=True)
 return c,r

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('inp');p.add_argument('out');p.add_argument('--report',required=True);a=p.parse_args()
 with gzip.open(a.inp,'rt') if a.inp.endswith('.gz') else open(a.inp) as f:c=json.load(f)
 c,r=apply(c);Path(a.out).write_text(json.dumps(c,separators=(',',':'))+'\n');Path(a.report).write_text(json.dumps(r,indent=1)+'\n')
 print('L19_IDX256 source-only; all five programme consumers256rows;0successfuledges')
if __name__=='__main__':main()
