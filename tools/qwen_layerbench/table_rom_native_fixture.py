#!/usr/bin/env python3
"""Prepare oracle streams from exact manifest; macro images use programme_store."""
import argparse,json,os
from pathlib import Path
import programme_store as P

ap=argparse.ArgumentParser()
ap.add_argument('--manifest',type=Path,required=True)
ap.add_argument('--images',type=Path,required=True)
ap.add_argument('--out',type=Path,required=True)
a=ap.parse_args()
manifest=json.loads(a.manifest.read_text());images=P.logical_images(manifest)
a.out.mkdir(parents=True,exist_ok=True)
for s,words in enumerate(images):
    d=a.out/f's{s}';d.mkdir(exist_ok=True)
    # Instance names describe the four macros in one slice. Separate process
    # runs consume each slice's physical masks, without recompiling the bench.
    for lane in range(4):
        path=d/f'table_s0_m{lane}.viamap.hex'
        if path.is_symlink():path.unlink()
        path.symlink_to((a.images/f'table_s{s}_m{lane}.viamap.hex').resolve())
    rows=[]
    for st in range(1,37):
        for u in range(4):
            rows.extend(P.relocate_word(words[r],u,btab_bases=manifest['parameters'].get('BTAB_WORD_BASES')) for r in P.read_rows(st,u))
    (d/'expected.hex').write_text(''.join(f'{w:0263x}\n' for w in rows))
