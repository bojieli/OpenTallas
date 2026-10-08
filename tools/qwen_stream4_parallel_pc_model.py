from pathlib import Path
import json, hashlib, math
ROOT=Path(__file__).resolve().parents[1]
def model(root=ROOT):
    r=Path(root)
    record=dict(schema='opentallas.qwen.parallel_pc.prebuild.v1',default_OFF=True,MACs_per_edge=0,replicas=128,
     inherited_model='tools/qwen_stream4_protected_model.py',inherited_rings=['landing281x64','write289x16','ACK9x64'],ROM_ECC=False,
     source_bytes_per_HCLK_edge=35.125,destination_bytes_per_CLK_edge=35.125,coded_bits_per_edge=504,
     simultaneous_raw_lanes=2,raw_leaf='ot_qwen_stream4_cdc_pc RSEL1 RNG10 LD64',coded_lane_bits=[256,248],
     lane_owner_metadata_bits=25,lane_padding_bits=8,raw_landing_storage_bits=2*281*64,
     replaced_landing_storage_bits=504*64,storage_delta_bits=2*281*64-504*64,
     raw_landing_control_FF_per_lane=38+29+30+650+281+4,
     replaced_checked_RSEL_FF=2*18*64,ACK_debt_counter_bits=7,ACK_debt_fault_bits=1,ACK_debt_checked_FF=16,ACK_debt_HCLK_dual_rail_FF=32,
     finite_ACK_debt_capacity=64,admission='existing w_room AND checked debt<AD; increment actual acceptedW; decrement ONLY wd_v && consumer wd_accept; never warm-clear',
     read_ports_per_PC=2,write_ports_per_PC=2,read_mux_NAND2=2*281*63*3,
     replaced_read_mux_NAND2=504*63*3,local_code_tracks=504,local_lane_tracks=562,
     wire_stages='existing LOCAL_WIRE_SPANS unchanged on504 coded bits and actual checked control/credit; no new external transport',
     clocks=dict(CLK_ps=833.333,HCLK_ps=1024,setup_uncertainty_ps=60,hold_uncertainty_ps=25),
     added_destination_capture_edges=1,publication_to_output_bound_destination_edges=7,
     latency_composition='replace landing six-destination-edge term by seven after same source encode/wire/pointer visibility; every36layer refill remains owner-composed, not startup-only',
     quiet='all inherited encoder/pointer/delivery/cache/credit/completion debt empty AND checked acceptedW-minus-validatedACK=0; HCLK sees complementary SYNC2 debt rails',
     actual_slot_fit=None,physical_qualified=False,loaded_raw_leaf_requalification_required=True,
     routing_capacity='inherited local40um channel,3preferred-direction layers at48nm =>2499 tracks;562 coded-lane tracks plus unchanged other ring/cache/control paths, no fullwidth die allocation claim',
     bounds='full36*131072 MEM_WORDS; PC7/slot/piece/kind/wrap sealed by existing codec; raw owner metadata AND code seal must match protected fetch ordinal',
     fault='lane validity/owner mismatch and raw faults fail closed; codeCE repaired by existing decoder; UE/seal/DMR faults quarantine without release; raw timing credit never borrowed')
    delta=record['storage_delta_bits']+2*record['raw_landing_control_FF_per_lane']-record['replaced_checked_RSEL_FF']+48
    record['estimated_FF_delta_per_PC']=delta
    record['estimated_cell_area_delta_per_PC_mm2']=(delta*.2916+(record['read_mux_NAND2']-record['replaced_read_mux_NAND2'])*.08748+math.ceil(delta/7)*.10206)/1e6
    record['source_SHA256']={x:hashlib.sha256((r/x).read_bytes()).hexdigest() for x in ['tools/qwen_stream4_protected_model.py','rtl/hdc/kv/ot_qwen_stream4_cdc_pc.sv','rtl/hdc/kv/ot_qwen_s4_protected_ring.sv','rtl/hdc/kv/ot_qwen_s4_protected_pc.sv']}
    return record
