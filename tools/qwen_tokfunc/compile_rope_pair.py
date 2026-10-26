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
import re
import os
from pathlib import Path
import subprocess
import sys



def write_wrapper_params(release, admission, directory, rom_dir=None, pathfinding=False):
    """The final compiler and existing-image recovery use this same renderer."""
    directory = Path(directory)
    params = dict(ROPE_OVL_FIRST_OFS=release['first_ofs'],
                  ROPE_OVL_ADM_OFS=admission['ofs'], ROPE_OVL_ADM_LEN=admission['len'],
                  ROPE_OVL_ADM_BASE=release['admission_base'])
    lines = ['// Generated from the sole pair calendar and four-ROM release.']
    if pathfinding:
        lines += ['// PATHFINDING ONLY: existing73-record image lacks the recurring HEAD_PREP slot.',
                  '// Final release requires actual current GEN ages and a corrected sole pair compile.']
    lines += [f'localparam integer {key} = {value};' for key, value in params.items()]
    lines += [f'localparam ROPE_OVL_ROM_DIR = {json.dumps(str(rom_dir if rom_dir is not None else directory))};']
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / 'ovl_wrapper_params.svh'
    target.write_text('\n'.join(lines) + '\n')
    return target


def render_existing_wrapper(argv):
    ap = argparse.ArgumentParser(description='Recover only a pathfinding wrapper from a recorded existing image')
    ap.add_argument('--release-metadata', type=Path, required=True)
    ap.add_argument('--admission-image', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--rom-dir', required=True)
    a = ap.parse_args(argv)
    release = json.loads(a.release_metadata.read_text())
    raw = a.admission_image.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if release.get('admission_sha256') != digest:
        raise SystemExit('existing admission image differs from recorded release hash')
    text = raw.decode()
    def number(name):
        m = re.search(r'localparam integer ' + name + r'\s*=\s*([0-9]+)\s*;', text)
        if not m: raise SystemExit('existing admission image lacks ' + name)
        return int(m.group(1))
    admission = dict(ofs=number('D2D_ADM_OFS'), len=number('D2D_ADM_LEN'))
    if release.get('first_ofs') != number('D2D_FIRST_TOKEN'):
        raise SystemExit('existing release and admission disagree on first token offset')
    a.out.mkdir(parents=True, exist_ok=False)
    target = write_wrapper_params(release, admission, a.out, a.rom_dir, pathfinding=True)
    record = dict(status='PATHFINDING_ONLY_EXISTING_PROGRAMME',
                  final_programme_qualified=False,
                  release_metadata_sha256=hashlib.sha256(a.release_metadata.read_bytes()).hexdigest(),
                  admission_image_sha256=digest, source_admission=release.get('admission'),
                  first_ofs=release['first_ofs'], admission_base=release['admission_base'],
                  admission=admission, token_period=number('D2D_TOKEN_PERIOD'),
                  rom_dir=a.rom_dir, wrapper_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                  limitation='existing image lacks recurring HEAD_PREP slot; final current GEN/source compile remains required')
    (a.out / 'wrapper_receipt.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))


def require_status_observation_ages(receipt):
    # Independent GEN paths. The HOST293 snapshot is a local reader format;
    # host_stages below continues to mean boot/HOST O61 ingress transport.
    for key in ('kv_descriptor_to_kvn_expected_edges', 'status225_transport'):
        if type(receipt.get(key)) is not int or receipt[key] < 0:
            raise SystemExit(f'unknown required coherent STATUS age: {key}')
    for key in ('kv_descriptor_to_kvn_expected_path', 'status225_transport_path'):
        value = receipt.get(key)
        if not isinstance(value, str) or not value.strip() or value.strip().upper() in ('UNKNOWN', 'PENDING', '?'):
            raise SystemExit(f'unknown required coherent STATUS GEN path: {key}')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-dir', type=Path, required=True)
    ap.add_argument('--ages', type=Path, required=True)
    ap.add_argument('--token-path', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--link-handoff', type=Path, required=True)
    ap.add_argument('--status-observers', action='store_true',
                    help='require final coherent STATUS/KVN GEN ages and paths; no extra calendar frames')
    a = ap.parse_args()
    source, out = a.source_dir.resolve(), a.out.resolve()
    receipt = json.loads(a.ages.read_text())
    if a.status_observers:
        require_status_observation_ages(receipt)
    # These must be source-bound GEN facts. No default stages or zero-hop
    # fallback: a measured zero is allowed when the actual GEN establishes it.
    for key in ('compute_source', 'kv_source', 'compute_gen_sha256', 'kv_gen_sha256',
                'head_producer', 'held_descriptor', 'user0_host_match_source',
                'tt_to_native_path', 'native_to_sysface_path', 'die_stages',
                'selected_slice_source', 'selected_slice_timing_receipt'):
        value = receipt.get(key)
        if not isinstance(value, str) or not value.strip() or value.strip().upper() in ('UNKNOWN', 'PENDING', '?'):
            raise SystemExit(f'unknown required source/GEN fact: {key}')
    for key in ('tt_to_native_edges', 'native_to_sysface_edges', 'head_prepare_edges',
                'host_stages', 'kv_codec', 'emb_window',
                'layer_period_min', 'attn_tx_shift', 'status_delay',
                'kv_descriptor_to_header_edges'):
        if type(receipt.get(key)) is not int or receipt[key] < 0:
            raise SystemExit(f'unknown required actual age/programme input: {key}')
    intrinsic = receipt.get('source_intrinsic_edges')
    names = ('ct_lm_sample', 'native_prepare_descriptor', 'face_held_bank')
    if not isinstance(intrinsic, dict) or any(type(intrinsic.get(k)) is not int or intrinsic[k] < 1 for k in names):
        raise SystemExit('unknown source-bound TT/native/held-bank intrinsic edge ledger')
    tt = receipt.get('tt_source')
    if not isinstance(tt, dict) or tt.get('producer_instance') != 'u_gi':
        raise SystemExit('actual selected TT source/GI qualification receipt required')
    if tt.get('status') != 'QUALIFIED_SOURCE_LOCAL_EDGES':
        raise SystemExit('selected TT source-local edges are missing or unqualified')
    for key in ('master', 'receipt_sha256', 'rtl_sha256', 'lp_record_sha256'):
        value = tt.get(key)
        if not isinstance(value, str) or not value.strip():
            raise SystemExit(f'unknown actual selected TT source identity: {key}')
        if key.endswith('sha256') and (len(value) != 64 or any(c not in '0123456789abcdef' for c in value)):
            raise SystemExit(f'invalid TT source qualification hash: {key}')
    for key in ('calendar_sample_edges', 'output_offset_edges', 'producer_offset_edges', 'source_to_output_edges'):
        if type(tt.get(key)) is not int or tt[key] < 0:
            raise SystemExit(f'unknown actual TT source-local age: {key}')
    if (tt['calendar_sample_edges'] != 1
            or tt['output_offset_edges'] - tt['producer_offset_edges'] != tt['source_to_output_edges']
            or tt['calendar_sample_edges'] + tt['source_to_output_edges'] != intrinsic['ct_lm_sample']):
        raise SystemExit('TT intrinsic age disagrees with qualified producer-relative LP source ledger')
    expected_head = sum(intrinsic[k] for k in names) + receipt['tt_to_native_edges'] + receipt['native_to_sysface_edges']
    if receipt['head_prepare_edges'] != expected_head:
        raise SystemExit('head_prepare_edges disagrees with actual source-intrinsic/GEN transport ledger')
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
         '--token-path', str(a.token_path.resolve())], 'ovl.log')
    run(['tools/qwen_split/d2d_ovl_release.py', str(out / 'ovl'), str(image),
         str(out / 'ovl_release_rope')], 'release.log')
    release = json.loads((out / 'ovl_release_rope/source.json').read_text())
    admission = calendar['program']['admission']
    write_wrapper_params(release, admission, out / 'ovl_release_rope')
    hashes = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(out.rglob('*')) if p.is_file()}
    (out / 'generated.json').write_text(json.dumps(dict(
        grade='SOURCE GENERATION ONLY; no functional or die-netlist PASS',
        compiler_recovery='e18e3d597', actual_gen_inputs=receipt,
        status_observers=dict(enabled=a.status_observers, version=1, transport_bits=225,
                              host_atomic_snapshot_bits=293,
                              host_stages_scope='boot/HOST O61 ingress, independent of STATUS transport',
                              kvn_deadline='not inferred; actual age/path retained for playback'),
        owner_callbacks=dict(
            admission=dict(segment=2, base=release['admission_base'],
                           phase='before actual sequencer adm_done',
                           owner='accepted HOST O61; filler owner may be 1..3 while cal_user is 0',
                           compare_cal_user_to_O61=False),
            recurrent_head=dict(segment=1, direction='C->K', kind=12,
                                phase='after actual sequencer adm_done, per-user token playhead',
                                owner='actual earliest c_emb token/position/user and held O61',
                                compare_cal_user_to_O61=True)), sha256=hashes), indent=2) + '\n')


if __name__ == '__main__':
    if sys.argv[1:2] == ['--render-existing-wrapper']:
        render_existing_wrapper(sys.argv[2:])
    else:
        main()
