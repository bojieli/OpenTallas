"""Bind the ONE address issuer to selected S81 geometry and actual ROM source ports.

No physical-provider selection, engine RTL, synthesis, route or image generation.
The local native receiver images must not be promoted to full-parent tables.
"""
import hashlib
import json
import math
from pathlib import Path

import dsrom_s81_fulldie as S

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/rtl/dsrom_recovery_20261004/issuer_parent_binding'


def actor_programming_cost(stream_words, *, phase_write_II, stream_write_II,
                           last_write_visible_edges, GO_visibility_guard_edges,
                           programming_hz):
    """Mutable fallback only: serial source-arm cost on an explicit provider.

    This function does not require mutable hardware or per-token writes for a
    general immutable image. Existing inputs() requires cold/idle/all_quiet/prior_drained, then replaces
    two PHROM words and the stream prefix. No overlap or hidden load credit.
    The caller must supply actual provider II, visibility and clock binding.
    Counts are accepted hardware writes, never software-array assignments.
    """
    values=(stream_words,phase_write_II,stream_write_II,
            last_write_visible_edges,GO_visibility_guard_edges)
    if any(type(v) is not int or v<=0 for v in values):
        raise ValueError('positive word count, II and captured visibility/GO fence required')
    if not math.isfinite(programming_hz) or programming_hz<=0:
        raise ValueError('explicit positive programming clock required')
    phase_edges=2*phase_write_II
    stream_edges=stream_words*stream_write_II
    edges=phase_edges+stream_edges+last_write_visible_edges+GO_visibility_guard_edges
    return dict(PHROM_write_words=2,STREAM_write_words=stream_words,
        payload_bytes=16+6*stream_words,
        accepted_write_edges=phase_edges+stream_edges,
        visible_and_GO_fence_edges=last_write_visible_edges+GO_visibility_guard_edges,
        exposed_edges=edges,exposed_us=edges/programming_hz*1e6,
        overlap_credited_edges=0,once_per_fresh_actor=True,
        assumption='Serial source arm; requires measured/model-bound hardware ports and visibility, not a hardware qualification.')


