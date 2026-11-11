#!/usr/bin/env python3
"""One source root + manifest that BOTH the as-built frame schedule tie (lower_xs.qualify_frame_source) and the slice
source lookup (slice_source.manifest_selection) accept, made from a bind's OWN as-built manifest (S81-PLAN-1 11-10).

A candidate bind's manifest (e.g. TYPE-SAFE-5 cand/asbuilt_bs.json) sits outside its source tree, has an absolute base
and names some files by absolute path outside it (romq / gb_split ROM elements, plan kits, hard_params).  Neither check
accepts that.  Given ROOT = a hard-link copy of the manifest base (cp -al, same device; never the shared tree itself),
this tool:
  * maps every file path in the manifest to a ROOT-relative one: paths under the base keep their relative path, paths
    outside it are hard-linked (copied across devices) to ext/<absolute path>;
  * requires every mapped file in ROOT to be byte-identical to the manifest's own file (sha256), else refuses;
  * writes ROOT/<--name> (base '.' relative to ROOT) and a receipt; the written manifest must select the same content
    as the original by dv_layer_compile.manifest_content, which the compiler re-checks at compile time;
  * optionally places this repo's frame_schedule_asb.py at ROOT/tools/s81_dv (rm first: ROOT is a hard-link copy).
Directory strings (e.g. stage_hash_roots) and non-path strings are left unchanged.  Nothing outside ROOT is written.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
sys.path[:0] = [str(REPO / 'tools/s81_dv')]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def place(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if sha(dst) != sha(src):
            raise ValueError(f'{dst} exists with other bytes than {src}')
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def build(manifest, root, name, extractor=True):
    manifest, root = Path(manifest).resolve(), Path(root).resolve()
    m = json.loads(manifest.read_text())
    b = Path(m.get('base', '.'))
    base = b if b.is_absolute() else (manifest.parent / b).resolve()
    if root == base:
        raise ValueError('ROOT must be a copy, never the manifest base itself')
    mapping = {}

    def remap(v):
        if isinstance(v, dict):
            return {k: remap(x) for k, x in v.items()}
        if isinstance(v, list):
            return [remap(x) for x in v]
        if not (isinstance(v, str) and '\n' not in v and len(v) < 4096):
            return v
        p = Path(v)
        src = p if p.is_absolute() else base / p
        if not src.is_file():
            return v
        src = src.resolve() if p.is_absolute() else src
        if p.is_absolute():
            rel = (src.relative_to(base).as_posix() if src.is_relative_to(base)
                   else 'ext' + src.as_posix())
        else:
            rel = p.as_posix()
        if '..' in Path(rel).parts:
            raise ValueError('path escapes the base: ' + v)
        dst = root / rel
        if p.is_absolute() and not src.is_relative_to(base):
            place(src, dst)
        if not dst.is_file() or sha(dst) != sha(src):
            raise ValueError(f'ROOT copy differs from the manifest file: {rel}')
        mapping[v] = dict(path=rel, sha256=sha(src))
        return rel
    out = remap({k: v for k, v in m.items() if k != 'base'})
    out['base'] = os.path.relpath(root, (root / name).parent)
    out['frame_root_note'] = (f'S81-PLAN-1 frame_root.py: ROOT-relative copy of {manifest} (sha256 {sha(manifest)}); '
                              'every file byte-identical to the original')
    dst = root / name
    if dst.exists():
        dst.unlink()
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, indent=1) + '\n')
    import dv_layer_compile as C
    if C.manifest_content(manifest) != C.manifest_content(dst):
        raise ValueError('frame-root manifest does not select the original content')
    if extractor:
        t = root / 'tools/s81_dv/frame_schedule_asb.py'
        if t.exists():
            t.unlink()
        shutil.copy2(REPO / 'tools/s81_dv/frame_schedule_asb.py', t)
    rec = dict(schema='opentallas.s81.frame_root.v1', manifest=str(manifest), manifest_sha256=sha(manifest),
               base=str(base), root=str(root), frame_manifest=name, frame_manifest_sha256=sha(dst),
               files_mapped=len(mapping), external=sorted(k for k, x in mapping.items() if x['path'].startswith('ext/')),
               extractor_sha256=sha(root / 'tools/s81_dv/frame_schedule_asb.py') if extractor else None,
               mapping=mapping)
    (root / (name + '.frame_root.json')).write_text(json.dumps(rec, indent=1) + '\n')
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--root', required=True, help='hard-link copy of the manifest base (cp -al)')
    ap.add_argument('--name', default='physical/die_plan/s81/bind/frame_asbuilt.json')
    ap.add_argument('--no-extractor', action='store_true')
    a = ap.parse_args()
    r = build(a.manifest, a.root, a.name, not a.no_extractor)
    print(f"FRAME_ROOT {r['root']} {r['frame_manifest']} sha {r['frame_manifest_sha256'][:12]} files {r['files_mapped']} "
          f"external {len(r['external'])}")


if __name__ == '__main__':
    main()
