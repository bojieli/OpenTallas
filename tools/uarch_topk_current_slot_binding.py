#!/usr/bin/env python3
"""Reconcile complete selector proxy with current parent reservation, no G0 waiver."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess

FULL='aa745a879e20e3db598f7be9345cb7ad3b1d5d2f'
PARENT='d2b3fde765a9cb1b97ec03864dbf7e48f0cf51f4'
POLICY='d4b9a4a6966bf211df81136b3df886a980f4bd36'
PATHS={'full':'results/uarch/topk_balanced_filter_successor_model_20261002/model.json',
       'parent':'results/uarch/dsrom_noECC_complete_parent_map_20261002/r2/model.json',
       'policy':'results/uarch/ds_mtp_agentic_headline_policy_20261002.json'}

def load(repo,commit,path):
    data=subprocess.check_output(['git','show',commit+':'+path],cwd=repo)
    return json.loads(data),dict(commit=commit,path=path,sha256=hashlib.sha256(data).hexdigest())

def reconcile(full,parent,policy):
    rom=[x for x in full['shapes'] if all(x['compiled'][k]==v for k,v in
         {'N':4,'NMAX':2048,'LDW':4,'P':64,'PF':64,'DIG':8}.items())]
    required={x['area']['proposed_source_50pct_proxy_core_mm2'] for x in rom}
    if len(required)!=1:raise ValueError('ambiguous complete ROM selector area')
    need=required.pop();sel=parent['selector'];box=sel['single_full_slot_bbox_DBU']
    width=box[2]-box[0];height=box[3]-box[1]
    if width<=0 or height<=0:raise ValueError('invalid current selector rectangle')
    reserved=width*height/1e12
    if abs(reserved-sel['reserved_rectangle_mm2'])>1e-10:raise ValueError('parent rectangle area mismatch')
    minheight=math.ceil(need*1e12/width)
    if policy['status']!='AGENTIC_MEDIAN_SOURCE_PENDING' or policy['headline_qualified_rate'] is not None:
        raise ValueError('unexpected agentic headline policy')
    return {'schema':'TOPK_CURRENT_SELECTOR_RESERVATION_RECONCILIATION_V1',
      'required_complete_construction_proxy_mm2':need,'current_reserved_rectangle_mm2':reserved,
      'current_old_full_proxy_mm2':sel['full_proxy_mm2'],
      'uncovered_complete_proxy_mm2':max(0,need-reserved),
      'complete_proxy_extra_over_current_charged_proxy_mm2':need-sel['full_proxy_mm2'],
      'current_bbox_DBU':box,'minimum_height_same_width_DBU':minheight,
      'minimum_area_only_bbox_DBU':[box[0],box[1],box[2],box[1]+minheight],
      'minimum_extra_height_DBU':max(0,minheight-height),
      'minimum_bbox_is_not_placement_or_corridor_acceptance':True,
      'area_pass':reserved>=need,'clock_branch_basis':parent['clock'],
      'clock_policy':{'period_ps':833,'SS_setup_uncertainty_ps':60,'FF_hold_uncertainty_ps':25},
      'clock_branch_basis_is_not_selector_stage_timing':True,
      'remaining':['Archimedes accepts complete selector state+logic reservation once, no old-store duplicate credit',
                   'Archimedes checks enlarged rectangle against retained controller, corridor, root/VM routes and clock/PG',
                   'Maxwell prices relocated load/result transport and actual serial caller residence',
                   'source-construction stage arcs + full-context SS setup/FF hold acceptance'],
      'G0':'REFUSE_CURRENT_SLOT_AND_UNCLOSED_CONTEXT','engine_RTL_admitted':False,'PR_admitted':False,
      'MTP_headline':{'policy':'third-party agentic median per-request committed tokens / complete elapsed decode',
                      'numeric_provenance_pending':True,'qualified_rate':None,
                      'local_pooled_tau':'historical sensitivity only; superseded for headline'},
      'new_jobs':0,'PVE2_PVE3':'drain-only'}

def build(repo):
    models={};pins={}
    for key,commit in [('full',FULL),('parent',PARENT),('policy',POLICY)]:
        models[key],pins[key]=load(repo,commit,PATHS[key])
    record=reconcile(models['full'],models['parent'],models['policy']);record['sourcepins']=pins
    return record

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    with a.out.open('x') as f:json.dump(build(a.repo),f,indent=2,sort_keys=True);f.write('\n')
