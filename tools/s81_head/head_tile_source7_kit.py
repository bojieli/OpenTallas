#!/usr/bin/env python3
"""Build the SOURCE7 HEAD tile candidate with explicit control-copy area price.

Consumes the portable SOURCE7 source plan/sidecar, preserving its qualified START
export copy and registered raw-reset aliases. No clock/CTS or route is launched.
The initial kit is synth/place only; its clock groups must be rebuilt from the
new mapped sinks before CTS. One source event, no interface/pin/steady-cycle edit.
"""
import argparse,copy,hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/die_plan'),str(ROOT/'tools/s81_head')]
import gen_phys
from head_start_reset_aliases import patch_rtl
from head_tile_relay_kit import install

def build(source,out):
 source,out=Path(source).resolve(),Path(out).resolve()
 if out.exists():raise ValueError('fresh output directory required: '+str(out))
 path=source/'source7/source_plan.json';side_path=source/'source7/source_sidecar.json'
 plan=json.load(open(path));side=json.load(open(side_path));t=plan['partition_types']['hd_tile']
 if not t.get('clock',{}).get('landing_origin_export_copy'):raise ValueError('SOURCE7 FWD_COPY1 is required')
 original=copy.deepcopy(t);t['landing_control_status_copy']=True
 # This is the existing physical tile contract, not the generic non-tile450/380 budget.
 t['clock'].update(insertion_ps=525.,insertion_ff_ps=425.25,insertion_basis='native hd_tile525/425.25 physical contract; fresh clock assignment required after candidate placement')
 # Exactly one count-aligned data ring is in this tile; the per-ring manifest below must confirm it.
 t['cells']=int(t.get('cells',0))+8
 candidate=path.with_name('source_plan_statuscopy.json');candidate.write_text(json.dumps(plan,indent=1)+'\n')
 kits=gen_phys.write_phys(plan,out,ROOT,types=['hd_tile'],trial=True,plan_path=candidate,landing=side)
 kit=Path(kits[0]);wrapper=out/'_rtl'/f"{t['module']}.sv"
 rows=t.get('reset_start_raw_exports',[])
 text=patch_rtl(wrapper.read_text(),rows)
 if '.CONTROL_STATUS_COPY(1)' not in text or 'FWD_COPY(1)' not in text:raise ValueError('generated physical source lost a required opt-in')
 wrapper.write_text(text);(kit/'rtl'/wrapper.name).write_text(text)
 # Source-only helpers reproduce the already-qualified existing-stage layout.
 receipt=install(kit,ROOT/'results/head_tile_source_1029/targets_copy_result.tsv',ROOT/'tools/s81_head/head_tile_banks.tcl')
 manifest=json.load(open(out/'_rtl/gen_clock_landings.json'))
 rings=manifest['reset_placements']['hd_tile'];ff=sum(v.get('status_copy_flops',0) for v in rings.values() if isinstance(v,dict))
 if ff!=8:raise ValueError('status-copy price must be exactly8extraFF for this SOURCE7 tile, got'+str(ff))
 report=dict(source_plan_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),source_sidecar_sha256=hashlib.sha256(side_path.read_bytes()).hexdigest(),
  retained_export_copy=True,raw_reset_exports=len(rows),added_status_flops=ff,added_cycles=0,clock_source_budget_ps=dict(TT=525.,FF=425.25),
  corridor=receipt,physical_clock_assignment='NOT RUN: actual new sinks required before CTS',route_qualified=False)
 (out/'source7_tile_receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
 return kit

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('--out',required=True);a=p.parse_args();build(a.source,a.out)
