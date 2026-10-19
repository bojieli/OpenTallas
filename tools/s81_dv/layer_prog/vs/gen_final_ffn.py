"""Exercise the production encoder against actual saved checkpoint down vectors.

This is the arithmetic/row-placement cut, not a transport or full-token test.
The preload is assembled using the production RD map and cap address map.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / 'tools/s81_dv/layer_prog'), str(ROOT / 'tools/s81_dv'), str(ROOT / 'tools')]
import final_ffn as F


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--fixtures', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--beat', type=int, default=0)
    p.add_argument('--post', action='store_true')
    p.add_argument('--mutant', choices=['owner', 'row', 'order', 'posta1', 'postcoef'])
    a = p.parse_args()
    if a.mutant in ('posta1', 'postcoef') and not a.post:
        p.error('POST mutants require --post')
    fx, out = Path(a.fixtures), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    meta = json.loads((fx / 'meta.json').read_text())
    assert meta['tp'] == 4
    experts = list(meta['experts'])
    assert len(experts) == 6 and experts == sorted(experts)
    assert 0 <= a.beat < 80
    paths = [fx / f'ops/ffn.experts.{e}.down.bin' for e in experts]
    paths.append(fx / 'ops/ffn.shared.down.bin')
    values = [np.fromfile(x, np.float32).view(np.uint32) for x in paths]
    expected = np.fromfile(fx / 'ops/ffn.combine_allreduce.bin', np.float32).view(np.uint32)
    assert all(len(v) == 5120 for v in values) and len(expected) == 5120
    # Reconstruct real capture words; then apply EXACT producer->consumer map.
    source = {}
    for rank in range(4):
        for sid in range(16):
            for expert in range(7):
                cfg = F.capture(rank, sid, expert)
                for i in range(80):
                    leaf, w = divmod(i, 64)
                    source[rank, sid, leaf, cfg['obase'] + w] = int(values[expert][1280 * rank + 80 * sid + i])
    moves = [m for rank in range(4) for m in F.transfers(rank)]
    F.verify_moves(moves)
    F.check_lease([], 0, 1000)
    image = {}
    for m in moves:
        if m['beat'] != a.beat:
            continue
        for w in range(8):
            key = (m['rank'], m['source_sid'], m['source_leaf'], 4 * m['source_row'] + w)
            dest = 4 * m['row'] + w
            assert dest not in image
            image[dest] = source[key]
    assert len(image) == 448
    if a.mutant == 'owner':
        # Real stale other-owner content at identical local row addresses.
        other = (a.beat + 1) % 80
        for e in range(7):
            for w in range(64):
                image[4 * (F.ASSEMBLED + 16 * e) + w] = int(values[e][64 * other + w])
    if a.mutant == 'row':
        for e in range(7):
            b = 4 * (F.ASSEMBLED + 16 * e)
            old = [image[b + w] for w in range(64)]
            for w in range(64):
                image[b + w] = old[(w + 8) % 64]
    if a.mutant == 'order':
        # Shared first changes the actual canonical addition order.
        old = dict(image)
        for e in range(7):
            for w in range(64):
                image[4 * (F.ASSEMBLED + 16 * e) + w] = old[4 * (F.ASSEMBLED + 16 * ((e + 6) % 7)) + w]
    cmd = F.commands(a.beat // 5, a.beat % 5)['combine']
    pack = lambda words: sum(int(x) << (32 * i) for i, x in enumerate(words))
    post_expected = []
    if a.post:
        residual = np.fromfile(fx/'ops/attn.hc_post.bin',np.float32).view(np.uint32).reshape(4,5120)
        result = np.fromfile(fx/'ops/ffn.hc_post.bin',np.float32).view(np.uint32).reshape(4,5120)
        coef = np.fromfile(fx/'ops/ffn.hc.pre_post.bin',np.float32).view(np.uint32)
        comb = np.fromfile(fx/'ops/ffn.hc.sinkhorn.bin',np.float32).view(np.uint32)
        assert len(coef) == 8 and len(comb) == 16
        for h in range(16):
            words = [int(residual[c,64*a.beat+8*(h//2)+4*(h%2)+w])>>16 for c in range(4) for w in range(4)]
            packed = sum(x << (16*i) for i,x in enumerate(words))
            for w in range(8):
                image[4*(2*h)+w] = (packed>>(32*w)) & 0xffffffff
            want = [int(result[c,64*a.beat+8*(h//2)+4*(h%2)+w])>>16 for c in range(4) for w in range(4)]
            post_expected.append(sum(x << (16*i) for i,x in enumerate(want)))
        for i,v in enumerate(list(coef)+list(comb)):
            image[4*1008+i] = int(v)
        if a.mutant == 'postcoef':
            image[4*1010],image[4*1010+1] = image[4*1010+1],image[4*1010]
    (out / 'img.mem').write_text(''.join(f'{pack([image.get(4*r+w, 0) for w in range(4)]):032x}\n' for r in range(1024)))
    (out / 'imgv.mem').write_text(''.join(f'{int(4*r in image)}\n' for r in range(1024)))
    # Existing real VP/VS/VQ benchmark, command at600, subsequent real RDOUT.
    dur = 100  # conservative model bound; exact age printed by the RTL bench
    prog = [1 << 252 | 600 << 228 | 13 << 224 | dur << 186 | cmd,
            2 << 252 | 8 << 202 | F.COMBINED, 0]
    y = expected[64 * a.beat:64 * (a.beat + 1)]
    exp = [pack(y[i:i+8]) for i in range(0,64,8)]
    last = 600
    if a.post:
        from layer_prog.lower_vs import vp_cmd
        postcmd = F.commands(a.beat//5,a.beat%5)['post']
        if a.mutant == 'posta1':
            postcmd = vp_cmd(2,a0=1009,a1=450)
        prog = [4 << 252 | 600 << 228 | vp_cmd(3,a0=0),
                1 << 252 | 700 << 228 | 13 << 224 | dur << 186 | cmd,
                1 << 252 | 800 << 228 | 2 << 224 | 100 << 186 | postcmd,
                4 << 252 | 900 << 228 | vp_cmd(4,a0=32),
                5 << 252 | 960 << 228,
                2 << 252 | 8 << 202 | F.COMBINED,
                2 << 252 | 8 << 210 | 16 << 202 | 32,
                2 << 252 | 24 << 210 | 1 << 202 | 1008, 0]
        exp += post_expected
        exp.append(pack(coef))  # retained pre1008 plus actual post1009
        last = 960
    (out / 'prog.mem').write_text(''.join(f'{x:064x}\n' for x in prog))
    (out / 'exp.mem').write_text(''.join(f'{x:064x}\n' for x in exp))
    (out / 'expm.mem').write_text('ff\n' * len(exp))
    (out / 'xq.mem').write_text('0\n')
    (out / 'xqi.mem').write_text('0\n')
    (out / 'params.txt').write_text(f'+sid={a.beat//5} +k={a.beat%5} +nxq=0 +last={last}\n')
    if a.post:
        paths += [fx / ('ops/' + n + '.bin') for n in ('attn.hc_post', 'ffn.hc_post', 'ffn.hc.pre_post', 'ffn.hc.sinkhorn')]
    manifest = dict(beat=a.beat, mutant=a.mutant, source=f"actual {meta['layer']} checkpoint FFN down outputs",
                    scope='mapped arithmetic cut; transport not simulated', command=f'{cmd:040x}',
                    inputs={str(x): hashlib.sha256(x.read_bytes()).hexdigest() for x in paths},
                    golden_sha256=hashlib.sha256((fx/'ops/ffn.combine_allreduce.bin').read_bytes()).hexdigest())
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('FINAL_FFN_VECTOR', a.beat, a.mutant, len(image), flush=True)


if __name__ == '__main__':
    main()
