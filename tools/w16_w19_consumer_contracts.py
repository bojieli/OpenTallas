#!/usr/bin/env python3
"""Bind existing non-SM metadata to reference consumers, without physical credit."""
import argparse
import ast
import hashlib
import json
import subprocess
from collections import defaultdict
from pathlib import Path

import w16_w19_resident_bounds as B

ROOT = Path(__file__).resolve().parents[1]
VERIFY = 'results/rtl/w19_checkpoint_production_20261001/non_SM_inventory_parent_verification.json'
ISA = 'tools/w19_hbm_tp96_isa.py'
GOLDEN = 'tools/hdc_golden_v41.py'
OWNER_COMMIT = '910fb60fc'
OWNER_PATH = 'tools/w19_checkpoint_pack.py'
OUT = 'results/uarch/w16_w19_consumer_contracts_20261001'


def parent_agreement(inv, parent):
    B.require(parent['status'] == 'PASS_AT_STORED_METADATA_SCOPE', 'parent metadata verdict')
    B.require(parent['inventory_sha256'] == B.sha(B.INVENTORY), 'parent inventory identity')
    for key in ('checkpoint_revision', 'checkpoint_index_sha256', 'programme_sha256', 'stored_bytes'):
        B.require(parent[key] == inv[key], 'parent metadata mismatch: ' + key)
    B.require(parent['unique_tensors_verified'] == len(inv['items']), 'parent tensor count mismatch')
    groups = defaultdict(lambda: {'tensors': 0, 'stored_bytes': 0, 'dtype_bytes': defaultdict(int)})
    for item in inv['items']:
        group = groups[item['group']]
        group['tensors'] += 1
        group['stored_bytes'] += item['stored_bytes']
        group['dtype_bytes'][item['dtype']] += item['stored_bytes']
    B.require(dict(groups) == parent['groups'], 'parent group/dtype accounting mismatch')
    B.require(set(inv['header_bindings']) == set(parent['header_bindings']), 'parent header set mismatch')
    for name, h in inv['header_bindings'].items():
        p = parent['header_bindings'][name]
        B.require(h['sha256'] == p['framed_header_sha256'] and h['header_bytes'] == p['header_bytes']
                  and inv['shards'][name]['bytes'] == p['file_bytes'], 'parent header identity mismatch')
        B.require(p['full_blob_rehashed'] is False, 'unsupported full-blob audit promotion')
    B.require(parent['physical_format_or_replication_qualified'] is False and parent['adopt'] is False,
              'unsupported physical/adoption promotion')


def functions(path):
    return {n.name: n for n in ast.walk(ast.parse((ROOT / path).read_text())) if isinstance(n, ast.FunctionDef)}


def binding(suffix):
    if suffix in ('hc_attn_fn', 'hc_attn_scale', 'hc_attn_base'):
        return 'hc_mixes', 'attn', 'hc_mixes'
    if suffix in ('hc_ffn_fn', 'hc_ffn_scale', 'hc_ffn_base'):
        return 'hc_mixes', 'ffn', 'hc_mixes'
    mapping = {
        'attn_norm.weight': ('hc_pre_norm', 'attn', None),
        'ffn_norm.weight': ('hc_pre_norm', 'ffn', None),
        'attn.q_norm.weight': ('q_norm_kv_row', None, None),
        'attn.kv_norm.weight': ('q_norm_kv_row', None, None),
        'attn.attn_sink': ('attend', None, None),
        'ffn.gate.bias': ('route', None, None),
        'attn.compressor.norm.weight': ('compressor', None, None),
        'attn.indexer.wk.weight': ('compressor', None, None),
        'attn.indexer.k_norm.weight': ('compressor', None, None),
        'engram.q_weight': ('engram_mix', None, None),
        'engram.k_weight': ('engram_mix', None, None),
        'norm.weight': ('final_norm', None, None),
        'engram.embed.weight': ('engram_fetch', None, None),
        'engram.embed.scale': ('engram_fetch', None, None),
        'embed.weight': ('host_input_lookup', None, None),
        'ffn.gate.bias_vl': ('unreferenced_in_AR_executor', None, None),
    }
    B.require(suffix in mapping, 'unsupported reference consumer mapping: ' + suffix)
    return mapping[suffix]


