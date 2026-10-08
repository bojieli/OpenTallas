#!/usr/bin/env python3
"""Context-bound codec resource model; no physical/RTL qualification implied."""
import hashlib
import json
import math
from pathlib import Path
from hbm_result_relay_protection_model import crc32c

ROOT = Path(__file__).resolve().parents[1]

def context_codec_model():
    # message LSB: payload270, sequence16, source5, record16, owner73.
    columns = [crc32c(1 << i, 380) for i in range(380)]
    masks = [sum(1 << i for i, c in enumerate(columns) if (c >> j) & 1) for j in range(32)]
    # Eleven <=36-input chunks, reduced into three groups then one output.
    weights = [[((m >> (36*k)) & ((1 << 36)-1)).bit_count() for k in range(11)] for m in masks]
    xor_count = sum(max(n-1, 0) for row in weights for n in row) + 32*(8+2)
    encoder_ff = 3*380 + 32*(11+3+1) + 34
    # Carry independent context through all four checker stages, as well as
    # the complete physical frame. Two separate checker lanes are retained.
    checker_ff = 2*(4*(318+94) + 32*(11+3+1)) + 2*(16+7+1)
    ff, xor, gate = .37908, .13122, .08748
    encoder_raw = encoder_ff*ff + (xor_count+48)*xor + 51*gate
    checker_raw = checker_ff*ff + 2*(xor_count+32+16)*xor + (2*31+64)*gate
    syndromes = columns + [1 << i for i in range(32)]
    assert all(syndromes) and len(set(syndromes)) == 412
    return dict(schema='opentallas.hbm_result_context_codec.v1', selected=False,
      status='analytical-sizing-only; consumer RTL and physical qualification pending',
      logical_crc_bits=380, physical_frame_bits=318, hard_slices=6,
      layout='payload270[0:269],sequence16[270:285]; logical-only source5[286:290],record16[291:306],owner73[307:379]; transmitted CRC32[286:317]',
      polynomial_hex='1edc6f41', initial_crc=0, final_xor=0, direction='MSB-first',
      matrix_masks_hex=[f'{m:095x}' for m in masks],
      encoder_latency_cycles=3, arrival_checker_latency_cycles=4, consume_checker_latency_cycles=4,
      total_codec_cycles_per_result=11,
      encoder_matrix_xor2_count_upper=xor_count,
      encoder_stage_logic_depths=[max(math.ceil(math.log2(n)) if n>1 else 0 for row in weights for n in row),2,2],
      encoder_FF_bits=encoder_ff, duplicated_checker_FF_bits=checker_ff,
      all32_encoder_two_checker_FF_bits=32*(encoder_ff+2*checker_ff),
      encoder_raw_area_proxy_um2=encoder_raw, checker_raw_area_proxy_um2=checker_raw,
      encoder_area_at55pct_um2=encoder_raw/.55, checker_area_at55pct_um2=checker_raw/.55,
      all32_encoder_two_checker_area_at55pct_um2=32*(encoder_raw+2*checker_raw)/.55,
      coverage='All single/double-bit syndromes distinct/nonzero across logical380 plusCRC32; arbitrary multibit context substitutions can collide, not authenticated identity',
      reset_epoch_contract=[
        'Producer and both consumers independently install protected owner73/record16/source5 from the live reservation; never learn expected context from incoming data.',
        'Context remains immutable until transport, stored rows, consume pipeline, completion and durable obligations drain. A new reservation requires an explicit synchronized epoch transition.',
        'During reset all captures/consumption suppressed; clear transport and stored-row validity. Zero transport bits are reset filler, not a valid codeword for nonzero context.',
        'After reset, validate every encoded idle and valid beat once duplicated local fill count establishes pipeline fill. Received rv cannot disable CRC or sequence checks.',
        'Sequence increments per source beat modulo65536. Arrival checks expected beat identity; consumption checks independently protected stored expected row sequence, not current free-running sequence.',
        'Bound stale lifetime below65536 beats within one context and prevent context/epoch reuse while stale frames exist. Unsynchronized endpoint reset aborts reservation and requires drain/rearm.',
        'Either lane mismatch, CRC/context/sequence mismatch or control mismatch inhibits actual capture/consumption and raises persistent protected fault.'],
      required_gates=['Actual issuer independently supplies identical protected context to producer/arrival/consume endpoints',
        'Price protected stored expected-sequence/row association, context installation and epoch handshake in ingress model',
        'Price legal encoder fan-in, checker reassembly, changed slice wire demand and floorplan slots',
        'Measure full-shape codec RTL, fault injection, SS/FF margins and real consumer release/fault propagation'],
      source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'tools/hbm_result_relay_protection_model.py']})

if __name__ == '__main__':
    print(json.dumps(context_codec_model(), indent=2))
