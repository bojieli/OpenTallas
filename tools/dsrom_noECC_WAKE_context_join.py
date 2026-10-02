#!/usr/bin/env python3
"""Join real retained maps, instance abstracts and positive-only frame debit."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_noECC_WAKE_cell_retention_20261002/terminal'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
    for name,h in json.loads((BASE/'input_hashes.json').read_text()).items():
        if sha(BASE/name)!=h:raise ValueError('immutable raw evidence changed '+name)
    x=json.loads((BASE/'context_terminal.json').read_text());m=json.loads((BASE/'mapping_terminal.json').read_text())
    if x['status']!='EIGHT_ACTUAL_WAKE_CELLS_RETAINED_CONTEXT_OPEN':raise ValueError('not complete retained maps')
    cases={}
    for k,c in x['cases'].items():
        w=c['actual_WAKEDFF'];e=c['physical_geometry_contract']
        if not w['passed'] or any(w[n]!=8 for n in ['mapped_local_FF_count','distinct_FF_outputs','distinct_WAKE_outputs']):raise ValueError('real8 retained FF/outputs required')
        names={i['instance'].removeprefix('u_e.') for i in e['macro_instances']}
        if names!=set(c['actual_macro_cells']):raise ValueError('mappedmacro/translatedabstract identity mismatch')
        if len(c['actual_capture_FF_cells'])!=1088 or len(c['actual_ICG_cells'])!=8:raise ValueError('completecapture/clock required')
        h=151200 if k=='q' else 157680;oldh=144720 if k=='q' else 157680
        width=e['outline_DBU'][2];cut=e['compute_control_clock_region_DBU'][0]
        available=e['area_reservation']['proposed_remaining_cell_region_plus_capture_strips_um2']+(width-cut)*(h-oldh)/1e6
        cases[k]={'WAKE_retention':w,'physical_macros':4,'macro_payload_width_bits':274,'macro_identity_bijection':sorted(names),'actual_top_ports':c['actual_top_ports'],'actual_ICG_cells':c['actual_ICG_cells'],'SS_FF_clock_pin_loads':c['SS_FF_pin_loads'],'mapped_cell_area_um2':c['mapped_area_um2'],'outline_DBU':[0,0,width,h],'whole_frame_area_um2':width*h/1e6,'frame_growth_um2_replace_once':width*(h-oldh)/1e6,'available_cell_capture_reservation_um2':available,'source50pct_cell_debit_um2':2*c['mapped_area_um2'],'margin_before_CTS_wires_PGvias_um2':available-2*c['mapped_area_um2'],'full_source_pin_OBS_PG_template_bound_to':'context_terminal.json/cases/'+k+'/physical_geometry_contract','PG_template_growth_required_strip_DBU':[0,oldh,width,h] if h>oldh else None,'actual_PG_CTS_installed':False,'capture_constraints':c['capture_constraints'],'parent_IO_requirements':c['parent_IO_requirements'],'macro_instance_body_and_halo_not_credited':True}
    return {'schema':'opentallas.dsrom.retained-WAKE-context-join.v1','candidate':x['candidate'],'mapping_source_commit':m['source_commit'],'mapping_terminal_sha256':sha(BASE/'mapping_terminal.json'),'context_terminal_sha256':sha(BASE/'context_terminal.json'),'cases':cases,'MACs_ports_payloads_reduction_order_and_added_cycles_unchanged':True,'fixed_period_ps':x['fixed_period_ps'],'SS_setup_ps':60,'FF_hold_ps':25,'physical_G0_admitted':False,'PnR_admitted':False,'remaining_concrete_context':['CTS: actual8 root/localWAKE placement, eightICG branch buffering, skew/slew/minpulse','PG: translatedmacro pins/OBS/halo, extend qnewbottomstrip PDN and install via/spacing/pinescape union','IO: source-parent CFG/VM/root endpoint drivingcell arrival/slew and receiver load','SSFF: macroclkQ+selectedcaptureenables+onecyclecapture-to-lane, with endpoint-narrow multicycle only','Maxwell: replace qframe once +3310.2432um2/pair; retainBFgrowth and fullselector1.68242mm2'],'old_a910_failure_preserved':True,'no_cold_synthesis_in_attribute_preparation':True}
if __name__=='__main__':
    x=build();(BASE/'model.json').write_text(json.dumps(x,indent=2,sort_keys=True)+'\n');print(sha(BASE/'model.json'))
