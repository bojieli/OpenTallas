"""HBM index service successor sizing, before implementation; no adoption credit."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def model():
    return dict(schema='opentallas.hbm_index_service.v1',status='PREBUILD_NOT_QUALIFIED',
        source_sha256={'tools/uarch_model.py':hashlib.sha256((ROOT/'tools/uarch_model.py').read_bytes()).hexdigest()},
        geometry=dict(TP=96,stack_count=4,PCs_per_stack=32,blocks_per_stack=342,keys_per_block=8,key_bytes=68,
            placement='stack=floor(owned_block_ordinal/342); stack_sector=17*(owned_block_ordinal%342)+sector_in_block; pc=stack_sector%32; j=stack_sector//32'),
        compute=dict(MACs_per_cycle=0,communication_bytes_per_cycle=1024,bytes_per_PC_per_cycle=32),
        boundaries=dict(index_ports_per_stack=8,line_bits=1088,tag_bits=10,valid_bits=1,tracks_per_stack=8792,
            reverse_credit_bits=8,routing_channel_capacity=None,fit='REQUIRES_R25I_CHANNEL_CHECK'),
        buffering=dict(scorer_port_depth=64,line_payload_bytes=69632,
            service_return_reservation='Reserve line capacity before each read; never depend on response backpressure',
            service_reassembly='32-byte sectors cross 136-byte lines; tag and out-of-order reassembly mandatory',
            service_return_words=32*64,service_payload_bytes=32*64*32,
            service_SECDED_check_bits=32*64*10,service_SECDED_read_cycles=2,service_SECDED_write_cycles=1,
            valid_scoreboard_bits=32*64,protection_implemented=False,
            service_reassembly_area=None,physical_macro_inventory=None),
        replicas=dict(services_per_die=4,PC_engines_per_die=128,output_ports_per_die=32,
            descriptor_fanout_per_stack=32,mux_demux='sector byte fragments to 8 line ports; not a free wire'),
        latency=dict(stack_bytes_max=342*544,HBM_lower_bound_cycles_1p2GHz_at_1TBps=342*544*1.2e9/1e12,
            scorer_min_ingest_cycles=171,write_mapping_added_cycles=0,measured_service_cycles=None,
            token_composition='8 index layers; old one-PC kind2 path remains unqualified against full-stack price'),
        write_mapping=dict(default_off=True,window_CKV_unchanged=True,arithmetic_unchanged=True,
            shadow_sector_index='retain die-global block-relative offset; placement affects addresses only'),
        line_transport=json.loads((ROOT/'results/rtl/hbm_index_service_20261008/line_cdc_before_rtl.json').read_text()),
        collector=dict(sector_boundary_bits_per_PC=269,central_cut_PCs=16,
            central_cut_payload_bits=4304,reverse_pop_bits=32,
            legacy_band_height_um=259,M4_cross_pin_pitch_um=.096,
            payload_pin_run_um=413.184,one_M4_face_fit=False,
            required_change='explicit multi-layer collector capacity or widened collector boundary; actual relay latency and mutable/link protection must be priced',
            segmented_production_integration=False),
        signoff=dict(TT_setup_ps=0,FF_hold_ps=0,DRC=0,SS='sensitivity',qualified=False),adopted=False)
if __name__=='__main__':print(json.dumps(model(),indent=2))
