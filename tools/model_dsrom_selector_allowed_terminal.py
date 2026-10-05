"""One mandatory source-policy repair: terminal HB2 -> allowed BUFx4.

Same station state, geometry, pipeline, clock and uncertainty. No cell sweep,
RTL build or placed/extracted timing claim; historical model stays unchanged.
"""
import fnmatch
import gzip
import hashlib
import json
from pathlib import Path
import re
import uarch_topk_buffered_station_source_model as M
import uarch_topk_station_SSFF_cell_model as C

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_selector_allowed_terminal_model_20261002'
OLD=ROOT/'results/uarch/topk_buffered_station_source_model_20261002/model_r2.json'
OLD_SHA='1589f533c2212363c87b1fc286295444ff1b836680ba1daa92f6a5c2c017919e'
POLICY_SHA='c5c868f35c7c04365a074aef2d81c72641441a8070a117bcb1a35b696942507c'


def sha(b):return hashlib.sha256(b).hexdigest()


def policy():
    raw=(C.BASE/'inputs/config.mk').read_bytes()
    if sha(raw)!=POLICY_SHA:raise ValueError('production policy changed')
    lines=re.findall(r'^export DONT_USE_CELLS\s*(?:=|\+=)\s*([^\n]+)',raw.decode(),re.M)
    if not lines:raise ValueError('DONT_USE policy absent')
    return [word for line in lines for word in line.split()]