def build():
    price=json.loads((OUT/'inputs/issuer_model_84528.json').read_text())
    m=S.build();capture=m['hub']['capture']
    parent=[capture.x,capture.y,capture.x+capture.w,capture.y+capture.h]
    box=price['slot_xy_um'];x0,y0,x1,y1=box
    inside=parent[0]<=x0<x1<=parent[2] and parent[1]<=y0<y1<=parent[3]
    if not inside:raise ValueError('issuer outside selected capture reservation')
    if abs((x1-x0)*(y1-y0)-price['reservation_um2'])>1e-6:
        raise ValueError('issuer area changed')
    for coordinate in (x0,x1):
        if abs(coordinate/S.GX-round(coordinate/S.GX))>1e-6:
            raise ValueError('issuer x off selected planning lattice')
    for coordinate in (y0,y1):
        if abs(coordinate/S.GY-round(coordinate/S.GY))>1e-6:
            raise ValueError('issuer y off selected planning lattice')
    paths=['tools/dsrom_s81_fulldie.py','tools/dsrom_recovery_issuer_parent_binding.py',
        'rtl/v41die/ot_v41_spine_pq_w17w10.sv',
        'tools/dsrom_s81_target_field_controls.py','tools/v41_die_images_w17w10.py',
        'tools/runtime/dsrom/s81_minimum_qe_controls.cpp',
        'tools/runtime/dsrom/s81_minimum_qe.cpp',
        'physical/dsrom_recovery_field/ot_v41_pq_spine_screen.sv',
        str((OUT/'inputs/issuer_model_84528.json').relative_to(ROOT))]
    return dict(schema='opentallas.dsrom-recovery.issuer-parent-binding.v1',
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        selected_parent=dict(pairs=2417,BF_pairs=519,stage_count=81,TP=4,
            instance=capture.name,master=capture.master,bbox_um=parent,
            domain=capture.domain,abstract_kind='reservation slab, not actual placed cells',
            other_owners={k:dict(instance=m['hub'][k].name,domain=m['hub'][k].domain)
                          for k in ('vm','collective')}),
        issuer=dict(name='sp_capture/sp_pq_issuer',instances_per_field_die=1,
            bbox_um=box,parent_local_bbox_um=[x0-parent[0],y0-parent[1],x1-parent[0],y1-parent[1]],
            rectangle_contained=inside,planning_lattice_aligned=True,
            reservation_um2=price['reservation_um2'],estimated_cell_um2=price['estimated_cell_um2'],
            cell_budget_um2=price['cell_budget_um2'],remaining_cell_budget_um2=price['remaining_cell_budget_um2'],
            charged_once=True,raw_FF=47,new_clock_sinks=47,new_reset_sinks=0,
            hierarchy='g_addr_lookahead; active_fam1, active_nbeat16, active_base16, active_addr14',
            added_cycles=0,II=1,existing_cell_nonoverlap_verified=False,
            actual_site_rows_and_PG_verified=False,clock_and_signal_routes_verified=False,
            area_accounting='NEW issuer debit only. Do not credit old capture area or put the stream ROM inside this47FF budget.'),
        parent_tables=dict(PHW=10,SAW=14,
            PHROM=dict(word_bits=64,words=2048,bits=131072,simultaneous_read_ports=2,
                addresses=['{i_ph,0}','{i_ph,1}'],
                equivalent_even_odd_banking='2x1024x64, same10bit i_ph, BOTH read in same source edge'),
            STREAM=dict(word_bits=48,words=16384,bits=786432,read_ports=1,address_bits=14),
            source_read_latency='Combinational lookup, captured by existing source flops; no extra edge',
            write_ports=0,ROM_reset_ports=0,ROM_clock_ports=0,
            external_interface='OT_PQ_ROM_PORTS: rom_pa0/1, rom_pq0/1, rom_sa, rom_sq',
            selected_synth_immutable_image=None,selected_hard_abstract=None,
            immutable_capacity_status='SOURCE CATALOG READY per Arendt: stage37/38 full624/626 canonical phases and keys, conflicts0, no descriptor dynamic fields in PHROM; exact existing-body sharing with fixed SBASE. Unshared41400 append count was not a capacity impossibility.',
            resident_catalog=dict(stage37=dict(phases=624,distinct_body_words=1208),stage38=dict(phases=626,distinct_body_words=1144),
                image_directory='/srv/opentallas-scratch/codex/arendt-all40-source-schedules-20261005/immutable_stages_r1',
                provenance='Arendt owner handoff; image bytes/provider enrollment not independently claimed by this record'),
            preferred_provider='Static physical provider if general source-bound image is validated; mutable RAM fallback only if actually needed.',
            static_access_latency_us=None,static_initialization_latency_us=None,
            static_initialization_amortization=None,
            immutable_per_token_write_policy='No host-write charge for a validated general hardware image. Price actual access and initialization; do not infer zero delay from capacity fit.',
            clock_to_Q_ps=None,loaded_combinational_access_ps=None,
            synthetic_or_weight_macro_timing_transfer=False,
            synthesis_gap='Internal zero init + runtime OT_ROM_DIR readmemh is a simulation image loader, not an enrolled immutable synthesis image. No actual full-parent table master is instantiated by selected reservation graph.',
            required_source_binding='Compile-time full-parent phase/stream image from same canonical phase/key namespace and Arendt schedules; keep simultaneous phase reads and source latency. Bind actual synthesized ROM access or its real hard view before contextual route.'),
        local_native_controls=dict(PHROM_words=2,stream_base=0,consumer_numeric_width=48,
            emitter_format='010x is minimum character padding, not40bit truncation',
            original_emitter_format='012x: same word value, different leading zero padding',
            defined_stream_bits=dict(BF16_highest_used_bit=39,FP4_FP8_highest_used_bit=13,
                                     physical_carrier_bits=48),
            full_parent_image=False,
            reason='One-fragment receiver controls, local phase0/base0; canonical element CFGphase is preserved separately. Not full-stage PHW10/SAW14 image.'),
        screen=dict(stream_words=256,stream_bits=48,write_port=True,
            full_parent_provider=False,SS_FF_transfer=False),
        current_programming=dict(source='tools/runtime/dsrom/s81_minimum_qe.cpp::Impl::inputs',
            actual_action='When !configured: wait cold/idle/obs_rows_left0/all_quiet/prior_drained; assign PHROM[2*phase], PHROM[2*phase+1], then strom[base+j]; set configured.',
            once_per_fresh_actor=True,held_retry_reloads=False,
            update_payload_bytes='16 +6*actual_stream_word_count',
            shared_prefix_overwrite=True,
            actual_hardware_write_port=None,write_II=None,last_write_visible_edges=None,
            hardware_programming_latency_us=None,net_optional_field_gain_us=None,
            programming_overlap_proved=False,
            provider_selection='Static resident image selected for Epicurus physical-provider binding; mutable source-arm pricing is inactive for this case.',
            mutable_programming_cost_applied=False,
            per_token_host_programming_required=False,
            matched_policy='Use SAME selected provider in serialized and47FF cases. Static case prices actual access/initialization without per-token host writes for a general image; mutable fallback prices accepted writes and positive last-write visibility beforeGO. Never overwrite active owned data.',
            optional_adoption_threshold_rate_gain_percent=1,
            mandatory_baseline_fix_separate=True,
            composition_callable='MUTABLE FALLBACK ONLY actor_programming_cost: accepted2PHROM+actualstream count, explicit per-portII/clock/visibility/GOguard, zero hidden loading credit; not applied to a general static image',
            warning='The .920us result excludes hardware programming and is an isolated scheduling measurement, not net whole-token gain.'),
        physical_build_admitted=False,
        exact_remaining_hook='Actual full-parent immutable phase/stream table image/provider and cell-placed capture owner; no writable256 screen or weight ROM substitute.')


if __name__=='__main__':
    model=build()
    (OUT/'model.json').write_text(json.dumps(model,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(contained=model['issuer']['rectangle_contained'],
                         cell_budget_remaining_um2=model['issuer']['remaining_cell_budget_um2'],
                         physical_build_admitted=False)))
