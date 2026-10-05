#!/usr/bin/env python3
"""Existing-port format checks and conditional storage bounds; no new hardware."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

import w16_w19_resident_bounds as B
import w16_w19_consumer_contracts as C

ROOT = Path(__file__).resolve().parents[1]
OUT = 'results/uarch/w16_w19_hardware_formats_20261001'
HCP = 'rtl/hdc/hbm/ot_hdc_v41x_hcp_hbm_window.sv'
HCP_RECORD = 'results/rtl/hdc_v41x_hcp_hbm_exact.json'
GATHER = 'rtl/hdc/v41/ot_hdc_engram_gather.sv'
SLICE = 'rtl/hdc/v41x/ot_hdc_v41x_egather.sv'
WINDOW = 'rtl/hdc/v41x/ot_hdc_v41x_window_kv_blocks.sv'


def ports(path, module):
    text = (ROOT / path).read_text()
    match = re.search(r'\bmodule\s+' + re.escape(module) + r'\b(.*?)\);', text, re.S)
    B.require(match is not None, 'missing module: ' + module)
    return {name: dict(direction=direction, packed_range=width.strip() if width else None)
            for direction, width, name in re.findall(
                r'\b(input|output)\s+(?:wire|reg)\s*(\[[^\]]+\])?\s*(\w+)', match[1])}


def uniform_scale_compatible(scales):
    """Necessary scale condition for current beat0-latched gather; no numerical gate."""
    B.require(len(scales) == 8 and all(type(x) is int and 0 <= x < 256 for x in scales),
              'invalid eight-block scale row')
    return len(set(scales)) == 1


def fp32_bank_bound(elements, banks=8, lanes=8, window_words=256):
    B.require(all(type(x) is int and x > 0 for x in (elements, banks, lanes, window_words)),
              'invalid FP32 bank geometry')
    words = (elements + banks * lanes - 1) // (banks * lanes)
    return dict(source_fp32_bytes=elements * 4, minimum_words_per_bank=words,
                minimum_bank_bytes=words * lanes * 4,
                minimum_total_bank_bytes=words * banks * lanes * 4,
                existing_default_window_bytes=window_words * banks * lanes * 4,
                source_fits_default_window=words <= window_words,
                bound_scope='Equal-bank storage lower bound only; no full-shape bank image or execution proof')


def require_deployment(contract):
    """A software execution site or source dtype cannot supply a deployment contract."""
    required = ('format', 'read_port', 'resident_owner', 'deployed_bytes', 'region')
    B.require(isinstance(contract, dict) and all(contract.get(k) is not None for k in required),
              'missing actual format/read-port/ownership/region contract')
    B.require(type(contract['deployed_bytes']) is int and contract['deployed_bytes'] > 0,
              'unknown/zero deployed byte extent')
    B.require(contract.get('connected_TP96_source') and contract.get('source_sha256'),
              'component/software-only binding cannot qualify TP96 deployment')
    # Necessary fields only. No full-fit, physical or latency verdict is returned.
    return True


def build():
    inv = B.read(B.INVENTORY)
    C.parent_agreement(inv, B.read(C.VERIFY))
    B.inventory_bounds(inv)
    hcp, gather, slice_text = ((ROOT / p).read_text() for p in (HCP, GATHER, SLICE))
    B.require('parameter integer HW = 8' in hcp and 'parameter integer WORDS = 256' in hcp
              and 'parameter integer HAW = 20' in hcp and '.WB(HW*32)' in hcp
              and 'b * WORDS * SPW' in hcp, 'HCP component bank geometry changed')
    B.require('s1_b0 ? s1_side : s1_scl' in gather and
              '(r_beat == 0) ? rd[263:256] : scl' in slice_text,
              'Engram scale transport changed; requalify matching format')
    tensor = {i['tensor']: i for i in inv['items']}
    engram = []
    for layer in (1, 14):
        w, s = (tensor[f'layers.{layer}.engram.embed.{k}'] for k in ('weight', 'scale'))
        B.require(w['shape'][1] == 256 and s['shape'] == [w['shape'][0], 8], 'Engram source shape drift')
        engram.append(dict(layer=layer, rows=w['shape'][0], source_code_bytes_per_row=256,
                           source_scale_bytes_per_row=8, source_row_bytes=264))
    matrices = [i for i in inv['items'] if i['tensor'].endswith(('.hc_attn_fn', '.hc_ffn_fn'))]
    B.require(len(matrices) == 80 and all(i['dtype'] == 'F32' and i['shape'] == [24, 20480]
              for i in matrices), 'HC full-source geometry drift')
    bound = fp32_bank_bound(24 * 20480)
    historical = B.read(HCP_RECORD)
    B.require(historical['fixture']['K'] == 640 and historical['hbm_layout']['bank_count'] == 8,
              'historical HCP scope changed')
    pin_currency = {p: B.sha(p) == h for p, h in historical['source_sha256'].items()
                   if (ROOT / p).is_file()}
    window_record = B.read('results/rtl/v41x_packed_kv_mapping.json')
    B.require(window_record['payload_bytes_per_row'] == 528 and
              window_record['hbm_pitch_bytes_per_row'] == 544, 'historical window layout changed')
    contracts = {category: {field: None for field in
                 ('format', 'read_port', 'resident_owner', 'deployed_bytes', 'region')}
                 for category in ('constants', 'embedding', 'Engram', 'KV', 'index')}
    refusals = {}
    for category, contract in contracts.items():
        try:
            require_deployment(contract)
        except B.Refusal as exc:
            refusals[category] = str(exc)
        else:
            raise B.Refusal('unexpected actual deployment credit')
    paths = [B.INVENTORY, C.VERIFY, B.PROGRAM, C.ISA, C.GOLDEN, HCP, HCP_RECORD,
             'rtl/hdc/hbm/ot_hdc_v41x_weight_window.sv',
             'rtl/test/tb_hdc_v41x_hcp_hbm_exact.sv', GATHER, SLICE, WINDOW,
             'results/rtl/v41x_packed_kv_mapping.json',
             'results/rtl/hdc_v41_engram_gather_campaign.json',
             'rtl/gpu/ot_gpu_sm_v.sv', 'rtl/gpu/ot_gpu_expert_fetch.sv',
             'rtl/test/tb_w19_fetch_sm.sv', 'tools/uarch_model.py',
             'tools/w16_w19_consumer_contracts.py', 'tools/w16_w19_resident_bounds.py',
             'tools/w16_w19_address_prerequisite.py', 'tools/w16_measured_calibration.py',
             'tools/w16_w19_hardware_formats.py', 'tests/test_w16_w19_hardware_formats.py']
    return dict(schema='opentallas.w16.w19.existing_hardware_format_boundary.v1',
        base_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        Engram=dict(source_tables=engram, source_scale_granularity_columns=32,
            existing_gather_scale_granularity_columns=256,
            verdict='REFUSED_FORMAT_MAPPING: eight source scales versus beat0-latched single row scale',
            equal_row_bytes_do_not_prove_equal_encoding=True,
            ports={GATHER: ports(GATHER, 'ot_hdc_engram_gather'),
                   SLICE: ports(SLICE, 'ot_hdc_v41x_egather_slice')},
            alternative_decoder_or_adapter_qualified=None,
            witness=dict(kind='synthetic unit-test discriminant, not checkpoint or RTL measurement',
                         code=56, scale_bytes=list(range(127, 135)),
                         blockwise_exact_values=[1 << i for i in range(8)],
                         beat0_latched_values=[1] * 8)),
        HC=dict(existing_component_format='Eight banks; HW FP32 words per synchronous bank read; 256-bit HBM sectors',
            ports=ports(HCP, 'ot_hdc_v41x_hcp_hbm_window'), matrix_count=80,
            full_source_matrix_bound=bound,
            source_matrix_aggregate_bytes=sum(i['stored_bytes'] for i in matrices),
            historical_measurement_scope=historical['claim_boundary'],
            historical_existing_file_pin_currency=pin_currency,
            TP96_consumer_binding=None, full_shape_image_mapping=None,
            scale_base_bias_and_norm_ports=None),
        KV=dict(existing_component_ports=ports(WINDOW, 'ot_hdc_v41x_window_kv_blocks'),
            historical_payload_bytes=528, historical_sector_pitch_bytes=544,
            scope=window_record['scope'], TP96_mapping=None,
            note='Historical pitch is conditional; do not substitute it for actual TP96 resident allocation'),
        SM=dict(payload_bits=1088, payload_scope='Matrix operands only: 128B weights +8B exponents',
            note='Accepted256 transport does not establish DU/embedding/Engram/KV/index read ports'),
        actual_deployment_contracts=contracts, deployment_refusals=refusals,
        W19_handoff=dict(owner='Euler / actual accepted256 transport', acknowledgement=False,
            first_blocker='Supply an actual eight-scale-per-row Engram consumer/transport contract; existing gather format is incompatible',
            remaining='Identify actual non-SM read ports and deployed images, then resident rank/stack ownership and bases/extents. HC FP32 component format alone supplies no full-shape placement.',
            allocation_gate='Apply source-backed per-stack stack_bound/reservations_fit only after deployment contracts are supplied'),
        model_source_changed=False, measured_service_cycles=None, schedule_latency_ns=None,
        full_fit=False, adopted=False, pins={p: B.sha(p) for p in paths})


def check(record):
    for path, digest in record['pins'].items():
        B.require(B.sha(path) == digest, 'pin drift: ' + path)
    fresh = build()
    fresh['base_commit'] = record['base_commit']
    B.require(fresh == record, 'hardware format boundary does not reproduce')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--out', type=Path)
    mode.add_argument('--check', type=Path)
    args = ap.parse_args()
    try:
        if args.check:
            check(json.loads(args.check.read_text()))
        else:
            data = build()
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open('x') as f:
                json.dump(data, f, indent=2, sort_keys=True)
                f.write('\n')
        print('PASS: source-backed format boundary; Engram mapping and actual deployment REFUSED')
    except (B.Refusal, FileExistsError) as exc:
        ap.exit(2, 'REFUSED: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
