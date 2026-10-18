#!/usr/bin/env python3
"""kv_boot_images: the HOST boot image set of the KV die boot vehicle (LAYERBENCH G-K1, tools/qwen_layerbench/drive_qwk_slice_boot.svh).

Inputs: the compile of tools/qwen_kv_die/kv_static_programme.py (--profile die, run from the SAME source tree as the KV GEN
netlist's RTL so word counts / parameters match qkd_static_kv_boot_dispatch) = target{0..9,11,12,13}.hex + boot_bundle.json;
optionally --target1 FILE, the layer programme image of another compile (e.g. compiled_L1/kv_programme/boot.hex of
tools/qwen_layerbench/layer_compile.py on the die-run relay tables); and target 10 (the pre-boot die configuration of
qkd_kv_die_cfg, which kv_static_programme.py does not emit) built here with the formula of
tools/qwen_kv_die/kv_static_kvjf_join.die_cfg_image (32 ECTL words a | b << 5 | c << 10, NRST reset-region words, the
capability word (DIECAP=1), the seal 0x514b564443464731).

ECTL cfg of group i = 8 * stack + g (stacks WS, WN, ES, EN): the template identity (g << 2) | stack (tools/qwen_kv_die/
kv_static.py, the strap target 10 replaces), A = B = C (the die's qkd_ectl3_kiss_st takes one 5-bit cfg, from ectl_a_cfg).
Reset words: --dly (default 0 for every region): the kvs14c GEN does NOT wire qkd_kv_die_cfg.rst_dly to its
qkd_rst_region roots (their dly pins are die constants), so these words have no consumer there (recorded finding).

Outputs (--out DIR): target{t}.hex for t = 0..13 (target 0 = 1024 PW + 8 DW words), digests.memh (14 lines, line t = the
HOST loader digest of target t, i.e. the trusted auth digest: seed 0x51484f5354505247 ^ t, rotl7 ^ word ^ {desc, addr};
equal to boot_bundle.json for every bundle image, checked here), images.json (counts, digests, sha256, provenance).
    python3 tools/qwen_layerbench/kv_boot_images.py --kvprog DIR [--target1 FILE] [--capability 1] --out DIR
"""
import argparse
import hashlib
import json
from pathlib import Path

STACKS = ('WS', 'WN', 'ES', 'EN')
NRST = 43
DIE_CFG_SEAL = 0x514b564443464731
M64 = (1 << 64) - 1
ORDER = [10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 0]


def digest(t, pw, dw):
    d = 0x51484f5354505247 ^ t
    for a, w in enumerate(pw):
        d = (((d << 7) | (d >> 57)) & M64) ^ w ^ a
    for a, w in enumerate(dw):
        d = (((d << 7) | (d >> 57)) & M64) ^ w ^ ((1 << 10) | a)
    return d


def die_cfg_image(dly, capability):
    ect = [(g << 2) | s for s in range(4) for g in range(8)]
    if len(dly) != NRST or any(not 0 <= v < 256 for v in dly) or capability not in (0, 1):
        raise ValueError('die cfg fields')
    return [a | (a << 5) | (a << 10) for a in ect] + list(dly) + [capability, DIE_CFG_SEAL]


def rd(p):
    return [int(x, 16) for x in Path(p).read_text().split()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kvprog', type=Path, required=True)
    ap.add_argument('--target1', type=Path)
    ap.add_argument('--capability', type=int, default=1)
    ap.add_argument('--dly', default='', help='comma list of NRST reset-region delays (default all 0)')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    bundle = json.loads((a.kvprog / 'boot_bundle.json').read_text())
    bdig = {im['target']: int(im['digest'], 16) for im in bundle['images']}
    dly = [int(x) for x in a.dly.split(',')] if a.dly else [0] * NRST
    a.out.mkdir(parents=True, exist_ok=True)
    rec = dict(schema='opentallas.qwen_layerbench.kv_boot_images.v1', order=ORDER, epoch=bundle['epoch'], images={})
    digs = [0] * 14
    for t in ORDER:
        if t == 10:
            words, src = die_cfg_image(dly, a.capability), 'kv_boot_images.die_cfg_image (identity ECTL cfg, dly %s, cap %d)' % (
                'all 0' if not a.dly else a.dly, a.capability)
        elif t == 1 and a.target1:
            words, src = rd(a.target1), str(a.target1)
        else:
            words, src = rd(a.kvprog / f'target{t}.hex'), str(a.kvprog / f'target{t}.hex')
        pw, dw = (words[:1024], words[1024:]) if t == 0 else (words, [])
        d = digest(t, pw, dw)
        if t in bdig and not (t == 1 and a.target1) and d != bdig[t]:
            raise ValueError(f'target {t}: loader digest {d:016x} != boot_bundle {bdig[t]:016x}')
        if t == 1 and a.target1 and (words[324] != rd(a.kvprog / 'target1.hex')[324] or words[325] != bundle['epoch']):
            raise ValueError('target 1 override: LP_DIGEST / epoch differ from the bundle ISA image')
        digs[t] = d
        (a.out / f'target{t}.hex').write_text(''.join(f'{w:016x}\n' for w in words))
        rec['images'][str(t)] = dict(pw=len(pw), dw=len(dw), digest=f'{d:016x}', source=src,
                                     bundle_digest=f'{bdig[t]:016x}' if t in bdig else None,
                                     sha256=hashlib.sha256((a.out / f'target{t}.hex').read_bytes()).hexdigest())
    (a.out / 'digests.memh').write_text(''.join(f'{d:016x}\n' for d in digs))
    (a.out / 'images.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({t: (v['pw'], v['dw'], v['digest']) for t, v in rec['images'].items()}))


if __name__ == '__main__':
    main()
