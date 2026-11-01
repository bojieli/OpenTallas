#!/usr/bin/env python3
"""Lower real TP8 checkpoint tables into the finite four-user QC store.

This emits table contents only. Reset/START, ROOT destination relocation,
command calendars, physical slice IDs, and token execution need their own gates.
No missing stage, scale, constant, or per-slice instruction is filled with zeros.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import dv_lower as D
import programme_store as P

VM_STRIDE, CROM_ELEMENTS = 4096, 2048


def relocate_instruction(word, user):
    """Relocate the actual 457-bit SU fields; preserve external address windows.

    Native vm8q/crh have no hidden user selector. CROM table addresses are
    16-element rows, so the 128-row user partition spans 2048 elements.
    a_src=1 selects WROM, whose namespace is not qualified by this pass.
    """
    if user not in range(4) or not 0 <= word < 1 << 457:
        raise ValueError('invalid user/instruction')
    if word == 0:
        return 0
    f = D.su_unpack(word)
    if f['go'] or not f['nin'] or not f['nout']:
        raise ValueError('stored instruction must have go=0 and positive dimensions')
    if f['asrc']:
        raise ValueError('WROM source relocation is not qualified')
    for name in ('a', 'b', 'c'):
        stride = CROM_ELEMENTS if name != 'a' and f[name + 'src'] else VM_STRIDE
        last = f[name] + (f['nout'] - 1) * f[name + 'so'] + (f['nin'] - 1) * f[name + 'si']
        if last >= stride:
            raise ValueError(f'{name} operand crosses its user partition')
        f[name] += user * stride
    for name, enabled in (('d', f['dst'] == 1), ('rb', bool(f['red']))):
        if not enabled or f[name] >> 22:
            continue
        last = f[name] + (f['nout'] - 1) * f['rso' if name == 'rb' else 'dso']
        if name == 'd':
            last += (f['nin'] - 1) * f['dsi']
        if last >= VM_STRIDE:
            raise ValueError(f'{name} result crosses its user partition')
        f[name] += user * VM_STRIDE
    return D.su_word(**f)


def prog_users(records):
    """Keep all six source pairs and generate four distinct private VM images."""
    if len(records) != P.PROG or sorted(r['eaddr'] for r in records) != list(range(P.PROG)):
        raise ValueError('six distinct native PROG pairs required')
    out = []
    for user in range(P.USERS):
        rows = []
        for rec in sorted(records, key=lambda r: r['eaddr']):
            payload = int(rec['payload'], 16)
            P.encode(3, rec['eaddr'], rec['payload'])  # exact native padding/width check
            lo, hi = payload & ((1 << 457) - 1), payload >> 512
            value = relocate_instruction(lo, user) | (relocate_instruction(hi, user) << 512)
            rows.append(dict(addr=rec['eaddr'], payload_hex=f'{value:0256x}'))
        out.append(rows)
    return out


def stage_tables(stage, lowering, btab, crom):
    """Compose genuine per-slice lowering outputs, distributing CROM broadcasts."""
    if not 1 <= stage <= P.STAGES:
        raise ValueError('stage outside finite store')
    slices = []
    for sid in range(P.SLICES):
        program = lowering.get(str(sid), lowering.get(sid))
        bt = btab.get(str(sid), btab.get(sid))
        if program is None or bt is None:
            raise ValueError(f'missing native slice {sid}')
        cr = [r for r in crom if r['dst'] in (sid, 15)]
        def unique(records, addr):
            out = {}
            for rec in records:
                a, value = int(rec[addr]), rec['payload']
                if a in out:
                    raise ValueError(f'duplicate table write slice {sid} addr {a}')
                out[a] = dict(addr=a, payload_hex=value)
            return [out[a] for a in sorted(out)]
        slices.append(dict(slice=sid, prog_users=prog_users(program),
                           btab=unique(bt, 'eaddr'), crom=unique(cr, 'eaddr')))
    return dict(stage=stage, slices=slices)


def compile_inputs(inputs, btab_compact=None):
    """Accept actual lowered streams, never a synthetic 36-stage replication."""
    if inputs.get('schema') != 'opentallas.qwen.native-table-streams.v1':
        raise ValueError('native source stream manifest required')
    stages = inputs['stages']
    if sorted(s['stage'] for s in stages) != list(range(1, 37)):
        raise ValueError('all 36 actual source stages required')
    compact = inputs.get('btab_compact') if btab_compact is None else btab_compact
    if compact not in (0, 1):
        raise ValueError('exact selected native BTAB_COMPACT required')
    source = inputs['source']
    for stage in stages:
        if not stage.get('image_sha256') or not stage.get('checkpoint_revision'):
            raise ValueError('each stage must name its actual checkpoint image')
    certificate = dict(schema='opentallas.qwen.su-user-relocation.v1',
        vm_stride=VM_STRIDE, crom_elements=CROM_ELEMENTS,
        btab_compact=compact, btab_user_bases=(0,272,344,416) if compact else (0,128,256,384),
        external_windows='unchanged; requires calendar and token qualification',
        source_stages=[dict(stage=s['stage'], image_sha256=s['image_sha256'],
                            checkpoint_revision=s['checkpoint_revision']) for s in stages])
    cert_bytes = (json.dumps(certificate, sort_keys=True) + '\n').encode()
    manifest = dict(schema='opentallas.qwen.mu-table-input.v1',
        parameters=dict(P.NATIVE_COMPACT_PARAMETERS) if compact else
                   dict(NU=4, PIDX_STRIDE=128, CROM_ROW_STRIDE=128, BTAB_WORD_STRIDE=128),
        source=dict(source, user_relocation_certificate_sha256=hashlib.sha256(cert_bytes).hexdigest()),
        qualification='TABLE LOWERING ONLY; ROOT/calendar/slice-ID/native-token gates OPEN',
        stages=[stage_tables(s['stage'], s['prog_stream'], s['btab_stream'], s['crom_table'])
                for s in sorted(stages, key=lambda s: s['stage'])])
    P.logical_images(manifest)  # reject incomplete shapes before emitting any masks
    return manifest, certificate


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--streams', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--btab-compact', type=int, choices=(0,1), help='selected native loader ABI for older stream bundles')
    a = ap.parse_args()
    manifest, certificate = compile_inputs(json.loads(a.streams.read_text()), a.btab_compact)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'mu_table_input.json').write_text(json.dumps(manifest, indent=1) + '\n')
    (a.out / 'user_relocation.json').write_text(json.dumps(certificate, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
