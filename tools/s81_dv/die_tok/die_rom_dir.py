#!/usr/bin/env python3
"""TOK-DS-2 (11-01): assemble one +OT_ROM_DIR for the whole-die S81 bound top from per-frame field image dirs.

The bound top passes every frame ROM its original-path selector, e.g. INSTANCE "u_f_7L10.u_r1.u_c5_0" (cfg ROM) or
"u_f_7L10.u_r1.u_e5" (element; ot_v41_rom_elem_qx_pq_w10 appends _0/_1/b_0/b_1), and the macro model reads
<OT_ROM_DIR>/<INSTANCE>.viamap.hex.  The field image writer (tools/s81_dv xs_place / write_images) names the same
ROMs frame-locally: u_f_7L10_c5_0.viamap.hex, u_f_7L10_e5_0.viamap.hex (pair / element indices are frame-global in
both).  This tool links each writer image to its bound name (row u_rR looked up from the bound top) and reports
coverage: every bound selector with / without an image.  Nothing is renamed inside the images.

  die_rom_dir.py --rtl <bind out/rtl> --out ROMDIR IMGDIR [IMGDIR ...]
"""
import argparse, collections, json, os, re
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rtl', required=True, help='bound rtl dir (top + partition types: single-use types hardcode selectors)')
    ap.add_argument('--out', required=True)
    ap.add_argument('dirs', nargs='+')
    a = ap.parse_args()
    sel = set()
    for f in sorted(Path(a.rtl).glob('*.sv')):
        sel |= set(re.findall(r'\.\w*INSTANCE\("(u_f_\w+\.u_r\d+\.u_\w+)"\)', f.read_text()))
    sel = sorted(sel)
    row = {}                                        # (frame, local name e.g. c5_0 / e5) -> row
    for s in sel:
        f, r, n = s.split('.')
        row[(f, n[2:])] = r
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    have, srcs, unmapped = set(), {}, []
    for d in a.dirs:
        d = Path(d)
        for p in sorted(d.rglob('u_f_*.viamap.hex')):
            m = re.match(r'(u_f_\d[LR]\d+)_(c\d+_\d+|e\d+)([bew]?_\d)?\.viamap\.hex$', p.name)
            if not m:
                unmapped.append(str(p)); continue
            f, n, suf = m.group(1), m.group(2), m.group(3) or ''
            r = row.get((f, n))
            if r is None:
                unmapped.append(str(p)); continue
            name = f'{f}.{r}.u_{n}{suf}.viamap.hex'
            if name in srcs and srcs[name] != str(p.resolve()):
                raise SystemExit(f'conflict: {name} from {srcs[name]} and {p}')
            srcs[name] = str(p.resolve())
            dst = out / name
            if dst.is_symlink() or dst.exists():
                dst.unlink()
            os.symlink(p.resolve(), dst)
            have.add(f'{f}.{r}.u_{n}')
    frames = collections.Counter(s.split('.')[0] for s in sel)
    cov = collections.Counter(s.split('.')[0] for s in sel if s in have)
    rep = dict(selectors=len(sel), with_image=len(have & set(sel)), images_linked=len(srcs), unmapped=unmapped[:50],
               n_unmapped=len(unmapped), frames={f: [cov.get(f, 0), n] for f, n in sorted(frames.items())},
               frames_full=sorted(f for f in frames if cov.get(f, 0) == frames[f]),
               frames_none=sorted(f for f in frames if cov.get(f, 0) == 0))
    (out / 'die_rom_dir.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(f"selectors {rep['selectors']} with_image {rep['with_image']} linked {rep['images_linked']} unmapped "
          f"{rep['n_unmapped']} frames full {len(rep['frames_full'])} none {len(rep['frames_none'])} of {len(frames)}")


if __name__ == '__main__':
    main()
