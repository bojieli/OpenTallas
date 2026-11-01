#!/usr/bin/env python3
"""Extract genuine 36-layer TP8 checkpoint constants and lower native QC tables.

Attention owners must come from the selected command calendar; this pass does
not invent a new return schedule. No matrix code ROM or golden execution is
changed. Full token and per-user ROOT/calendar qualification remain open.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import dv_lower as D
import dv_lower_mat as M
import dv_lower_vec as V


def checked_lines(path, expected):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f'checkpoint table bytes differ: {path}')
    return [int(s, 16) for s in data.split()]


def lower_image(directory, layer, rank, own, attention_owners):
    meta = json.loads((directory / f'layer{layer}_rom.json').read_text())
    if (meta['layer'], meta['die'], meta['tp']) != (layer, rank, 8):
        raise ValueError('checkpoint stage/rank/TP mismatch')
    for name in ('program.hex', 'matrix_scale_bf16.hex'):
        checked_lines(directory / name, meta['image_sha256'][name])
    crom = checked_lines(directory / 'crom.hex', meta['image_sha256']['crom.hex'])
    prog = str(directory / 'program.hex')
    isa, norm = V.isa_vec(prog), D.isa_rmsnorm(prog)
    # Decode the original instruction to locate actual shared per-head gains.
    import hdc_qwen_fullshape_isa_w12 as QI
    ops = [QI.decode_instruction(w) for w in checked_lines(directory / 'program.hex', meta['image_sha256']['program.hex'])]
    gains = [o for o in ops if o['unit'] == 2 and o['c_src'] == 1 and o['mc'] == 1
             and o['ma'] == 1 and o['su_nin'] == 128 and o['c_so'] == 128]
    if len(gains) != 1 or gains[0]['su_nout'] != 5:
        raise ValueError('exact TP8 four-Q/one-K norm instruction required')
    qbase = gains[0]['c_base']
    bits = lambda start, n: np.asarray([w & 0xffffffff for w in crom[start:start+n]], dtype=np.uint32)
    q = bits(qbase, 128)
    if any(not np.array_equal(q, bits(qbase + h * 128, 128)) for h in range(1, 4)):
        raise ValueError('Q gains differ across heads; broadcast lowering invalid')
    ps = meta['post_tp_scale_bases']
    consts = dict(ps1=bits(ps[0], 4096).view(np.float32), ps2=bits(ps[1], 4096).view(np.float32),
                  q_norm=q.view(np.float32), k_norm=bits(qbase + 4*128, 128).view(np.float32))
    if any(len(consts[k]) != n for k, n in [('ps1',4096),('ps2',4096),('q_norm',128),('k_norm',128)]):
        raise ValueError('truncated source constants')
    scale_words = checked_lines(directory / 'matrix_scale_bf16.hex', meta['image_sha256']['matrix_scale_bf16.hex'])
    scales = {}
    for m in meta['matrix_layout']:
        if m['name'] not in ('qkv', 'o', 'gu', 'down'):
            continue
        hw = [(scale_words[m['scale_base'] + r//16] >> (16*(r%16))) & 0xffff for r in range(m['rows'])]
        scales[m['name']] = (np.asarray(hw, dtype=np.uint32) << 16).view(np.float32)
    if set(scales) != {'qkv','o','gu','down'}:
        raise ValueError('missing production matrix scales')
    vm, cr = V.vm_map_vec(own), V.crom_map(own)
    programs = {}
    for sid in range(12):
        bl = own['residual']['blocks_per_slice'][sid]
        ssq = D.su_word(nout=len(bl), nin=128, a=vm['X']['base'], aso=128, asi=1,
                        red=1, redsq=1, rb=D.W_SC | bl[0], rso=bl[1]-bl[0] if len(bl)>1 else 0)
        words = V.image(sid, V.words(sid, own, vm, cr, isa, att=attention_owners), ssq)
        programs[str(sid)] = [dict(eaddr=a, payload=f'{p:0256x}') for a,p in D.prog_words(words)]
    bt = M.btab_stream(M.btab_layout(own), scales)
    return dict(stage=layer+1, checkpoint_revision=meta['checkpoint_revision'],
        image_sha256=meta['image_sha256'], prog_stream=programs,
        btab_stream={str(s):[dict(eaddr=a,payload=f'{p:0256x}') for a,p in bt[s]] for s in range(12)},
        crom_table=[dict(dst=s,eaddr=a,payload=f'{p:0256x}') for s,a,p in V.crom_table(own,cr,consts)])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--images', type=Path, required=True)
    ap.add_argument('--rank', type=int, choices=range(8), required=True)
    ap.add_argument('--attention-owners', required=True, help='four comma-separated slice IDs from selected calendar')
    ap.add_argument('--lowering-commit', help='exact source commit when running a git archive')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    att = [int(s) for s in a.attention_owners.split(',')]
    if len(att) != 4 or len(set(att)) != 4 or any(s not in range(12) for s in att):
        ap.error('four distinct legal attention owners required')
    own = D.ownership(slice_rtl='s8')
    stages, locks = [], set()
    for layer in range(36):
        directory = a.images / f'layer{layer}' / f'die{a.rank}'
        meta = json.loads((directory/f'layer{layer}_rom.json').read_text())
        locks.add(meta['checkpoint_lock_sha256'])
        stages.append(lower_image(directory,layer,a.rank,own,att))
        print(f'LOWERED rank={a.rank} stage={layer+1} actual tables', flush=True)
    if len(locks) != 1:
        raise ValueError('mixed checkpoint locks')
    commit = a.lowering_commit or subprocess.check_output(['git','-C',str(D.ROOT),'rev-parse','HEAD'],text=True).strip()
    if len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
        raise ValueError('exact lowering commit required')
    out = dict(schema='opentallas.qwen.native-table-streams.v1',
        source=dict(lowering_commit=commit,checkpoint_sha256=locks.pop()),
        rank=a.rank, attention_owners=att, ownership=own, btab_compact=1,
        qualification='table payload lowering; selected calendar/slice IDs/native-token qualification OPEN', stages=stages)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(out)+'\n')


if __name__ == '__main__':
    import sys
    sys.path.insert(0,str(D.ROOT/'tools'))
    main()
