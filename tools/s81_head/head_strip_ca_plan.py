#!/usr/bin/env python3
"""Produce fresh HK4 CA plan/bind from one reviewed TT/FF clock GRT snapshot.

Initial stage-clock estimates are provisional until emitted START flops are
included in the next GRT. No earlier K/origin table is accepted as input.
"""
import argparse,json,subprocess,sys
from pathlib import Path
W=Path(__file__).resolve().parents[2];T=W/'tools/die_plan';H=W/'tools/s81_head';D=W/'results/die_head_21_1028/hk4'

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('run');a.add_argument('--plan',required=True);a.add_argument('--out',required=True);a=a.parse_args();run=Path(a.run).resolve();plan=Path(a.plan).resolve();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
 def step(name,args):
  with open(out/(name+'.log'),'x') as f:
   rc=subprocess.call([sys.executable]+[str(x) for x in args],cwd=W,stdout=f,stderr=subprocess.STDOUT)
  print(name,'rc',rc,flush=True)
  if rc:raise SystemExit(rc)
 step('proof0',[H/'head_mk_proof_lca.py',run,D/'spine_regions.json',out/'proof0'])
 step('fall_TT',[T/'tap_fall_merge.py',out/'proof0','TT',run/'out_TT/arr_TT.txt','--tree',run/'clk/tree.json','--out',out/'proofT'])
 step('fall_FF',[T/'tap_fall_merge.py',out/'proofT','FF',run/'out_FF/arr_FF.txt','--tree',run/'clk/tree.json','--out',out/'proof'])
 step('physical_ocv',[H/'landed_phase_ocv.py',plan,run,'--tools',T,'--clock-cell','inv2','--core-lat','TT=450,FF=380','--port-taps','--out',out/'physical_ocv.json'])
 step('region_ocv',[H/'head_strip_ocv_regions.py',out/'physical_ocv.json','--table',D/'region_plan/regions_map.json','--regions',D/'spine_regions.json','--out',out/'region_ocv.json'])
 step('plan',[T/'count_align_plan.py',out/'region_ocv.json','--corner','TT_droop-regions_corelat450,FF_droop-regions_corelat380','--sta-proof',out/'proof','--sta-plan',plan,'--sta-clock-cal','spice_edge','--sta-cppr-lca','--sta-clock-ocv','table','--sta-clock-droop','shared','--sta-droop-regions',out/'proof/droop_regions.json','--sta-core-latency-ff','380','--sta-ca-ring',D/'clock_profile/ca_ring_hd_tile_dh20.json','--sta-clock-cell','inv2','--start-tree','clock','--start-clean','width','--mc-chips','2000','--out',out/'plan.json'])
 result=json.load(open(out/'plan.json'))['summary'];iv=result['sta_interval']
 assert result['crossings']==427 and iv['rows']==427,('incomplete HEAD external crossing set',result)
 assert not any(iv.get(k,0) for k in ('missing','unbound','rows_without_measured_fall')),('incomplete physical STA hull',iv)
 assert result['fail']==0 and result['below_100ps']==0,('CA design margin failure',result)
 step('bind',[T/'count_align_bind.py',out/'plan.json','--parts','table','--table',D/'region_plan/regions_map.json','--table-out',out/'regions_ca.json','--out',out/'bind.json','--strap-form','--plan-die',plan,'--straps-out',out/'straps.json'])
 step('emit_start',[T/'start_stage_emit.py','emit',out/'bind.json',out/'proof','--ctree',run/'clk','--plan',plan,'--out',out/'start_stages'])
 (out/'scope.json').write_text(json.dumps({'source':'fresh current clock GRT; no old K/origins','core_budget_ps':{'TT':450,'FF':380},'hd_tile_ring_clock':'actual ca_ring_hd_tile_dh20 per-type profile','stage_clock_scope':'initial estimates; emitted START flops require next measured GRT before freeze','release':'NOT_CLAIMED'},indent=1))
if __name__=='__main__':main()
