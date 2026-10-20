#!/usr/bin/env python3
"""Source-pinned RF port/capacity model. Does not authorize RTL or a gate."""
import argparse
import hashlib
import json
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MACRO='physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2'

def model():
    meta=json.loads((ROOT/(MACRO+'.json')).read_text())
    def candidate(name,writers,banks,condition):
        n=writers*banks*6
        return dict(name=name,macros=n,read_replicas=6,writer_arrays=writers,
            physical_banks=banks,logical_bits=8192,allocated_bits=n*32768,
            capacity_amplification=n*4,macro_area_um2=n*meta['area']['macro_area_um2'],
            required_calendar_condition=condition,status='NOT RUN')
    sources=['tools/hbm_static/qcore_rf_sram_model.py','tools/uarch_model.py','rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_qcore_r9.sv',
      'rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_top.sv',
      'physical/ref_tile/hbm_su_qcore_r6n_1019/spec.json',
      'tools/hbm_static/su_top_compile.py','tools/hbm_static/su_red_carry_calendar.py']
    sources += [MACRO+s for s in ['.json','.v','.lef','_tt.lib','_ss.lib','_ff.lib']]
    return dict(schema='opentallas.hbm.qcore-rf-sram-source-model.v1',
      status='MODEL_ONLY_ENGINE_NOT_READY',production_qualified=False,physical_qualified=False,
      unified_model_entry='tools/uarch_model.py:hbm_qcore_rf_sram_candidate_model',
      source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources},
      production_binding=dict(contract='/home/ubuntu/artifacts/hdie-d4/d4g_gen2e4_r7portage/net/contract_pre.json',
        source_commit='0ae60e322',qcore_params=dict(MUT=0,COLLPORT=1,RF_LOCAL=1),
        programme='ot_hbm_su_programme_pslice_c5',command_quarter='NW command[4844+:2422]',
        PIPE=2,compiler_start_advance_edges=6,EDGES_default=7111,
        old_component_manifest_sha256='544ba72d0cf50f2ca1f75092fd1ba5c9a56adbb2b590bd77e7f30ebdb2a25e93',
        old_component_edges=7116,old_component_qualified=False,
        actual_host_configuration_and_current_command_inventory='NOT PROVEN; never alias old standalone image to current binding'),
      RF=dict(words=256,bits_per_word=32,banks=64,rows_per_bank=4,logical_bits=8192,
        read_classes_normal=5,read_class5_words=8,read_bits_per_edge=416,read_bytes_per_edge=52,
        relay_write_ports=4,relay_write_bits_per_port=32,coll_write_bits=256,
        write_bits_per_edge=384,write_bytes_per_edge=48,issue_interval_edges=1,macs_per_cycle=0,
        external_RF_command_and_writer_bits=480,external_RF_drain_control_bits=2,
        external_RF_data_and_command_return_bits=420,external_RF_boundary_bits=902),
      semantic_contract=dict(write_capture='pin E; memory commit E+1',
        read_capture='command E; read-before-write array sample E+1; selected data E+2; external rf_bword/rf_dsec E+3',
        macro='1R1W sampled at rising edge, registered read; word_read executes before masked word_write',
        collision='highest relay writer wins per 6-bit bank even when rows differ; COLL overrides matching eight banks; preserve conflict fault',
        reset='RF data unreset; ownership table must persist, no reset-to-owner0 that changes retained data',
        invalid='preserve every-edge output hold contract, not only valid data',
        startup='arbitrary SRAM state and arbitrary persistent owner code need an explicit coupled-state proof and real first-valid calendar; no zero-init credit',
        logical_added_edges=0,logical_edge_status='candidate only; physical regional transport can require additional edges'),
      candidates=[candidate('general_five_writer_LVT',5,1,'No traffic restriction; implement exact same-bank priority and COLL precedence before writer-owned arrays'),
        candidate('calendar_single_packed_row',1,1,'Every edge all active writes must share addr[7:3]; one composite256-bit write mask. Current production NOT PROVEN'),
        candidate('calendar_four_packed_banks',1,4,'Map bank=addr[4:3], row=addr[7:5]; at most one distinct packed row per physical bank/edge. Current production NOT PROVEN')],
      general_candidate=dict(mapping='packed row=addr[7:3], lane=addr[2:0]; COLL address is packed-row directly',
        writer_arrays=5,reads_per_array=6,macro_count=30,macro_active_rows=32,macro_width=256,
        allocated_bits=983040,useful_replicated_bits=245760,owner_table_bits=768,
        owner_table='256x3 persistent FF state (<2kb), 5-way latest-writer select per word; no reset clearing. Codes5..7 map to defined owner for total-state relation',
        normal_read='read all five writer arrays for selected packed row, 8:1 lane selection then5:1 owner select',
        class5_read='five256-bit reads, independent owner select for each of8words',
        physical_read_output_bits_per_edge=7680,write_data_pin_bits=7680,
        dynamic_written_bits_per_edge=2304,
        control_copy_first_budget=dict(mask_copies=480,extra_scalar_data_FF=128,owner_read_selector_FF=78,
          status='STRUCTURAL ESTIMATE, not synthesized; write/address/control native fanout still owed'),
        macro_clk_to_q_ps={c:meta['timing'][c]['clk_to_q_ps'] for c in ['tt','ss','ff']},
        latency_credit=0,rate_credit=0),
      physical_screen=dict(status='NOT RUN; screen is not floorplan/native/PG/clock admission',
        macro_width_um=94.824,macro_height_um=41.04,literal_origin_lattice_um=43.2,
        coarse_pitch_um=[129.6,86.4],x_channel_um=34.776,y_channel_um=45.36,
        RF_plus_existing_reducer_macros=32,coarse_grid=[4,8],coarse_outline_um=[604.8,777.6],
        old_outline_um=[280.8,280.8],outline_ratio=(604.8*777.6)/(280.8**2),
        density='40-60% one full-width standard band requires actual mapped area and exact exception inventory; not proved',
        pin_access='actual LEF role/pin geometry, track census and per-face channel capacity still owed; no pins/6 gap formula assumed',
        planning_reach='outline exceeds405um; reject an unlanded global stage. Regional roots/registered seams need full transparent endpoint proof and explicit calendar price',
        clocks='30 new macro clocks require real-Lib clock roles and bound regional root inventory; no shared-root spread assumption',
        PG='fresh actual native PG census/protected/fixed/empty-net audit required; intermediate ordinary pre-global_connect nulls are not automatically defects'),
      regional_transport=regional_model(),
      blockers=['Current production host-config/command image not source-bound; no reduced write concurrency admitted',
        'General30 macro area116747.3088um2 alone exceeds old78848.64um2 outline',
        'Every stage/all drivers <=32 including mask broadcasts/reset/owner readmux remains unmeasured',
        'Full405reach and any added physical stages not composed with compiler staticcalendar',
        'No actual full-band density, PG, clockspread, SS/FF timing or production throughput proof'],
      next='Bind actual current command inventory; choose/model regional macro architecture; prove exact same-edge/state semantics; then source RTL and standalone native only')

