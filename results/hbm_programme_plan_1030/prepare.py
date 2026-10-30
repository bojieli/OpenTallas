#!/usr/bin/env python3
"""Required programme plan-stage recipe: actual posttap obstacles -> frozen cell homes before GEN."""
import argparse,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/die_plan'));import core_infra_plan as CP,core_infra as CI
ap=argparse.ArgumentParser();ap.add_argument('--baseline',required=True);ap.add_argument('--technology',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();out=pathlib.Path(a.out)
assert not out.exists(),'Use a fresh candidate; never overwrite a failed/approved plan'
s=json.load(open(a.baseline));t=json.load(open(a.technology));assert s['module']=='ot_hnx_fused_host_program';assert any(o['name'].startswith('TAP_TAPCELL')for o in t['obstacles']),'Actual posttap fixed obstacle inventory is mandatory'
new,report=CP.legalize_slice(s,t);assert set(new['cell_placements'])=={'mp_isl0_ck0','mp_isl0_rst0'}
assert new['islands']==s['islands']and new['pushdown']==s['pushdown']and new['latency']==s['latency']
out.mkdir(parents=True);(out/'ot_hnx_fused_host_program.json').write_text(json.dumps(new,indent=1)+'\n');(out/'legalization.json').write_text(json.dumps(report,indent=1)+'\n');(out/'master_core_infra.tcl').write_text(CI.emit_tcl(new));print('PLAN_PREP frozen2cellhomes, allTAP/ports/masters/island preserved; parentreview beforeGEN/physical',report['max_displacement_um'])
