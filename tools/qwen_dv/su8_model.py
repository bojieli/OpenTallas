"""Source-pinned SU control split model; no default implementation adoption."""
from pathlib import Path
import hashlib,json,math

ROOT=Path(__file__).resolve().parents[2]
INVENTORY='results/arch/qw_suvm8_1020/su8_model0720/inventory.json'

def model(root=ROOT):
    root=Path(root);record=json.loads((root/INVENTORY).read_text())
    if record['schema']!='opentallas.qwen.su_control_inventory.v1':raise ValueError('foreign SU inventory')
    if hashlib.sha256((root/record['source']).read_bytes()).hexdigest()!=record['source_sha256']:
        raise ValueError('SU inventory source changed; remeasure before RTL')
    if record['omitted_module']!=[dict(instance='u_vm.',module='qfd_dv_s5_vm7')]:
        raise ValueError('unowned omitted storage/control in inventory')
    inputs=dict(start=1,program_word=457,retire=1,last=1,lane_fault=8,kv_write=8,rd_v=1,red_busy=1,red_fault=1,landed_vm_write=8)
    outputs=dict(core_group_record=244,group_valid=3,lane_valid=8,lane_addresses=768,not_ready=1,idle=1,fault=1,progress=16,rows=16)
    boundaries=sum(inputs.values())+sum(outputs.values())
    ff=record['actual_control_ff']-record['btab_payload_flops_removed']+boundaries+2
    base_area=record['control_only_mapped_area_um2']-256*record['dff_area_um2']
    area=base_area+(boundaries+2)*record['dff_area_um2']
    # Full retained prefix/replication sizing headroom; this is a cost envelope,
    # not a substitute for actual post-source synthesis/census.
    max_area=area+base_area/2
    face=dict(N=outputs['lane_addresses'],E=outputs['core_group_record']+outputs['group_valid'],
              S=sum(outputs.values())-outputs['lane_addresses']-outputs['core_group_record']-outputs['group_valid']+2,
              W=sum(inputs.values()))
    lattice=43.2;side=math.ceil(max(face.values())/6/lattice)*lattice
    # Four signal layers, minimum ASAP7 M2 pitch48nm: exact track count is
    # measured at native physical admission; this conservative projection
    # reserves only25% for crossing records after PG/clock/local-route usage.
    tracks=math.floor(side/0.048)*4*0.25
    return dict(schema='opentallas.uarch.qwen_su8.v1',adopted=False,status='MODEL_PERMITS_SOURCE_PROTOTYPE_ONLY',
      basis=record,input_bits=inputs,output_bits=outputs,MACs_per_cycle=0,compute='integer address/control generation; numerical SU datapath stays in lane leaves',
      SRAM_bits=0,external_storage='VM8b owns18 real SRAM macros; SU8 contains no dynamic tables',
      vector_beats_per_cycle=1,boundary_bits_per_cycle=sum(inputs.values())+sum(outputs.values()),
      input_bytes_per_cycle=sum(inputs.values())/8,output_bytes_per_cycle=sum(outputs.values())/8,
      existing_onebit_muxes=record['actual_1bit_mux'],new_boundary_muxes=0,new_boundary_flops=boundaries,
      extra_start_alignment_flops=2,projected_ff=ff,replica_plan='four current-address copies and eight lane offsets retained; replace768 raw stride copies by768 precomputed offsets; no added cadence/edges',
      measured_baseline_area_um2=base_area,projected_min_area_um2=area,projected_budget_area_um2=max_area,
      outline_candidate_um=[side,side],face_bit_counts=face,face_density_per_um={k:v/side for k,v in face.items()},
      perimeter_pin_limit_per_um=6,pin_bound_min_side_um=max(face.values())/6,
      projected_fill_budget=max_area/(side*side),pin_bound_fill_exception_required=True,
      routing=dict(signal_layers=4,pitch_um=0.048,record_track_capacity_at25pct=tracks,max_face_demand=max(face.values()),passes=tracks>=max(face.values()),qualification='projection only; actual reachable pin/layer/channel audit owed'),
      latency=dict(observed_command_accept_before=2,observed_command_accept_su8=6,vm_read_answer_before=2,vm_read_answer_vm8=4,
                   vm_write_read_min_before=1,vm_write_read_min_vm8=3,table_write_added=2,slice_lane_roundtrip_added=2,
                   decomposition='control inputs/state shifted3 edges plus registered outputs1; start pin1+two alignment stages, VM answer+2 then SU pin1',
                   btab='bypass SU to group/lane relay; no added SU word-stage on BTAB'),
      critical_source='precompute lane*stride before lane-address register, kept prefix current+offset; actual source depth/census mandatory',
      not_qualified=['source equivalence/causals','actual full source synthesis/depth/fanout','unified parent slot binding','native per-operation calendar emission GAP','actual VM8b closure','actual clocks/reach/PG/pins'])

if __name__=='__main__':print(json.dumps(model(),indent=2))
