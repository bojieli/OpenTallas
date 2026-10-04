#!/usr/bin/env python3
"""Source-only composition of the existing x-need proposal; launches nothing."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'results/uarch/dsrom_xneed_s82_source_join_20261003'

def model(root=ROOT):
    inputs={}
    for entry in json.loads((root/'source_inputs.json').read_text()):
        data=(root/entry['archive']).read_bytes()
        if hashlib.sha256(data).hexdigest()!=entry['sha256']:raise ValueError('source archive changed')
        inputs[(entry['commit'],entry['path'])]=data
    def source(suffix):
        hits=[v for (c,p),v in inputs.items() if p.endswith(suffix)]
        if len(hits)!=1:raise ValueError('ambiguous source input')
        return hits[0].decode()
    q=source('ot_v41_rom_elem_w10.sv');pair=source('ot_v41_pair_w17w10.sv')
    field=source('ot_v41_field_w17w10_sys.sv');top=source('ot_v41_rt_die_l20_c8.sv')
    required=['ot_v41_walk2_w10 #(.N(NSEG)) u_nw', 'for (k = N - 1; k >= 0; k = k - 1) if (live[k] && k > c)',
              'if (hit) begin', '{n_run, n_q, n_b, n_c, n_j} <= n_nx;', 'wire n_step = hit;']
    if any(t not in q for t in required):raise ValueError('source control-loop contract changed')
    if ('ot_v41_rom_elem_w10 #(' not in pair or 'ot_v41_pair_w17w10 #(' not in field
        or 'output wire [ROM_FBW-1:0] rom_fb' not in top or 'QP_NEED_LOOKAHEAD' in pair):
        raise ValueError('source hierarchy changed')
    proposal=json.loads(source('dsrom_qpipe_xneed_lookahead_20261003/model.json'))
    s82=json.loads(source('dsrom_s82_token_pricing_20261003/model.json'))
    count=s82['q_only_pairs']
    if count+s82['BF_pairs']!=s82['field_pairs_per_die']:raise ValueError('S82 ownership count mismatch')
    c=proposal['construction'];cost=proposal['cost'];lat=proposal['latency']
    if c['accepted_beat_II_cycles']!=1 or c['fill_cycles_increment']!=0 or lat['new_added_cycles_per_qop']!=0:
        raise ValueError('lookahead added latency/II changed')
    cell=Decimal(str(cost['combined_incremental_cell_area_reserve_um2']))*count/Decimal(1000000)
    placed=Decimal(str(cost['placed_area_at_50pct_um2']))*count/Decimal(1000000)
    margin=Decimal(str(s82['screen_margin_mm2']))
    return {'schema':'dsrom-xneed-s82-current-source-join-v1',
      'parent_source':'124c889c364678c238a06cea1d63af88727d8060','S82_pin':'8c6d5bd7521a1a7788cd6babda624d0b5bceac36',
      'parent_top':'ot_v41_rt_die_l20_c8','field_model':'ot_v41_field_w17w10_sys','pair':'ot_v41_pair_w17w10',
      'element':'ot_v41_rom_elem_w10','external_field_boundary':True,'lookahead_installed_in_parent':False,
      'recurrence':{'accept':'hit; not offered xs_v alone','update':'accepted beat chooses exact successor; stalled beat holds state/facts',
         'source_priority_feedback_present':True,'restart':'same n_more/c_live/fF0/fF1 source restart; empty go invalidates',
         'config_loader_cycles':27,'new_config_words':0,'public_ports_increment':0},
      'cycles':{'lookahead_increment_model':0,'lookahead_accepted_II_model':1,'measured_added_cycles':None,
         'inherited_Rcap0_total_extra':2,'inherited_Rcap1_total_extra':3,'qualified_selected_total_extra':None,
         'not_two_cycle_walker':True,'token_delta_increment_model_s':0,'absolute_qop_calendar_not_measured':True},
      'replication':{'q_pairs_per_rankdie':count,'BF_pairs_unchanged':s82['BF_pairs'],'rankdies':s82['layer_dies'],
         'FF_increment_per_qpair':c['total_FF_increment'],'FF_increment_per_rankdie':c['total_FF_increment']*count,
         'FF_increment_all_rankdies':c['total_FF_increment']*count*s82['layer_dies'],
         'clock_buffers_per_rankdie':cost['clock_buffer_reserve']*count,'control_buffers_per_rankdie':cost['control_buffer_reserve']*count,
         'cell_reserve_increment_mm2_per_rankdie':float(cell),'placed_reserve_increment_mm2_per_rankdie':float(placed),
         'S82_prior_screen_margin_mm2':float(margin),'gross_margin_after_uncredited_increment_mm2':float(margin-placed),
         'overlap_credit':0,'area_reconciliation_required':True},
      'boundaries':{'added_MAC_per_cycle':0,'added_external_bits_per_cycle':0,'added_memory_bytes_per_cycle':0,
         'internal_metadata_bits_per_qpair':252,'routing_tracks':'NOT_EXTRACTED; 252 metadata bits is not a track count',
         'clock_reset_PG_slot_fit':'OPEN','SS_setup_ps':60,'FF_hold_ps':25,'period_ps':833},
      'source_hook_plan':{'default_off':'QP_NEED_LOOKAHEAD=0, new additive modules only',
         'propagation':'field q-only sites -> pair -> q element; BF512 unchanged',
         'no_BF_lookahead_credit':True,'no_compiler_or_macro_word_order_change':True,
         'prerequisite':'mandatory second-row decoder correction in reference and candidate; immutable-ROM independent public arithmetic/tag/fault oracle',
         'owner_split':'Epicurus x-need element; Archimedes combined source/caller; Claude current S82 system measurements; Maxwell clock/physical homes'},
      'admission':'MODEL_SOURCE_BOUND_NOT_RTL_OR_PHYSICAL_ADMITTED','new_RTL':False,'new_builds':0,
      'adoption':False,'rates_or_stage_die_rows_regenerated':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.write_text(json.dumps(model(),sort_keys=True,indent=2)+'\n')
if __name__=='__main__':main()
