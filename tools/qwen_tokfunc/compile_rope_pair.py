#!/usr/bin/env python3
"""Fleet-only generation of one RoPE pair image and its four MU playback ROMs.

Usage: compile_rope_pair.py --source-dir ASSEMBLY --ages ACTUAL_GEN_RECEIPT
                          --token-path COMPILED_TOKEN_JSON --out NEW_DIRECTORY

This generates programmes, not a functional PASS. Unknown source/transport ages
refuse before creating output. HEAD_PREP identity comes from the selected actual
c_emb producer and held O61 descriptor, never RESULT or inferred next-token data.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-dir', type=Path, required=True)
    ap.add_argument('--ages', type=Path, required=True)
    ap.add_argument('--token-path', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--link-handoff', type=Path, required=True)
    a = ap.parse_args()
    source, out = a.source_dir.resolve(), a.out.resolve()
    receipt = json.loads(a.ages.read_text())
    # These must be source-bound GEN facts. No default stages or zero-hop
    # fallback: a measured zero is allowed when the actual GEN establishes it.
    for key in ('compute_source', 'kv_source', 'compute_gen_sha256', 'kv_gen_sha256',
                'head_producer', 'held_descriptor', 'user0_host_match_source',
                'tt_to_native_path', 'native_to_sysface_path', 'die_stages'):
        value = receipt.get(key)
        if not isinstance(value, str) or not value.strip() or value.upper() in ('UNKNOWN', 'PENDING', '?'):
            raise SystemExit(f'unknown required source/GEN fact: {key}')
    for key in ('tt_to_native_edges', 'native_to_sysface_edges', 'head_prepare_edges',
                'host_stages', 'kv_codec', 'emb_window',
                'layer_period_min', 'attn_tx_shift', 'status_delay',
                'kv_descriptor_to_header_edges'):
        if type(receipt.get(key)) is not int or receipt[key] < 0:
            raise SystemExit(f'unknown required actual age/programme input: {key}')
    if receipt['head_prepare_edges'] < 5:
        raise SystemExit('head_prepare_edges omits source prepare/held-descriptor stages')
    if receipt['emb_window'] < 1627 or receipt['kv_codec'] not in (1, 2):
        raise SystemExit('invalid 73-record RoPE programme shape')
    # A new directory retains earlier failed generations and immutable receipts.
    out.mkdir(parents=True, exist_ok=False)
    (out / 'actual_gen_inputs.json').write_text(json.dumps(receipt, indent=2) + '\n')

    def run(args, log):
        with (out / log).open('w') as f:
            subprocess.run([sys.executable, *args], cwd=source, stdout=f,
                           stderr=subprocess.STDOUT, check=True,
                           env=dict(os.environ, PYTHONPATH=str(source / 'tools')))

    pair = out / 'pair'
    options = ['--out', str(pair), '--txl', '6', '--phy', '5', '--profile', 'program',
               '--die-stages', receipt['die_stages'], '--mu', '--rope', '--pinreg',
               '--host-stages', str(receipt['host_stages']),
               '--token-path', str(a.token_path.resolve()),
               '--link-handoff', str(a.link_handoff.resolve())]
    for flag, key in (('kv-codec', 'kv_codec'),
                      ('emb-window', 'emb_window'), ('layer-period-min', 'layer_period_min'),
                      ('attn-tx-shift', 'attn_tx_shift'), ('status-delay', 'status_delay'),
                      ('head-prepare-edges', 'head_prepare_edges')):
        options += ['--' + flag, str(receipt[key])]
    run(['tools/qwen_split/d2d_link_calendar.py', *options], 'pair.log')
    calendar = json.loads((pair / 'calendar.json').read_text())
    head = [m for m in calendar['messages']
            if m['seg'] == 1 and m['src'] == 'C' and m['kind'] == 12]
    if len(head) != 1:
        raise SystemExit('sole calendar lacks unique actual recurring Ckind12 descriptor')
    ready = head[0]['rx_out'] + receipt['kv_descriptor_to_header_edges']
    if ready > calendar['program']['emb_header_send']:
        raise SystemExit(f'actual descriptor/header deadline fails: ready {ready} > '
                         f"header {calendar['program']['emb_header_send']}")
    image = out / 'd2d_cal_image_mu_rope.svh'
    run(['tools/qwen_split/d2d_cal_seq_image.py', str(pair), str(image)], 'image.log')
    run(['-m', 'qwen_static_schedule.mu_d2d_ovl', '--out', str(out / 'ovl'),
         '--pair-calendar', str(pair / 'calendar.json'), '--stages', receipt['die_stages'],
         '--kv-codec', str(receipt['kv_codec']), '--kv-prog',
         '--token-path', str(a.token_path.resolve()),
               '--link-handoff', str(a.link_handoff.resolve())], 'ovl.log')
    run(['tools/qwen_split/d2d_ovl_release.py', str(out / 'ovl'), str(image),
         str(out / 'release')], 'release.log')
    release = json.loads((out / 'release/source.json').read_text())
    admission = calendar['program']['admission']
    params = dict(ROPE_OVL_FIRST_OFS=release['first_ofs'],
                  ROPE_OVL_ADM_OFS=admission['ofs'], ROPE_OVL_ADM_LEN=admission['len'],
                  ROPE_OVL_ADM_BASE=release['admission_base'])
    lines = ['// Generated from the sole pair calendar and four-ROM release.']
    lines += [f'localparam integer {key} = {value};' for key, value in params.items()]
    lines += [f'localparam ROPE_OVL_ROM_DIR = {json.dumps(str(out / "release"))};']
    (out / 'release/ovl_wrapper_params.svh').write_text('\n'.join(lines) + '\n')
    hashes = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(out.rglob('*')) if p.is_file()}
    (out / 'generated.json').write_text(json.dumps(dict(
        grade='SOURCE GENERATION ONLY; no functional or die-netlist PASS',
        compiler_recovery='e18e3d597', actual_gen_inputs=receipt, sha256=hashes), indent=2) + '\n')


if __name__ == '__main__':
    main()
