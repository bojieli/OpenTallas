#!/usr/bin/env python3
"""Q5 real return correction sizing; not a PHY/CDC adoption certificate."""
def model():
    return {
        'schema':'opentallas.qwen.q5.landing.v1','target':'Qwen3-8B ROM AR only',
        'macs_per_cycle':0,'compute_intensity':0,'communication_intensity':'one 32-byte sector per HCLK edge',
        'replicas':128,'ecc_words_per_replica':4,'memory_bytes_cycle':{'HBM_payload':32,'HBM_check':4},
        'boundary_bits_cycle':{'controller_to_gate':313,'gate_to_CDC':281},
        'replication_cost':{'decode64_instances':512,'metadata_registers_bits':128*25,'payload_registers_bits':128*256,'CE_counter_bits':128*32},
        'outline_um':[230,230],'slot_area_um2':52900,'array_slot_area_mm2':128*52900/1e6,
        'route':{'pins_signal':313+281+36,'track_pitch_um':0.064,'escape_layers':2,'tracks_per_face':int(230/0.064)*2,'placement_utilization_target':0.55},
        'clock_period_ps':1024,'core_clock_period_ps':833.333,'setup_uncertainty_ps':60,'hold_uncertainty_ps':25,
        'latency':{'added_HCLK_edges_each_return':1,'added_first_read_ns':1.024,'steady_II_HCLK':1,'token_cost':'add once to each non-overlapped KV return dependency region, compose from actual layer calendar'},
        'native_AR_landing':{'MARGIN':1,'RSEL':1,'RNG':10,'LCRED':16,'maximum_core_credit_returns_per_edge':1,'actual_retirement':'decodedhead half consumed or intentionalVdrop; productionadapter owner qwen_system','wrapper_forwarding':'LCRED explicitly passed, not native default6','added_cycles_from_parameter_fix':0},
        'credit_contract':'prepaid CRED32 fits LD64 including added correction edge; only actual CDC retirement returns credit; UE quarantines debt',
        'storage_cost':{'HBM_check_overhead_fraction':0.125,'free_ECC_sideband_claim':False,'native_check_provider':'MISSING; do not silently tie to zero'},
        'gates':{'positive':'full 288b clean and every single-bit with exact metadata through actual native CDC','negative':'double-bit UE no crossing/no recycled credit, correction-disabled mutant, reset while debt requires parent fence','physical':'TT setup>=0 FF hold>=0 DRC0 with SS sensitivity'},
        'open':['actual HBM check-bit provider/PHY pins','existing native drained common-reset integration','full physical die adoption'],
        'CDC_storage_inventory':'native lmem/wmem/amem are flop arrays; SECDED rejected by confirmed ClaudeV28, Q5 HBM correctionbeforeCDC remains required',
        'adopted':False,
    }
if __name__=='__main__':
    import json
    print(json.dumps(model(),indent=2))
