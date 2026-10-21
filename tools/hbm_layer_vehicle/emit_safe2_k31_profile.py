#!/usr/bin/env python3
"""Emit the existing k31/npos1 HC input programme under an explicit SAFE2 profile.

No expected O is accepted. This is source-only input assembly, not execution.
The small AST extraction avoids loading the full model or changing shared code.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path
import struct
from types import SimpleNamespace
from hc_safe2_phase40_1021 import SAFE2_P40, root_rows_for_profile

HELPER_SHA = '9a0e002e752e193f34909d3543a0764a4f3d371432b40d2086fb7e66d046b05a'
IMAGES_SHA = '4bbb842ce36d82d9a34a9ab2a5a6564e322557b857bf17b730856b5a82c7895a'


def pinned(path, expected):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f'input source SHA mismatch: {path}')
    return raw.decode()


def lower(checkpoint, legacy_helper, hc_images):
    helper = pinned(legacy_helper, HELPER_SHA)
    images = pinned(hc_images, IMAGES_SHA)
    prog = next(n for n in ast.parse(images).body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'PROG_OUT' for t in n.targets))
    prog_out = ast.literal_eval(prog.value)
    if prog_out != 9:
        raise ValueError('unexpected source programme output latency')
    constants = {'CHECKPOINT_SHA256', 'ROOT_APPLY_AFTER_LAUNCH', 'TAIL_RESULT_LATENCY',
                 'TAIL_EMIT_GUARD', 'EVENT_FIELDS'}
    functions = {'sha_file', 'checkpoint_parameters', 'event_word', 'root_rows'}
    selected = []
    for node in ast.parse(helper).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in constants for t in node.targets):
            selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in functions:
            selected.append(node)
    env = dict(hashlib=hashlib, json=json, struct=struct, Path=Path,
               HC=SimpleNamespace(PROG_OUT=prog_out))
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(legacy_helper), 'exec'), env)
    parameters, provenance = env['checkpoint_parameters'](checkpoint, 0, 'attn')
    table, rows, schedule = root_rows_for_profile(env['root_rows'], parameters, 39,
                                                 profile=SAFE2_P40, npos=1)
    return dict(status='SOURCE_INPUT_ASSEMBLY_ONLY', execution_qualified=False,
                qualifies_native_layer=False, qualifies_native_chain=False,
                scope=dict(rank=0, fixture='k31', priced_record=30, opcode='HC.HC_MIX_POST',
                           tag='hc_attn (mixes + Sinkhorn)', K=20480, npos=1,
                           relocated_component_vm=dict(A_sector=64, O_sector=72),
                           native_L0_mapping=False),
                root_targets=dict(programme=164, table=165),
                root_programme_rows=[f'{x:064x}' for x in rows],
                root_table_rows=[f'{x:064x}' for x in table], root_schedule=schedule,
                checkpoint_input_provenance=provenance,
                source_binding=dict(legacy_helper_commit='9f2ae79aac7a25d72eba314e4cc0d641e79aed49',
                                    legacy_helper_sha256=HELPER_SHA, hc_images_sha256=IMAGES_SHA,
                                    candidate_source_commit='5bdf1a9c5',
                                    candidate_spec_profile_commit='6f0c096c3',
                                    die_mapping_commit='4359fec30',
                                    profile=SAFE2_P40),
                root_data_producer='actual root required; no fixture result drive emitted',
                remaining=['actual SAFE2 candidate source/graph and common caller binding',
                           'actual native census using published reviewed authority',
                           'separate real root coupled execution; legacy11 proof not reusable',
                           'reset startup, clock delivery/model, physical gate and adoption'],
                multi_position_calendar='NOT_GENERATED_OR_QUALIFIED')


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ['checkpoint', 'legacy-helper', 'hc-images', 'out']:
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    d = lower(a.checkpoint, a.legacy_helper, a.hc_images)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out/'safe2_k31_profile.json').write_text(json.dumps(d, indent=2)+'\n')
    for key, name in [('root_programme_rows','root_programme.mem'), ('root_table_rows','root_table.mem')]:
        (a.out/name).write_text('\n'.join(d[key])+'\n')
    print(json.dumps({k:d[k] for k in ['status','scope','root_schedule']}))


if __name__ == '__main__':
    main()
