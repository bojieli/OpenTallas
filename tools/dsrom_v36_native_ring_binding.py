#!/usr/bin/env python3
"""Read-only V36 source inventory; static selection is never compiled evidence."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CAP='rtl/dsrom_sys/s81_capture_parent/'
CORE='rtl/w17_runtime/hdc/v41x/fastpp_pc21/l20/ot_hdc_core_v41x.sv'
PATHS=[CAP+'selection.json',CAP+'sources.f',CAP+'ot_hdc_core_v41x.sv',CORE,
       'tools/dsrom_s81_system_sources.py','tools/hdc_isa_v41.py','tools/hdc_program_v41.py',
       'tools/hdc_replay_v41.py','tools/v41_fullshape_isa.py','tools/v41_fullshape_program_bind.py',
       'rtl/test/v41_runtime/s81_selected/w17_current_fastpp_c8_s81_rt.cpp',
       'results/host/s81_native_head_capture_terminal_20261004/terminal.json',
       'results/host/s81_head_capture_binding_fix_20261004/terminal.json']
def inventory(root):
    selected=json.loads((root/(CAP+'selection.json')).read_text())
    hashes={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in PATHS}
    return dict(schema='opentallas.dsrom.v36-native-ring-binding.v1',
        status='CONDITIONAL_PENDING_ACTUAL_COMPILED_PROGRAM_PROVIDER',
        observed_source_sha256=hashes,
        static_selection=dict(top=selected['top'],parameters=selected['parameters'],
            sources_file=selected['sources_file'],host_cpp=selected['host_cpp'],
            functional_parent_measured=selected['functional_parent_measured'],
            physical_admission=selected['physical_admission'],
            listed_core=CAP+'ot_hdc_core_v41x.sv',
            core_matches_manifest=hashes[CAP+'ot_hdc_core_v41x.sv']==selected['source_sha256'][CAP+'ot_hdc_core_v41x.sv'],
            remaining_manifest_hashes_validated=False,compiled_receipt=False),
        installer=dict(source='tools/dsrom_s81_system_sources.py',CORE=CORE,
            generated_core='native/ot_hdc_core_v41x.sv then capture/WAVE hooks',
            original_source_unchanged=True),
        ABI=dict(default_core_NSLOT=1,static_selection_core_NSLOT_override=False,
            ISA_source='tools/hdc_isa_v41.py',SLOTW8_DYN=25,SLOTP8_DYN=26,TOK32_DYN=27,
            program_source='tools/hdc_program_v41.py',
            compressor_condition='ratio2 && layout.ring>2',
            program_fields=dict(ME='me_d_obase=SLOTW8',SU=['a_d=SLOTP8','b_d=SLOTP8','c_d=SLOTP8']),
            canonical_reduced_fixture_values=dict(DYN25='(position & 7)<<2',DYN26='((position>>1)&3)<<7'),
            fullshape_record_stride_and_ME_address_units_bound=False,
            actual_emitted_program_bound=False,actual_fullshape_ISA_width_bound=False),
        current_clones=dict(capture_parent='DYN25/26 and TOK32 initialized only under NSLOT>1',
            fastpp_pc21_l20='same NSLOT>1 guard; unchanged'),
        qualification_prerequisites=dict(canonical_source='codex/mtp-numerical-repair-20261009',
            canonical_tip_reported='bfd8bcf8b',canonical_default_enable='3dea693b1',same_source_gates=[14,15,19,20],
            all_four_terminal_qualified=True,
            required_provider=['actual compiled source list and source hashes','actual program bytes/config/ISA fields',
                'effective NSLOT1 and ring8 elaboration','executed DYN25/26 instruction and visibility trace',
                'existing native sequencer contextual physical source/budget']),
        historical_receipts=dict(native_head='exit1/source16d35fbeb; head+END only, no fulltoken or physical credit',
            host_capture_fix='compile/linkPASS/source0613be50f; host-only, no runtime/native rebuild'),
        fullshape_provider=dict(source='tools/hdc_replay_v41.py',layout='ShapeLayout',
            allocated_slot_elements='4*hd, two records',
            unpartitioned_compressor='SLOTW/DYN18; no SLOTP8 or rollback_ring option',
            TP_compressor='ratio1 only; ratio2 slot ring explicitly not emitted',
            ring8_compiler_selected=False,production_consumer_witness=False),
        physical_context=dict(actual_selected_sequencer_bound=False,standalone_route_allowed=False,
            WFC_SOURCE_dispatcher_is_native_HDC_sequencer=False),
        scope=dict(native_port_applied=False,new_RTL=False,new_routes=False,
            auth_leases_mirrors_reset_epochs_added=False,reintroduces_retired_hist_ring_integration=False))
def model():
    return dict(schema='opentallas.dsrom.v36-native-ring-model.v1',adopted=False,
        status='conditional pending actual program/source/physical context',
        mechanism='initialize existing DYN25/26 for actual qualified one-position ring8; TOK32 remains multi-position only',
        MACs_per_cycle=0,compute_intensity=0,memory_bytes_per_cycle_delta=0,
        boundary_bits_per_cycle_delta=0,external_ports_added=0,
        storage=dict(existing_DYN_entries=2,new_entries=0,variable_bits_per_position=5,
            synthesis_live_bit_delta_upper=5),
        mux_demux=dict(local_selector_upper=16,variable_mux_arms_upper=80),
        fanout=dict(variable_bit_sinks_upper=16),
        replicas=dict(minimum_component=1,production_count='requires actual compiled hierarchy'),
        routing=dict(new_external_tracks=0,local_signal_sink_upper=80,
            existing_channel_capacity='unbound until selected sequencer context identified'),
        area=dict(existing_slot='unbound',conditional_logic_upper='5 live DFF bits and80 local mux arms',
            actual_mapped_area_um2=None,slot_fit=False),
        latency=dict(canonical_reported_added_decode_cycles=0,native_measured_added_cycles=None,changed_golden_order=False,
            production_clock='existing selected sequencer; not inferred from SOURCE dispatcher',
            single_user_credit=0,contextual_measurement_required=True),
        implementation_gate='all same-source numerical14/15/19/20 + actual compiled ring8 provider before targeted native port',
        physical_gate='existing sequencer context only; no standalone route')
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'inventory.json').write_text(json.dumps(inventory(a.root),indent=2)+'\n')
    (a.output/'model.json').write_text(json.dumps(model(),indent=2)+'\n')
if __name__=='__main__':main()
