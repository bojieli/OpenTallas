#!/usr/bin/env python3
"""Strict selection from preserved receipts, not a route launcher."""
from pathlib import Path
import argparse
import json
import math
import re
ROOT=Path(__file__).resolve().parents[1]/'results/rtl/dsrom_qpipe_terminal_20261003'


def sta_wns(text):
    values=re.findall(r'^OT_WNS\s+([^\s]+)\s*$',text,re.M)
    if len(values)!=1:
        raise ValueError('exactly one STA WNS required')
    value=float(values[0])
    if not math.isfinite(value):
        raise ValueError('finite STA WNS required')
    return value


def assess(root=ROOT):
    r=root/'R_cap0'
    physical=json.loads((r/'physical.json').read_text())
    receipt=json.loads((r/'launcher_receipt.json').read_text())
    macro=json.loads((r/'macro_gate.json').read_text())
    final=json.loads((r/'final_macro_extract.json').read_text())
    context=json.loads((root/'S82_physical_contract.json').read_text())
    for corner in ('SS','FF'):
        if (r/('final_'+corner+'.rc')).read_text().strip()!='0':
            raise ValueError('STA invocation did not complete')
    ss=sta_wns((r/'final_SS.log').read_text())
    ff=sta_wns((r/'final_FF.log').read_text())
    d=physical['design']
    params=d['parameters']
    if not (physical['flow_completed'] and receipt['status']=='DRIVER_RETURNED'):
        raise ValueError('terminal physical receipt required')
    if not (d['clock_period_ns']==0.833 and d['clock_uncertainty_ns']==0.06
            and d['clock_uncertainty_hold_ns']==0.025):
        raise ValueError('clock policy changed')
    actual=(r/'macro_alignment_actual.log').read_text()
    aligned='OT_MACRO_TRACK_ASSERT PASS label=POST_TAPCELL macros=4 pins_checked=1152 offtrack=0 max_offset_nm=0.0 no_track_grid=0' in actual
    schema_macro=physical['place_and_route']['memory_macros']['macros'][0]
    geometry=(final['instance_count']==context['ROM_macro']['macros_per_pair']==4
              and len(final['def_components'])==4
              and schema_macro['words']==context['ROM_macro']['rows']==4096
              and schema_macro['bits_per_word']==context['ROM_macro']['word_bits']==274)
    native_closure=(ss>=0 and ff>=0 and physical['status']=='pass'
                    and d['closed'] and d['signal_integrity_clean'] and d['drc']==0
                    and macro['verdict']=='PASS' and aligned and geometry)
    live=json.loads((root/'R_cap1_live_receipt.json').read_text())
    bf=json.loads((root/'BF_c8_historical_assessment.json').read_text())
    return {
        'schema':'dsrom-qpipe-selection-terminal-v1',
        'selected_q_abstract':None,'selected_BF_abstract':None,
        'fewest_qualified_added_cycles':None,
        'reason':'no candidate presently passes full functional/performance/physical hierarchy',
        'R_cap0':{'source_commit':physical['git']['commit'],'terminal_utc':physical['completed_at'],
            'launcher_pid':receipt['pid'],'launcher_exit':receipt['exit_code'],
            'flow_completed':physical['flow_completed'],'added_cycles':1+params['QP_CAP']+params['QP_P1'],
            'SS_setup_WNS_ps':ss,'FF_hold_WNS_ps':ff,
            'ORFS_reported_hold_WNS_ps':d['hold_wns_ns']*1000,
            'separate_FF_check_is_authoritative_for_FF':True,
            'DRC':d['drc'],'integrity_violations':d['signal_integrity_violations'],
            'native_closed':native_closure,'verdict':'REJECTED_NO_RESCUE' if not native_closure else 'PHYSICAL_ONLY_NOT_ADOPTED',
            'cell_area_um2':d['area_um2'],'cell_count':d['cells'],
            'actual_macro_alignment_pass':aligned,'S82_ROM_geometry_matches':geometry,
            'source_corrected_config_decoder':False,'independent_full_arithmetic_oracle_gate':False,
            'actual_adoption_performance_gate':False,
            'qualified_abstract_delivered':False},
        'R_cap1':{'source_commit':physical['git']['commit'],'added_cycles':3,
            'launcher_pid':live['pid'],'receipt_status':live['status'],
            'observed_stage':'5_2_route detailed routing, iteration18,870 DRC in live snapshot',
            'terminal_verdict':None,'qualified_abstract_delivered':False},
        'BF':{'verified_live_launcher':None,'checked_hosts':['local','ot-epyc1tb','ot-agidock128','ot-pve1'],
            'historical_latest_retained_job':bf['bf16_job'],'historical_host':bf['host'],
            'historical_failure':bf['failure'],'historical_abstract_available':bf['qualified_final_abstract'],
            'historical_failure_is_current_S82_verdict':False,
            'new_pipelined_BF_gate_or_route_launched':False},
        'S82_source_commit':'8c6d5bd7521a1a7788cd6babda624d0b5bceac36',
        'new_route_or_rescue_jobs':0,'live_Rcap1_untouched':True,
        'adoption':False,'stage_die_rate_rows_regenerated':False,
    }


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.write_text(json.dumps(assess(),sort_keys=True,indent=2)+'\n')
if __name__=='__main__':main()
