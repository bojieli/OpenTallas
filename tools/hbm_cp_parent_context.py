#!/usr/bin/env python3
"""Prepare one source-faithful CP+association child in the selected service slot."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONTRACT='results/rtl/hbm_child_contract_20261005/child_reservations.json'
OUT=ROOT/'physical/hbm_cp_parent_context_20261005'

def prepare():
    r=json.loads((ROOT/CONTRACT).read_text());cp=r['CP'];clock=r['clock']
    c=next(c for c in r['channels'] if c['child']=='CP')
    from uarch_model import hbm_cp_validate_allocated_sources
    checked_sources=hbm_cp_validate_allocated_sources(ROOT,cp)
    OUT.mkdir(parents=True,exist_ok=True)
    gx,gy,gx1,gy1=cp['gross_bbox_um'];cx,cy,cx1,cy1=cp['core_bbox_um']
    assert abs(cx1-cx-43.2)<1e-8 and abs(cy1-cy-43.2)<1e-8
    # Network estimates are replaced by propagated CTS in routed corner STA.
    sdc=(ROOT/'results/rtl/hbm_child_contract_20261005/cp_parent_clk_sm.sdc').read_text()
    sdc=sdc.replace('clk_sm','core_clk')
    sdc=sdc.replace('set_clock_latency -early 90', 'set_clock_latency -min 90')
    sdc=sdc.replace('set_clock_latency -late 100', 'set_clock_latency -max 100')
    sdc+='\n# Context exports held execution and new-request permit from the real join.\n'
    sdc+='set ot_association_outputs [get_ports {exec_owned new_request_permit association_fault}]\n'
    sdc+='set_output_delay -clock core_clk -max 166.666666667 $ot_association_outputs\n'
    sdc+='set_output_delay -clock core_clk -min 0 $ot_association_outputs\n'
    sdc+='set_load 9.673192000 $ot_association_outputs\n'
    sdc+='\n# Root POR is also timed for recovery/removal, not false-pathed.\n'
    sdc+='set_input_delay -clock core_clk -max 166.666666667 [get_ports por_n]\n'
    sdc+='set_input_delay -clock core_clk -min 0 [get_ports por_n]\n'
    (OUT/'context.sdc').write_text(sdc)
    widths={p['name']:p['bits'] for p in cp['ports']}
    pins=[];lines=['# Selected M6 channel coordinates translated by the child gross origin.']
    for pin in c['pin_track_allocation']:
        port=pin['port'];bit=pin['bit']
        if port in ('association/raw_grant','association/qualified_owned'):
            continue  # Real joined nets are internal, not duplicated top ports.
        if port=='association/fault':port='association_fault'
        elif port.startswith('association/'):port=port.split('/')[1]
        width=widths[pin['port']]
        name=port if width==1 else f'{port}[{bit}]'
        x=cx-gx;y=pin['coordinate_um']-gy
        lines.append(f'place_pin -pin_name {{{name}}} -layer M6 -location {{{x:.9f} {y:.9f}}}')
        pins.append(dict(name=name,layer='M6',xy_um=[x,y],parent_coordinate_um=pin['coordinate_um']))
    # These two tracks use the explicit clock/reset reserve, not signal capacity.
    for name,index in [('clk',0),('por_n',1)]:
        y=cy-gy+c['offset_um']+index*c['pitch_um']
        lines.append(f'place_pin -pin_name {{{name}}} -layer M6 -location {{{cx-gx:.9f} {y:.9f}}}')
        pins.append(dict(name=name,layer='M6',xy_um=[cx-gx,y]))
    assert len(pins)==236 and len(set(p['name'] for p in pins))==236
    # Keep the nested association allocation in the existing CP outline.
    sx,sy,sx1,sy1=cp['submodules'][1]['relative_bbox_um']
    parent_dx=cx-cp['core_relative_um'][0];parent_dy=cy-cp['core_relative_um'][1]
    regions=[('cp_body',[cx-gx,cy-gy,cx1-gx,sy+parent_dy-gy]),
             ('cp_association',[sx+parent_dx-gx,sy+parent_dy-gy,sx1+parent_dx-gx,sy1+parent_dy-gy])]
    lines+=['set ot_block [ord::get_db_block]', 'set ot_dbu [$ot_block getDbUnitsPerMicron]']
    for name,bbox in regions:
        dbbox=[f'[expr {{round({v:.9f}*$ot_dbu)}}]' for v in bbox]
        lines += [f'set ot_region [odb::dbRegion_create $ot_block {name}]',
                  '$ot_region setType EXCLUSIVE',
                  f'odb::dbBox_create $ot_region {" ".join(dbbox)}',
                  f'set ot_group_{name} [odb::dbGroup_create $ot_block {name}]',
                  f'$ot_group_{name} setRegion $ot_region']
    # Yosys/ABC may give cells anonymous names. Use source-held/output nets;
    # never infer the cell's ownership from an anonymous generated instance ID.
    lines += ['set ot_assoc_members 0','set ot_cp_members 0',
              'foreach ot_inst [$ot_block getInsts] {',
              ' if {[[$ot_inst getMaster] isBlock]} {error "Unexpected macro in CP-only context"}',
              ' set ot_association_cell 0',
              ' foreach ot_iterm [$ot_inst getITerms] {',
              '  if {[[$ot_iterm getMTerm] getIoType] ne "OUTPUT"} {continue}',
              '  set ot_net [$ot_iterm getNet]; if {$ot_net eq "NULL"} {continue}',
              '  set ot_name [$ot_net getName]',
              '  if {[string match {u_su_association.on.*} $ot_name] ||',
              '      $ot_name in {exec_owned new_request_permit association_fault}} {set ot_association_cell 1}',
              ' }',
              ' if {$ot_association_cell} {',
              '  $ot_group_cp_association addInst $ot_inst; incr ot_assoc_members',
              ' } else {',
              '  $ot_group_cp_body addInst $ot_inst; incr ot_cp_members',
              ' }',
              '}',
              'if {$ot_assoc_members==0 || $ot_cp_members==0} {error "Missing actual CP/association context cells"}',
              'puts "OT_CONTEXT_REGION cp_association $ot_assoc_members"',
              'puts "OT_CONTEXT_REGION cp_body $ot_cp_members"']
    lines+=['orfs_write_db $::env(RESULTS_DIR)/3_2_place_iop.odb',
            'write_pin_placement $::env(RESULTS_DIR)/3_2_place_iop.tcl']
    (OUT/'pins_and_regions.tcl').write_text('\n'.join(lines)+'\n')
    # Existing selected service PDN, retaining M8/M9 straps over the child.
    fp=json.loads((ROOT/'results/rtl/hbm_child_contract_20261005/floorplan_revision.json').read_text())
    pitch=fp['pdn']['strap_pitch_um']['svc'];width=.48
    pdn='''add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name cp_service -voltage_domains {CORE} -pins {M8 M9}
add_pdn_stripe -grid cp_service -layer M1 -width 0.018 -pitch 0.54 -offset 0 -followpins
add_pdn_stripe -grid cp_service -layer M2 -width 0.018 -pitch 0.54 -offset 0 -followpins
'''
    for layer in ('M8','M9'):
        pdn+=f'add_pdn_stripe -grid cp_service -layer {layer} -width {width} -spacing {pitch/2-width:.9f} -pitch {pitch:.9f} -offset {pitch/2:.9f}\n'
    pdn+='add_pdn_connect -grid cp_service -layers {M1 M2}\nadd_pdn_connect -grid cp_service -layers {M2 M8}\nadd_pdn_connect -grid cp_service -layers {M8 M9}\n'
    (OUT/'pdn.tcl').write_text(pdn)
    record=dict(schema='hbm.cp.parent-context.physical-inputs.v1',contract=CONTRACT,
        contract_sha256=hashlib.sha256((ROOT/CONTRACT).read_bytes()).hexdigest(),
        checked_sources=checked_sources,
        die_area_um=[0,0,gx1-gx,gy1-gy],core_area_um=[cx-gx,cy-gy,cx1-gx,cy1-gy],
        parent_translation_um=[gx,gy],regions=regions,pins=pins,
        signal_ports=234,power_clock_reset_ports_excluded_from_signal_count=True,
        reserved_signal_tracks=236,available_signal_tracks=577,
        physical_pin_placement_may_snap_to_translated_native_grid=True,
        clock=clock,PG_source='existing selected service M8/M9 width.48 and svc pitch',
        measured_load_or_CTS=False,adopted=False,
        parameters={k:1 for k in ['ENABLE','SU_ENABLE','SU_REGISTERED_OUTPUTS','SU_REGISTERED_STATUS','SU_REGISTERED_BOUNDARY','SU_BALANCED_OWNER_BOUNDARY']},
        source_faithful_top='ot_hbm_integrated_su_cp_context',joint_W2_parent_repeat=False)
    (OUT/'inputs.json').write_text(json.dumps(record,indent=2)+'\n')
    return record

def corner_sta(orfs, output):
    # Existing single-corner sessions/SPEF, with actual FF data endpoints.
    import sys
    sys.path.insert(0,str(ROOT/'tools/w18'))
    import corner_sta as base
    original=base.script
    def script(corner,relative,macros):
        text=original(corner,relative,macros)
        text=text.replace('foreach p [get_pins -hierarchical */D]', 'foreach p [all_registers -data_pins]')
        check='max' if corner=='ss' else 'min'
        extra = """
