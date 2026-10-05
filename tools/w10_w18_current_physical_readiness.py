#!/usr/bin/env python3
"""Source-pinned terminal/current inventory; this audit never admits jobs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

BASE='454f29b8a63b86af6bc37aabd68589cf247adf07'
RECORDS={
 'bf_structure':'results/uarch/w10_baseline_wake/fullmap_r2/readiness.json',
 'q_inventory':'results/uarch/w10_q_elaboration_inventory_r1/inventory.json',
 'q_fit':'results/uarch/w10_final_element_fit_r1/fit.json',
 'root_terminal':'results/physical_abi3/asap7/chip/w18_karb21_final_fail_20261001/corner_sta.json',
 'region_terminal':'results/rtl/w18b_hash_diagnosis/pregionh_ksr_corner_sta.json',
 'region_baseline':'results/uarch/w18_baseline_boundary/corner_scope.json',
 'c8_terminal':'results/physical_abi3/asap7/chip/w18_bf16_c8_dependency_fail_20261001/recovery.json'}

def blob(commit,path):
    return subprocess.check_output(['git','show',commit+':'+path])

def source_join(source,reader):
    rows=[]
    for path,expected in sorted(source.items()):
        if path.startswith('/'):
            rows.append({'path':path,'expected':expected,'scope':'external historical library; not a current repository join'})
            continue
        try:actual=hashlib.sha256(reader(path)).hexdigest()
        except subprocess.CalledProcessError:actual=None
        rows.append({'path':path,'expected':expected,'current_sha256':actual,'matches':actual==expected})
    return rows

def build(records,pins,joins,observation):
    bf=records['bf_structure'];q=records['q_inventory'];root=records['root_terminal'];region=records['region_baseline']
    return {'schema':'w10_w18_current_physical_readiness_v1','source_commit':BASE,'input_pins':pins,
      'current_q_source_join':joins,
      'bf':{'source_commit':bf['source_commit'],'mapped_netlist_sha256':bf['structure']['mapped_netlist_sha256'],
        'structure':bf['structure'],'exactness':bf['exactness'],'measured_synthesis_stdcell_um2':bf['area']['measured_synthesis_stdcell_um2'],
        'physical_admission':False,'contextual_SS_FF_qualified':False,'current_final_LEF_ETMs_qualified':False,
        'next_prerequisites':['625-row fixed50pct complete slot with clock/hold/tap/endcap reserve','actual allpin escape plus contiguous capture/mux site placement','9-group spatial clock/PG and endpoint routes','source-matched neighbor clocks/IO; actual fullsize SSsetup/FFhold, route and extracted power/IR'],
        'retained_failure':'c8 DRT-0255; old wake floorplan 1distinctwake collapsed; neither supplies current timing'},
      'q':{'source':q['source'],'actual_mapped_standard_area_um2':q['actual_mapped_standard_area_um2'],
        'scope':'BF0 NB2 FASTPP WAKE1 XF4 LAT8 MTP6 current elaboration ONLY; full technology map not measured',
        'current_final_LEF_ETMs_qualified':False,'contextual_SS_FF_qualified':False,'physical_admission':False,
        'historical_q_transfer_credit':0,'fit_issues':records['q_fit']['q_final_evidence']['issues'],
        'next_prerequisites':['source-qualified actual Q full technology map incl distinct wake/ICG/ROM count','model reconcile actual full map area/clock/pin budgets against complete wholepoint','same-source Q golden fulllegalshape exactness and wake/reset/drain qualification','admissible full-goal floorplan then contextual SSFF and real extracted abstract']},
      'w18':{'karb21':'TERMINAL_REJECTED_DLOAD_ON_VALID_NO_RESTART','karb22':'TERMINAL_REJECTED_KSREG_NO_RESTART',
        'root_SS_overall_ps':root['setup_ss']['worst_slack_ps'],'root_SS_r2r_ps':root['setup_ss']['worst_reg_to_reg_slack_ps'],
        'root_FF_hold_ps':root['hold_ff']['worst_slack_ps'],
        'region_baseline_SS_overall_ps':region['setup_ss']['worst_slack_ps'],'region_baseline_SS_r2r_ps':region['setup_ss']['worst_reg_to_reg_slack_ps'],
        'region_baseline_FF_hold_ps':region['hold_ff']['worst_slack_ps'],
        'response_boundary':'MODEL_ONLY; 585/524ps cone evidence cannot qualify changed load/hold. Atomic payload/valid/credits/reset and all4port fit/power remain gates.',
        'live_waiter':'3029028 read-only LEF-presence waiter; existence is not source/corner qualification',
        'queued_routes_admitted':[],'die_rebase_admitted':False},
      'observed_host_jobs':observation,
      'next_specific_validation':{'first':'current Q cheap fullmap structure/area evidence after exact source/parameter prerequisite and measured bounded lease; no P&R',
        'physical':'BF fullgoal floorplan/structure validation only after constructive allpin/capture+spatial clockPG fit and wholegeometry binding; CTS/route only after that terminal guard',
        'w18':'model exact atomic boundary/credit and all4port capacity first; no rejected DLV/KSREG retry or legacy die chain'},
      'independent_tasks':['Q/BF source and artifact inventory','read-only retained terminal SSFF extraction','finite allpin/site/clockPG constructive model proof'],
      'actual_dependencies':['wholepoint finite geometry/power budget','source exactness and structural fullmap','constructive local fit and matched IO/clock contracts','measured host lease preserving L0 and other live jobs'],
      'new_jobs':0,'new_Engram_PnR':0,'retired_AGIdocks_all_excluded':True,'physical_admission':False,
      'actual_abstract_validator_available':False,'headline_clock_qualified':False,
      'verdict':'CURRENT_SOURCE_PREREQUISITES_OPEN_NO_ADMISSIBLE_NEW_Q_BF_W18_ROUTE'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--observation',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    records={};pins={}
    for key,path in RECORDS.items():
        raw=blob(BASE,path);records[key]=json.loads(raw);pins[key]={'commit':BASE,'path':path,'sha256':hashlib.sha256(raw).hexdigest()}
    joins=source_join(records['q_inventory']['source']['source_sha256'],lambda path:blob(BASE,path))
    raw=Path(a.observation).read_bytes();o=json.loads(raw);pins['observation']={'sha256':hashlib.sha256(raw).hexdigest()}
    x=build(records,pins,joins,o);Path(a.output).write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
if __name__=='__main__':main()