def regional_model():
    """Conservative fixed-edge budgets, not a globally minimal floorplan."""
    variants=[]
    for gap in [43.2,86.4]:
        leaf=345.6; pitch=leaf+gap
        axis_hops=math.ceil(pitch/405-1e-9)
        outbound=2*axis_hops+1; inbound=outbound
        outline=3*leaf+2*gap+86.4
        variants.append(dict(name=f'six_read_local_leaves_gap{gap:g}',RF_macros=30,
          hard_leaves=6,macros_per_leaf=5,leaf_outline_um=[leaf,leaf],
          grid=[3,3],occupied_slots=[[0,0],[1,0],[2,0],[0,2],[1,2],[2,2]],owner_hub=[1,1],
          persistent_owner_bits=768,owner_state_replication=1,
          outline_um=[round(outline,6)]*2,interleaf_gap_um=gap,
          max_grid_segment_um=pitch/axis_hops,axis_hops=axis_hops,local_face_hops=1,
          command_transport_edges=outbound,return_segments=inbound,
          external_read_edge=outbound+inbound+2,read_delta_edges=outbound+inbound-1,
          write_commit_edge=outbound+1,write_delta_edges=outbound,
          command_bits_per_leaf=489,owner_token_bits_total=39,return_bits_total=452,
          transport_register_budget=6*489*outbound+452*(inbound-1)+39*outbound,
          FF_budget_scope='Fixed-interval transport only; excludes pin/reset/branch/clock copies',
          assumed_signal_layers=1,assumed_pitch_um=.048,assumed_usable_tracks_fraction=.5,
          available_tracks_per_independent_corridor=math.floor(gap/.048)*.5,
          channel_screen='FAIL' if math.floor(gap/.048)*.5<489 else 'PASS arithmetic only',
          qualification=False))
    return dict(status='MODEL_ONLY_NO_ENGINE',traffic_restrictions=False,
      edge_formula='commandE; localcaptureE+Hc; macroE+Hc+1; selectedE+Hc+2; externalE+Hc+2+K; deltaHc+K-1 vsoldE+3',
      distance_lower_bound='For a named pairD, segments>=ceil(ManhattanD/405); not proof that pair exists',
      conservative_full_body_pair=dict(L1_um=1382.4,segments=4,command_edges=4,return_segments=4,read_delta=7,write_delta=4),
      alternatives=variants,reticle_fit='NOT RUN: actual enlarged parent/die composition required',
      density='NOT RUN: actual synthesis area determines full-width band; no lowfill waiver',
      clock_PG_native='NOT RUN',rate_credit=0,
      compiler_obligation='Bind exact data/metadata/owner/reset/fault edges and all coherent replicas before source engine')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    d=model();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps(dict(status=d['status'],candidates=[dict(name=x['name'],macros=x['macros']) for x in d['candidates']],engine_ready=False)))
