#!/usr/bin/env python3
"""Full-shape h2 mutable operand SRAM protection, sized before successor RTL."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NEW='ot_sram_1r1w_128x256_m1_r2c2';OLD='ot_sram_1r1w_64x512_m1_r2c2'

def model():
    paths={name:f'physical/asap7_memory_macros_v2/{name}/{name}.json' for name in [NEW,OLD]}
    specs={name:json.loads((ROOT/f).read_text()) for name,f in paths.items()}
    new,old=specs[NEW],specs[OLD]
    return {
        'status':'MODEL_BEFORE_RTL_DEFAULT_OFF_NOT_ADOPTED',
        'scope':'One full16lane NC8 PFMAX384 banked core inside one half-rate owner. Existing arithmetic golden reductiontree and rounding unchanged.',
        'source_macro_specs_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in paths.values()},
        'logical_memory':dict(columns=8,rows_per_column=64,payload_bits_per_row=512,payload_SECDED_words=8,identity_SECDED_words=1,encoded_bits_per_row=648,physical_port_bits=768,logical_encoded_bits=8*64*648),
        'identity': 'Protected stored metadata64 = reservedzero22 +valid1 +generation32 +column3 +row6. Read request carries the same expected tuple through protected metadata registers. Metadata mismatch or UE quarantines before arithmetic acceptance. Context generation must be real protected local state advanced once per accepted arm without wrap, never guessed from simulation.',
        'macros':dict(name=NEW,per_column=3,total=24,physical_bits=24*128*256,raw_area_um2=24*new['area']['macro_area_um2'],old_name=OLD,old_total=8,old_raw_area_um2=8*old['area']['macro_area_um2']),
        'ports':dict(each_macro='1R1W on one core clock, real simultaneous different-address read/write supported',physical_bytes_read_per_column_cycle=96,physical_bytes_written_per_column_cycle=96,encoded_bytes_per_column_cycle=81,payload_bytes_per_column_cycle=64,per_8_columns_payload_read_bytes_per_core_cycle=512,MACs_added=0),
        'collision': 'Same-address read/write asserted together is explicitly faulted and quarantined; no reliance on read-during-write data ordering. Full reducer prdy/write/issue ordering must prove this absent on legal inputs.',
        'capture':dict(encoded_data_register_stages=2,encoded_data_bits_per_column=2*648,request_metadata_stages=3,request_metadata_bits_per_column=3*72,fault_dualrail_bits_per_column=2,total_registered_bits_per_column=2*648+3*72+2,old_RQ_RQ2_payload_bits_per_column=2*512,added_register_bits_all_columns=8*((2*648+3*72+2)-2*512)),
        'clock':dict(core='Actual existing half-rate gated core,1666.667ps nominal derived from833.333ps stream, not a relaxed SDC substitution',new_macro_SS_clk_to_q_ps=new['timing']['ss']['clk_to_q_ps'],old_macro_SS_clk_to_q_ps=old['timing']['ss']['clk_to_q_ps'],uncertainty_setup_ps=60,uncertainty_hold_ps=25,physical_ECC_decode_slack_ps=None),
        'energy_per_column_access_fJ':dict(new_SS_read=3*new['timing']['ss']['read_energy_fj'],old_SS_read=old['timing']['ss']['read_energy_fj'],new_SS_write=3*new['timing']['ss']['write_energy_fj'],old_SS_write=old['timing']['ss']['write_energy_fj'],ECC_and_clock_energy=None),
        'latency':dict(intended_issue_to_tree_core_edges=4,intended_added_core_cycles=0,measured_added_core_cycles=None,contract='Retain actual address-register→macro→encodedRQ→encodedRQ2 edges, decode/check before tree admission. If final ECC/check path fails physical timing, add a real stage and shift valid/index together, price two streaming cycles per added half-rate core cycle.'),
        'routing':'Three independent256bit macro buses percolumn instead of one512bit bus; common address/enable fanout3,8parallel payloadECCdecode slices+1identityslice percolumn. Actual track demand/halo/clock/SSFF and wholecore footprint pending.',
        'scope_holds':['actual protected generation/arm/read identity integration','minimum full512bit64row column exact/CE/UE/identity/collision gate','fullshape banked reduction exactness against unchanged golden','remaining core/shell mutablecontrol protection','actual24macro physical placement and SSFF closure','fullnative token latency recomposition'],
        'no_claim':'Raw macro area reduction is not total area or floorplan fit. Existing h2 routed evidence belongs to old8macro raw source and cannot qualify this successor.'
    }
if __name__=='__main__':print(json.dumps(model(),indent=2))
