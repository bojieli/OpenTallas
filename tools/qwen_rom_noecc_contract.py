#!/usr/bin/env python3
"""No-ECC image preparation for the existing Qwen266-bit macro geometry.

Only the low256 payload bits are consumed. Upper10 unused physical columns
remain allocated and receive zero. Does not generate a smaller macro or
change the unified model, engine RTL, KV SRAM/HBM, or historical evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TILE='rtl/hdc/ot_qwen_rom_tile_w12.sv'
MACRO='physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v'

def payload_word(word):
    if not isinstance(word,int) or word<0 or word >= 1<<256:
        raise ValueError('Expected unsigned256bit payload; encoded parity is not an input payload')
    return word

def contract():
    source=(ROOT/TILE).read_text();macro=(ROOT/MACRO).read_text()
    assert 'wire [PWB-1:0] rd = rom_rd[(p*CODE_BANKS + b)*266 +: PWB];' in source
    assert 'localparam integer PWB = 2 * W * 8;' in source
    assert 'localparam integer BITS = 266;' in macro
    assert 'if (ce_in)' in macro
    paths=[TILE,MACRO,'tools/mem_compiler/ecc.py','tools/mem_compiler/rom_gen.py','tools/qwen_rom_noecc_contract.py']
    return dict(schema='opentallas.qwen-rom-noecc-contract.v1',status='SOURCE_BOUND_MODEL_OWNER_REVIEW',
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        policy=dict(Qwen_ROM_ECC_required=False,DeepSeek_ROM_ECC_required=False,
                    configuration_ROM_ECC_required=False,scope='All ROM including weight, program, constant and configuration ROM',
                    descriptor_validity_preserved=True,address_bounds_preserved=True,
                    descriptor_identity_preserved=True,arithmetic_contract_preserved=True,
                    mutable_control_state_protection_preserved=True,
                    SRAM_protection_preserved=True,HBM_protection_preserved=True,
                    link_protection_preserved=True,pinned_jobs_unchanged=True,
                    KV_SRAM_changed=False,HBM_changed=False,golden_exact_required=True),
        fixed_Qwen_shape=dict(W=16,TG=4,banks=5,columns=2,words_per_macro=4096,
            physical_word_bits=266,consumed_payload_bits=256,unused_high_bits=10,
            capture_FF_bits=2560,ROM_count=10,physical_allocated_bits=10*4096*266,
            payload_capacity_bits=10*4096*256,unused_physical_bits=10*4096*10),
        image_rule='Unsigned256bit payload copied literally into low256; high10 zero. No ECC encoding/decoding. Address, CEhold and payload rounding unchanged.',
        actual_decoder_removed=0,actual_decoder_storage_removed_bits=0,
        physical_macro_area_credit=0,physical_macro_timing_credit_ps=0,
        model_owner_delta=dict(owner='Maxwell',pinned_original_unchanged=True,
            path='tools/uarch_model.py:QWEN_ECC and qwen_rom_need_mm2',
            old_projection_multiplier=266/256,new_noecc_projection_multiplier=1,
            affected_storage_projection_ratio=256/266,
            affected_storage_projection_reduction_fraction=10/266,
            scope='Remove explicit SECDED surcharge from payload-density projections only. Existing compiled266bit macro area/storage/pin/clock costs remain actual. No arbitrary subtraction from whole die or token latency.',
            DeepSeek_scope='Coordinate DS owner to audit its own payload/parity and explicit storage terms; this Qwen packet grants no DS source credit.'),
        compiler_incompatibility='rom_gen.tile_image requires spec.bits==tile_data_bits for ecc none; existing266 macro with256 payload needs explicit padded no-ECC adapter, not secded encoding to satisfy the width check.',
        current_capture_control_reset_failures_retained=True,new_macro_ready=False,PnR_admitted=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--payload-hex',type=Path)
    parser.add_argument('--physical-hex',type=Path)
    args=parser.parse_args()
    if bool(args.payload_hex)!=bool(args.physical_hex):parser.error('Both image paths required together')
    result=contract()
    if args.payload_hex:
        lines=args.payload_hex.read_text().splitlines()
        words=[payload_word(int(line.strip(),16)) for line in lines if line.strip()]
        if len(words)>4096:raise ValueError('Single macro bounded preparation accepts at most4096 rows')
        with args.physical_hex.open('x') as out:
            out.write(''.join(f'{word:067x}\n' for word in words))
        result['image']={'rows':len(words),'payload_sha256':hashlib.sha256(args.payload_hex.read_bytes()).hexdigest(),
            'physical_sha256':hashlib.sha256(args.physical_hex.read_bytes()).hexdigest(),
            'scope':'One physical-word image, not full checkpoint masks, no numerical token rerun'}
    with args.output.open('x') as out:json.dump(result,out,indent=2,sort_keys=True);out.write('\n')
