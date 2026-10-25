#!/usr/bin/env python3
"""TOK-QK 10-24: token mutant m4 -- one schedule word of the KV boot image changed, image re-encoded (frame digests valid).

Decodes the encoded boot bundle (class-8 frames: op1 header, op2 words [desc<<8 | addr<<9 | word<<19], op3, op4 digest),
proves the decode by re-encoding the unmutated images with tools/qwen_static_kv/program_target_frames.encode_boot_bundle
(byte-exact against the bundle), then adds DELTA to word ADDR of target TARGET and re-encodes.  The transport accepts the
mutated image (digests recomputed), so only the die's behaviour can catch it.
  mut_m4.py BUNDLE OUTDIR [--target 13] [--addr 0] [--delta 1]     -> OUTDIR/{frames.hex,expect.txt,epoch.txt,m4.json}
Default target 13 word 0 = join4 beat calendar segment 0 (a schedule word; target 1 words are self-digested at 324 and sealed at 326).
"""
import argparse, gzip, json, sys
from pathlib import Path
R = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(R / 'tools/qwen_static_kv'))
from program_target_frames import encode_boot_bundle

M64 = (1 << 64) - 1
ap = argparse.ArgumentParser(); ap.add_argument('bundle'); ap.add_argument('out')
ap.add_argument('--target', type=int, default=13); ap.add_argument('--addr', type=int, default=0); ap.add_argument('--delta', type=int, default=1)
a = ap.parse_args()
b = json.load(gzip.open(a.bundle) if a.bundle.endswith('.gz') else open(a.bundle))
mu = b.get('layer_form') == 'MU' or any(im['target'] == 1 and im['program_words'] == 471 for im in b['images'])
images = []
for im in b['images']:
    prog, desc = [0] * im['program_words'], [0] * im['descriptor_words']
    for h in im['frames528']:
        f = int(h, 16)
        if f & 0xff == 2:
            (desc if (f >> 8) & 1 else prog)[(f >> 9) & 0x3ff] = (f >> 19) & M64
    images.append(dict(target=im['target'], epoch=b['epoch'], program=prog, descriptors=desc))
re = encode_boot_bundle(b['epoch'], images, mu=mu)
assert re['frames528'] == b['frames528'], 'decode/re-encode not exact'
img = next(i for i in images if i['target'] == a.target)
old = img['program'][a.addr]; img['program'][a.addr] = (old + a.delta) & M64
m = encode_boot_bundle(b['epoch'], images, mu=mu)
o = Path(a.out); o.mkdir(parents=True, exist_ok=True)
(o / 'frames.hex').write_text('\n'.join(m['frames528']) + '\n')
(o / 'expect.txt').write_text(''.join(f"{i['target']} {i['digest']}\n" for i in m['images']))
(o / 'epoch.txt').write_text(f"{m['epoch']}\n")
nd = sum(x != y for x, y in zip(m['frames528'], b['frames528']))
json.dump(dict(mutant='m4', target=a.target, addr=a.addr, old=f'{old:#x}', new=f"{img['program'][a.addr]:#x}", mu=mu,
               reencode_exact=True, frames=len(m['frames528']), frames_changed=nd), open(o / 'm4.json', 'w'), indent=1)
print(f'm4: target {a.target} word {a.addr} {old:#x} -> {img["program"][a.addr]:#x}; re-encode exact; {nd} frames changed')
