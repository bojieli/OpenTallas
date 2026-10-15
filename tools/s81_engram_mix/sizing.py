#!/usr/bin/env python3
"""Compose immutable MIX4 mapped-root receipts without claiming placement closure."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MULT={'ot_s81_engram_mul4':8,'ot_s81_engram_chunk8':12,'ot_s81_engram_add8':4,
      'ot_s81_engram_norm':2,'ot_s81_engram_sum':3,'ot_s81_engram_mix_control':1,
      'ot_s81_engram_signed_sqrt':1,'ot_s81_engram_sigmoid':1}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('evidence',type=Path);a=p.parse_args();r=a.evidence.resolve()
 records={}
 for area in sorted(r.glob('**/area.json')):
  d=json.loads(area.read_text());manifest=json.loads((area.parent/'sources.json').read_text())
  assert d['status']=='PASS' and not d['unmapped_cells'],area
  for path,want in manifest.items():
   assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==want,('stale source',area,path)
  records[d['top']]=d|{'receipt':str(area.relative_to(ROOT)),'manifest':str((area.parent/'sources.json').relative_to(ROOT))}
 rows=[]
 for top,n in MULT.items():
  d=records[top];rows.append({'top':top,'copies_per_cluster':n,'area_um2':d['cell_area_um2'],
   'cells':d['cell_count'],'receipt':d['receipt'],'mapped_flop_cells':sum(v for k,v in d['cells'].items() if 'DFF' in k)})
 shell=records['ot_s81_engram_mixq'];master=records['dsfd_engram_mix4_c']
 assert shell['excluded_blackbox_modules']==['ot_s81_engram_mix']
 assert master['excluded_blackbox_modules']==['ot_s81_engram_mixq']
 arithmetic=sum(x['copies_per_cluster']*x['area_um2'] for x in rows)
 cluster=arithmetic+shell['cell_area_um2'];total=4*cluster+master['cell_area_um2']
 census=json.loads((r/'current/census_mixq/census.json').read_text())
 res={'schema':'opentallas.s81.mix4.mapped_sizing.v1','status':'MAPPED_AREA_ONLY',
  'scope':'Actual independently mapped default-parameter root composition, no cross-root flatten optimization; no placement, CTS, routing or slot fit claim.',
  'root_rows':rows,'arithmetic_um2_per_copy':arithmetic,'mixq_shell_um2':shell['cell_area_um2'],
  'per_copy_cell_area_um2':cluster,'mix4_top_shell_um2':master['cell_area_um2'],'mix4_total_cell_area_um2':total,
  'per_copy_rtl_ff_bits':census['total_flop_bits'],'roots_per_copy':len(census['flop_bits_by_clock']),
  'largest_per_copy_rtl_root_ff_bits':max(census['flop_bits_by_clock'].values()),
  'bare_area_lower_bound_at_60pct_um2':total/.6,
  'existing_arithmetic_leaf_outline_um':[181.44,129.6],
  'placement_plan':{'representative_leaf':'ot_s81_engram_mul4','gate_outline_um':[181.44,129.6],
   'native_pin_contract':'physical/s81_die_pins/v20_engram_arithmetic/ot_s81_engram_mul4.json',
   'remaining':['actual placement/CTS of representative maximum-area root',
    'root-local valid/control and broadcast register placement must close <=500um per bit',
    '33-root per-copy arrangement and 4-copy/top-shell placement',
    'VM E 20R/4W exact native face alignment and station inventory',
    'all actual native root views TT/FF/DRC and fixed-calendar proof']}}
 (r/'summary.json').write_text(json.dumps(res,indent=1)+'\n');print(json.dumps({k:v for k,v in res.items() if k not in ('root_rows','placement_plan')},indent=1))
if __name__=='__main__':main()