set ot_ff [all_registers -data_pins]
set ot_ff_names [dict create]
foreach p $ot_ff {
 set n [get_full_name $p]
 dict set ot_ff_names $n 1
 set s [get_property $p slack_CHECK]
 if {$s ne "INF"} {puts "OT_ACTUAL_FF $n $s"}
}
foreach p [get_pins -hierarchical */D] {
 set n [get_full_name $p]
 if {![dict exists $ot_ff_names $n]} {
  set s [get_property $p slack_CHECK]
  if {$s ne "INF"} {puts "OT_COMBINATIONAL_D $n $s"}
 }
}
foreach p [all_outputs] {
 set s [get_property $p slack_CHECK]
 if {$s ne "INF"} {puts "OT_ACTUAL_OUTPUT [get_full_name $p] $s"}
}
puts OT_GROUP_TRUE_RECURRENCE
report_checks -path_delay CHECK -from [all_registers -clock_pins] -to $ot_ff -group_path_count 1 -format full_clock_expanded
puts OT_GROUP_INPUT_TO_TRUE_FF
report_checks -path_delay CHECK -from [all_inputs] -to $ot_ff -group_path_count 1 -format full_clock_expanded
puts OT_GROUP_OUTPUT
report_checks -path_delay CHECK -to [all_outputs] -group_path_count 1 -format full_clock_expanded
set ot_reset [get_pins -hierarchical */RESETN]
if {[llength $ot_reset]} {
 puts OT_GROUP_RESET_RECOVERY_REMOVAL
 report_checks -path_delay CHECK -to $ot_reset -group_path_count 1 -format full_clock_expanded
}
""".replace('CHECK',check)
        return text.replace('exit\n',extra+'\nexit\n')
    base.script=script
    result=dict(schema='hbm.cp.parent-context.corners.v1',
        ss=base.run(Path(orfs),'ss',[]),ff=base.run(Path(orfs),'ff',[]),
        FF_endpoint_basis='all_registers -data_pins; literal combinational */D separately labelled',
        uses_extracted_interconnect_and_propagated_clock=True,external_loads_analytical=True,parent_budget_adoption=False)
    Path(output).write_text(json.dumps(result,indent=2)+'\n')
    if any(result[c]['errors'] for c in ('ss','ff')):
        raise RuntimeError('Context corner STA errors retained')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--corner-sta',metavar='ORFS_DIR')
    parser.add_argument('--output')
    args=parser.parse_args()
    if args.corner_sta:
        if not args.output:parser.error('--corner-sta requires --output')
        corner_sta(args.corner_sta,args.output)
    else:
        r=prepare();print(f"CP context: {len(r['pins'])} physical pins,234 signals; allocated43.2um core; analytical clock/load budgets")
