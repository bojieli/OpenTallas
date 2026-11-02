"""Materialize a disabled normal-GEN readset for the source-native row proposal."""
import argparse
import hashlib
import json
from pathlib import Path

TOP='ot_hgi_sfu_programme_store_r10'
MASTER='ot_sram_1r1w_512x256_m1_r2c2'
ROOT=Path(__file__).resolve().parents[2]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--repo',type=Path,default=ROOT);a=p.parse_args();d=a.candidate.resolve();root=a.repo.resolve()
    d.relative_to(root);m=json.loads((d/'model.json').read_text());gate=json.loads((d/'row_pin_gate.json').read_text())
    for name in ('model.json','actual_FF_rows.csv','native_pins_clock_entry.json'):
        assert gate['inputs_sha256'][name]==sha(d/name),'stale row/pin/model qualification'
    assert gate['actual_FF']==20842 and gate['macro_halo_violations']==0 and gate['first_input_failures']==0
    assert all(v['bad_all_R0_MX_pin_corners']==0 for v in gate['adjacent_edges'].values())
    pins=d/'native_pins_clock_entry.json';psha=sha(pins);W,H=m['outline_um'];view=TOP+'@'+psha[:12]
    source=root/'results/hbm_programme_native_intake_0450'
    plan=json.loads((source/'GEN_plan.json').read_text());plan['die'].update(name='SELECTED_R10_NATIVE_ROW_CANDIDATE_GEN_ONLY',outline_um=[W,H])
    slot=plan['partition_types']['native_provider_slot'];slot['outline_um']=[W,H]
    slot['hard_cores'][0].update(outline_um=[W,H],pins_file=pins.name)
    (d/'GEN_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    # Normal --core-macros auto consumes this table even when the callback
    # recipe already carries placements. Bind it to these exact reviewed,
    # native-pin-grid-snapped rectangles, never the smaller old GEN geometry.
    core_macros=dict(schema='opentallas.core_macros.v1',cores={TOP:dict(status='KNOWN',
      basis='DISABLED_REVIEWED_EXACT_STATIC_RECTS_NOT_PLACED_PROVIDER',
      macros=[dict(name=q['name'],master=MASTER,rect_um=q['rect_um'],orient='R0')for q in m['macros']])})
    (d/'core_macros.json').write_text(json.dumps(core_macros,indent=2)+'\n')
    views=dict(schema='opentallas.hbm_arch.views.v1',plan='GEN_plan.json',plan_sha256=sha(d/'GEN_plan.json'),
      view_list=[dict(view=view,module=TOP,outline_um=[W,H],pins_file=pins.name,pins_sha256=psha,pins=2904,
        recipe_keys=[TOP],family='SOURCE13_SELECTED_R10_PAGE_AW1',canonical_type=None,instances=['B113.DISABLED_moved_r10'],placed=0)])
    (d/'views.json').write_text(json.dumps(views,indent=2)+'\n')
    clock_asset=d/'clock_placement_reservations.json';clock=json.loads(clock_asset.read_text())
    assert clock['rounding_permitted']is False and clock['creates_clock_cells']is False and clock['transfers_CTS_sink_ownership']is False
    for name in ('model.json','actual_FF_rows.csv','native_pins_clock_entry.json','clock_entry_gate.json'):
        assert clock['input_identity'][name]==sha(d/name),'clock reserves differ from exact native geometry'
    assert len(clock['reservations'])==32 and clock['outline_um']==[W,H]
    rects=[('root_island',clock['root_island_um'])]+[(q['name'],q['body_rect_um'])for q in clock['reservations']]
    reserve=['# Exact source-pinned native clock-space reservations; no clock cells or CTS sink binding.',
      '# Model SHA256 '+clock['model_sha256'],
      'set pc_block [ord::get_db_block]',
      'set pc_u [[ord::get_db_tech] getDbUnitsPerMicron]',
      'set pc_record [open $::env(RESULTS_DIR)/programme_clock_reservations.txt w]',
      'foreach {pc_name pc_x0 pc_y0 pc_x1 pc_y1} {']
    for name,box in rects:reserve.append('  '+name+' '+' '.join(format(v,'.17g')for v in box))
    reserve+=['} {',
      '  set pc_rect {}',
      '  foreach pc_v [list $pc_x0 $pc_y0 $pc_x1 $pc_y1] {',
      '    set pc_n [expr {round($pc_v*$pc_u)}]',
      '    if {abs($pc_v*$pc_u-$pc_n)>0.000001} {error "PROGRAMME_CLOCK_RESERVE off native DBU grid"}',
      '    lappend pc_rect $pc_n',
      '  }',
      '  lassign $pc_rect pc_a pc_b pc_c pc_d',
      '  foreach pc_i [$pc_block getInsts] {',
      '    set pc_m [$pc_i getMaster]',
      '    if {![$pc_m isBlock] && [$pc_m getName] ne "DFFHQNx1_ASAP7_75t_R"} continue',
      '    set pc_box [$pc_i getBBox]',
      '    set pc_h [expr {[$pc_m isBlock] ? round(4.32*$pc_u) : 0}]',
      '    if {$pc_a<[$pc_box xMax]+$pc_h && $pc_c>[$pc_box xMin]-$pc_h && $pc_b<[$pc_box yMax]+$pc_h && $pc_d>[$pc_box yMin]-$pc_h} {',
      '      error "PROGRAMME_CLOCK_RESERVE actual placed FF/macro halo collision $pc_name [$pc_i getName]"',
      '    }',
      '  }',
      '  odb::dbBlockage_create $pc_block $pc_a $pc_b $pc_c $pc_d',
      '  puts $pc_record [list $pc_name {*}$pc_rect]',
      '}',
      'close $pc_record',
      'puts "PROGRAMME_CLOCK_RESERVE exact33 rectangles; no clock cells or CTS ownership transfer"']
    (d/'programme_clock_reserve.tcl').write_text('\n'.join(reserve)+'\n')
    runtime=[]
    for src,dest in [(root/'tools/hbm_b2/programme_native_rows.tcl','runtime/programme_native_rows.tcl'),(d/'actual_FF_rows.csv','runtime/actual_FF_rows.csv'),
                     (d/'programme_clock_reserve.tcl','runtime/programme_clock_reserve.tcl'),(clock_asset,'runtime/clock_placement_reservations.json')]:
        runtime.append(dict(source=src.relative_to(root).as_posix(),sha256=sha(src),destination=dest))
    overlay=dict(macro_placement=[dict(inst=q['name'],xy_um=q['rect_um'][:2],orient='R0',macro=MASTER)for q in m['macros']],
      runtime_files=runtime,orfs_vars=dict(PRE_GLOBAL_PLACE_TCL='/work/runtime/programme_native_rows.tcl'))
    (d/'recipe_overlay.json').write_text(json.dumps(overlay,indent=2)+'\n')
    capsule=dict(status='DISABLED_NORMAL_GEN_READSET_READY_REVIEW_REQUIRED',view=view,
      DIE_AREA=[0,0,W,H],CORE_AREA=[4.32,4.32,W-4.32,H-4.32],macro_count=44,actual_FF=20842,ABI=2904,
      added_FF=0,added_cycles=0,source_default_changed=False,
      area_model_um2=dict(old_context=574.56*738.72,new_candidate=W*H,delta=W*H-574.56*738.72),
      proposed_PLACE_resource=dict(memory_GB=8,threads=2,stage='ONE_PLACE_ONLY_AFTER_REVIEW',
          basis='Context only: prior44-master pstore placement2.69GB; current actual66230std/20842FF/44SRAM; normal admission required'),
      normal_GEN=['python3','tools/hbm_b2/programme_current_native_kit.py','--row-plan',d.relative_to(root).as_posix(),'--out','OWN_SCRATCH_KITS','--tag','rows'],
      recipe_overlay='recipe_overlay.json',runtime_staging_api='910a8eb70+bb7ce574b; default empty; FLOW peer concur',
      clock_space_reservations=dict(asset=clock_asset.name,asset_sha256=sha(clock_asset),native_buffer_bodies=32,root_islands=1,
          creates_clock_cells=False,transfers_CTS_sink_ownership=False,rounding_permitted=False,
          preserved_through='GPL/DPL via exact native OpenDB blockages; fresh actual output audit required'),
      internal_clock_model=dict(status='CORRECTED_NATIVE_SOURCE_Y_GEOMETRY_PREP',source_peer='9636952c7',
          model_sha256=clock['model_sha256'],geometry_summary='clock_geometry_summary.json',regional_landing_reserves=32,
          max_actual_sinks_per_root=max(q['sink_count']for q in clock['reservations']),
          max_actual_Y_to_CLK_corners_um=max(q['max_actual_Y_to_CLK_full_corner_um']for q in clock['reservations']),
          previous_centre_only_model='FAIL: eight roots exceed220um, max220.899, corrected before physical dispatch',
          creates_clock_cells=False,transfers_CTS_sink_ownership=False,
          held=['Normal CTS exact site integration and electrical sizing/arrivals','No4.32-anchor rounding or physical reset/START credit']),
      source_proof_capsule=dict(original_readonly_kit='intel2:/srv/opentallas-scratch2/claude/codex-programme-native-0525/kits/ot_hgi_sfu_programme_store_r10_6a471c27f403-native_boundary',
        source_snapshot='542757d902e',actual_synth_sha256='403b159c3501a55715c55ea09779e000c2146f2c94be70eb5f6bfa1f937f0e41',
        actual_ODB_sha256='67b6465b2e0804bf9447bedc5e403273dacb706a32b1197154638cddcdc4871e',
        official_target='1_synth.v',official_points=54439,official_EQ='intel2:/srv/opentallas-scratch2/claude/codex-programme-postsynth-EQ-0605/lec',
        actual_LEC_sha256='4ca4d77ba726c52ed4c8f2e640128742814110fd9be60fb45cda57dfa0d41cbe',
        reset_cycles=4,reset_scope='Conditional component SOURCE_EQ only; no64/66 physical reset credit',
        intake='New exact checker/source/SYNTH join required; no automatic old-checker receipt or cache transfer'),
      held=['Structured internal-clock model and ROOT review before PLACE','New GEN must regenerate all DIE/CORE/PDN extents and normal preflight',
            'Normal actual row orientation/site/master checks; FIRM during GPL, normal DPL/guards unchanged',
            'Actual I/O timing/reset/START/provider/collar/parent source event still unqualified'])
    (d/'normal_intake_capsule.json').write_text(json.dumps(capsule,indent=2)+'\n')
    print(capsule['status'],view,flush=True)


if __name__=='__main__':main()