def build():
    raw=OLD.read_bytes()
    if sha(raw)!=OLD_SHA:raise ValueError('pinned226 station changed')
    old=json.loads(raw);patterns=policy();master='BUFx4_ASAP7_75t_R'
    if any(fnmatch.fnmatchcase(master,p) for p in patterns):raise ValueError('replacement master excluded')
    if not any(fnmatch.fnmatchcase(old['architecture']['terminal_hold_master'],p) for p in patterns):
        raise ValueError('source policy defect not reproduced')
    # Actual Liberty function is required, not an assumption from the name BUF.
    source_functions={}
    manifest_raw=(C.BASE/'source_manifest.json').read_bytes()
    if sha(manifest_raw)!=C.MANIFEST:raise ValueError('library source manifest changed')
    library_pins=json.loads(manifest_raw)
    for corner in ('SS','FF'):
        name=f'asap7sc7p5t_INVBUF_RVT_{corner}_nldm_220122.lib.gz'
        packed=(C.BASE/'inputs'/name).read_bytes()
        if sha(packed)!=library_pins[name]['sha256'] or len(packed)!=library_pins[name]['bytes']:
            raise ValueError('replacement Liberty bytes changed')
        text=gzip.decompress(packed).decode()
        if C.cell_facts(text,master)!=old['cell_facts'][corner]['BUF']:
            raise ValueError('pinned buffer timing facts differ from source')
        pin=C.group(C.group(text,'cell',master),'pin','Y')
        found=re.search(r'function\s*:\s*"([^"]+)"',pin)
        if not found or found[1]!='A':raise ValueError('replacement polarity changed')
        source_functions[corner]=found[1]
    ss=old['SS_conditional_screen'];ff=old['FF_conditional_screen'];facts=old['cell_facts']['SS']['BUF']
    terminal_delay=M.lut(facts['delay_transition_tables'],'cell_',160,1.44)
    terminal_slew=M.lut(facts['delay_transition_tables'],'transition',160,1.44)
    upper=ss['stage_upper_ps']-ss['HB_delay_ps']+terminal_delay
    destination_slew=terminal_slew+ss['wire_links']['HB_to_FF_local']['slew_growth_ps_2p2_RC_screen']
    margins={name:ff['zero_wire_hold_margins_ps'][name]+ff['minimum_characterized_cell_delays_ps']['BUF']-ff['minimum_characterized_cell_delays_ps']['hold']
             for name in ('data_FF','valid_FF')}
    if upper>833 or destination_slew>320 or min(margins.values())<0:raise ValueError('single allowed repair fails fixed screen')
    # Remote sink is already bounded by BUFx4 input cap in the original model.
    cap=max(old['cell_facts'][corner]['BUF']['input_cap_fF']['A'] for corner in ('SS','FF'))
    if cap!=ss['wire_links']['BUF_to_BUF_or_HB']['sink_cap_fF']:raise ValueError('reach changed by new sink')
    n=old['cost']['terminal_HB_cells'];lef=old['placement_contract']['LEF_master_dimensions']
    delta=n*(lef['BUF']['area_um2']-lef['hold']['area_um2'])
    total=old['cost']['station_cell_area_um2']+delta
    return dict(schema='opentallas.selector.fixed226.allowed-terminal.v1',candidate='DS4096-TP4-S58-PAR2-NP2048',
      baseline=dict(path=str(OLD.relative_to(ROOT)),sha256=OLD_SHA,unchanged=True),policy=dict(path=str((C.BASE/'inputs/config.mk').relative_to(ROOT)),sha256=POLICY_SHA,DONT_USE=patterns,changed=False),
      library_source_manifest_sha256=C.MANIFEST,one_mandatory_candidate_only=True,no_sweep=True,
      replacement=dict(old_master=old['architecture']['terminal_hold_master'],new_master=master,new_function=source_functions,count=n,
        restoring_INV_unchanged=True,local_wire_links_unchanged=True,repeaters_per_segment_unchanged=2,
        width_delta_um=lef['BUF']['width_um']-lef['hold']['width_um'],height_um=lef['BUF']['height_um']),
      fixed=dict(geometry=old['fixed_geometry'],core_state_bits=698354,data_FF=475954,valid_ASR=226,INV=476180,
        data_repeater_BUF=965012,terminal_BUF=n,terminal_HB=0,clock_BUF_floor=48007,
        input_edges=99,return_edges=99,write_edges=28,transport_cycles_per_call=226,service_increment_per_call=142,
        ninecall_increment=3312,ports_and_order_unchanged=True,maximum_remote_span_um=old['placement_contract']['maximum_remote_span_um'],
        segments_each_direction=100,formed_write_segments=29,remaining_half_pool_tracks=[28,38]),
      SS_conditional_screen=dict(period_ps=833,setup_uncertainty_ps=60,additional_skew_budget_ps=25,
        terminal_input_slew_ps_max=160,terminal_output_cap_fF_max=1.44,terminal_delay_ps=terminal_delay,
        terminal_output_slew_ps=terminal_slew,destination_slew_ps=destination_slew,stage_upper_ps=upper,
        remaining_ps=833-upper,source_RC_and_pin_detours_not_extracted=True),
      FF_conditional_screen=dict(hold_uncertainty_ps=25,additional_capture_skew_budget_ps=25,
        zero_wire_hold_margins_ps=margins,terminal_minimum_characterized_delay_ps=ff['minimum_characterized_cell_delays_ps']['BUF'],
        all_net_cap_fF_min=.72,all_cell_input_slew_ps_min=5,subgrid_extrapolation_credit=False,
        physical_min_load_and_slew_not_proven=True),
      cost=dict(cell_area_delta_um2=delta,station_cell_area_um2=total,station_reservation_mm2_at50pct=total*2/1e6,
        reserve_delta_mm2_at50pct=delta*2/1e6,old_station_replaced_not_added=True,additional_state_bits=0,additional_cycles=0,
        terminal_site_width_delta_DBU=round(1000*(lef['BUF']['width_um']-lef['hold']['width_um'])),
        clock_reset_PG_signal_escape_hold_route_repair_still_unpriced=True),
      construction=dict(new_master_LEF=lef['BUF'],terminal_net_source='Second repeat BUFx4/Y -> terminal BUFx4/A -> destination DFF/D',
        existing_remote_wire_ceiling_um=ss['wire_links']['BUF_to_BUF_or_HB']['length_ceiling_um'],
        local_destination_wire_ceiling_um=ss['wire_links']['HB_to_FF_local']['length_ceiling_um'],
        minimum_actual_load_and_slew_require_geometry=True,legal_sites_not_allocated=True,
        source_global_clock_reset_and_PG_union_required=True,caller_guard19_cells_remain_separately_charged=True),
      RTL_build_admitted=False,PR_admitted=False,HDL_equivalence=False,extracted_SS_FF=False,
      next_gate='Parent/Arch/Maxwell source-model admission, then independent full N4 NMAX2048 balanced-selector/caller-fence HDL preparation and gate. No physical admission from conditional timing screens.')


if __name__=='__main__':
    model=build();BASE.mkdir(parents=True,exist_ok=True);(BASE/'model.json').write_text(json.dumps(model,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(stage_upper_ps=model['SS_conditional_screen']['stage_upper_ps'],hold=model['FF_conditional_screen']['zero_wire_hold_margins_ps'],reserve_delta_mm2=model['cost']['reserve_delta_mm2_at50pct'],transport_cycles=226)))