def build():
    inv, parent, program = B.read(B.INVENTORY), B.read(VERIFY), B.read(B.PROGRAM)
    parent_agreement(inv, parent)
    bounds = B.inventory_bounds(inv)
    isa, golden = functions(ISA), functions(GOLDEN)
    families = {}
    for item in inv['items']:
        name = item['tensor']
        layer = int(name.split('.')[1]) if name.startswith('layers.') else 'head'
        suffix = '.'.join(name.split('.')[2:]) if name.startswith('layers.') else name
        fn, which, nested = binding(suffix)
        family = families.setdefault(suffix, dict(source_group=item['group'], source_dtype=item['dtype'],
            tensors=0, stored_bytes=0, reference_function=fn, golden_function=nested,
            reference_token_calls=[], hardware_consumer_contract=None, deployed_encoding=None,
            resident_replica_count=None, resident_rank_stack_map=None, reservations=None))
        family['tensors'] += 1
        family['stored_bytes'] += item['stored_bytes']
        if fn in ('host_input_lookup', 'unreferenced_in_AR_executor'):
            family['reference_scope'] = ('host input embedding; no compiled resident lookup opcode' if
                fn == 'host_input_lookup' else 'VL bias has no reference read in this AR executor; disposition pending')
            continue
        node = isa['f_' + fn]
        constants = {n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        if nested:
            gnode = golden[nested]
            B.require('hc_{which}_{s}' in ast.unparse(gnode) and 'hc_mixes' in ast.unparse(node),
                      'dynamic HC consumer changed')
        elif fn not in ('engram_fetch',):
            B.require(suffix in constants, 'reference tensor read changed: ' + suffix)
        matches = [op for obj in program['layers'] if obj['layer'] == layer for op in obj['ops']
                   if op.get('fn') == fn and (which is None or op.get('which') == which)]
        B.require(len(matches) == 1, 'missing/ambiguous reference opcode: ' + name)
        op = matches[0]
        family['reference_token_calls'].append(dict(layer=layer, opcode_id=op['id'], ranks=op['ranks']))
        family['reference_function_ast_sha256'] = hashlib.sha256(ast.dump(node).encode()).hexdigest()
    B.require('bias_vl' not in (ROOT / ISA).read_text(), 'AR executor now references VL bias; review mapping')
    B.require('ck.rows("embed.weight"' in (ROOT / ISA).read_text(), 'host embedding lookup changed')
    source = subprocess.check_output(['git', 'show', OWNER_COMMIT + ':' + OWNER_PATH], cwd=ROOT)
    B.require(b'need separate non-SM images' in source, 'owner producer coverage changed')
    model = (ROOT / 'tools/uarch_model.py').read_text()
    paths = [B.INVENTORY, VERIFY, B.PROGRAM, ISA, GOLDEN, 'tools/uarch_model.py',
             'tools/w16_w19_resident_bounds.py', 'tools/w16_w19_address_prerequisite.py',
             'tools/w16_measured_calibration.py', 'tools/w16_w19_consumer_contracts.py',
             'tests/test_w16_w19_consumer_contracts.py']
    return dict(schema='opentallas.w16.w19.reference_consumer_requirements.v1',
        base_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        inventory_source=B.INVENTORY, parent_metadata_verification=VERIFY,
        parent_verified_headers=len(parent['header_bindings']), inventory_bounds=bounds,
        source_tensor_families=families,
        classification='Reference software use only; W19 unclassified source group retained, not a hardware constants or replication contract',
        current_token_scope='TP96 position1048575; ranks in calls are execution sites, not resident replicas. Compressor rank varies across sequence blocks.',
        owner_producer=dict(commit=subprocess.check_output(['git', 'rev-parse', OWNER_COMMIT], cwd=ROOT, text=True).strip(),
            path=OWNER_PATH, sha256=hashlib.sha256(source).hexdigest(),
            scope='Historical rejected compact SM producer excludes non-SM images; no capacity or transport credit'),
        current_model=dict(sha256=B.sha('tools/uarch_model.py'),
            capacity_function_present='def _v41_state_user' in model,
            resident_consumer_encoding_contract=None, per_stack_reservations=None),
        reservation_gate='REFUSED: no sourced deployed byte extents, replication or stack ranges; reuse stack_bound/reservations_fit once supplied',
        W19_handoff=dict(owner='Euler / actual accepted256 transport', acknowledgement=False,
            next_boundary='Bind the listed reference consumers to actual non-SM image formats/read ports, resident ownership and per-stack bases/extents, including scratch; measure service only after that contract is concrete'),
        measured_service_cycles=None, schedule_latency_ns=None, full_fit=False, adopted=False,
        pins={p: B.sha(p) for p in paths})


def check(record):
    for path, digest in record['pins'].items():
        B.require(B.sha(path) == digest, 'pin drift: ' + path)
    fresh = build()
    fresh['base_commit'] = record['base_commit']
    B.require(fresh == record, 'consumer requirements do not reproduce')


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
        print('PASS: parent inventory and reference consumer requirements; physical reservations remain REFUSED')
    except (B.Refusal, FileExistsError) as exc:
        ap.exit(2, 'REFUSED: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
