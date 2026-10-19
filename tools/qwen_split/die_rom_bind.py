#!/usr/bin/env python3
"""Bind every Qwen compute-die tile code ROM to its image and audit the binding (QW-DIEFIX 10-19).

QW-XHEAD XT1 found that the die GEN bound NO ROM content: die.v instantiates 48 qfd_c_b16_dv clusters whose 16 tiles carry
ROM_TILE = -1, so every ROM macro model's INSTANCE is "" and a die-netlist simulation reads all-zero code ROMs.  The tile
identity is a strap (tile_id = {cid 12, 4 tie bits}, qfd_c_b16_dv.sv) and the sim-only ROM_TILE parameter must equal it
(qfd_tile_n?_rp2_45 traps a mismatch at run time); the macro model then loads +OT_ROM_DIR/qtile_t{T}_b{B}_c{C}.viamap.hex
(ot_qwen_tile_romleaf / ot_qwen_tile_rpair INSTANCE).  This tool:

  * reads die.v (each qfd_c_b16_dv instance + its CONSTANT cid strap) and the cluster source (each u_t_<c>_<r> tile, its
    master, its tile_id tie bits tl = 0 / th = 1 -> kslice);
  * emits rom_bind.vh: sim-only defparams `defparam <PREFIX><inst>.u_t_c_r.ROM_TILE = 16 cid + kslice;` (PREFIX defaults to
    "`OT_ROM_BIND_TOP." so any bench names its die instance; --prefix '' / --only for single-cluster vehicles);
  * emits rom_bind.json: per tile path, ROM_TILE, its 10 macro INSTANCE ids (5 banks x 2 columns), the mask manifest
    (path + sha256 + rank + partial stages) and the audit;
  * AUDIT (fail closed, exit 1): every cluster has a constant cid; ROM_TILE == the strap value for every tile; values unique
    and, on a full die (48 clusters), exactly 0..767; every tile master passes ROM_TILE down to a ROM leaf that forms the
    qtile_t%0d_b%0d_c.. INSTANCE (source scan); with --masks, every macro instance has a manifest entry whose file exists,
    is non-empty and matches its sha256 (full hash, or --hash-sample N files).

    die_rom_bind.py DIE_V [--root SRC] [--masks MANIFEST.json] [--rank 0] [--out-dir DIR] [--prefix P] [--only a,b]
Prints one ROM_BIND_AUDIT PASS|FAIL line.  Exit 0 PASS, 1 FAIL.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path

CLUSTER = 'qfd_c_b16_dv'
CLUSTER_SRC = 'rtl/physical/qcluster/qfd_c_b16_dv.sv'
SEARCH = ('rtl/physical', 'rtl/hdc')
LEAVES = {'ot_qwen_tile_romleaf', 'ot_qwen_tile_rpair'}
BANKS, COLS, TILES_PER_CLUSTER, DIE_CLUSTERS = 5, 2, 16, 48


def _int(lit: str) -> int:
    m = re.fullmatch(r"\s*(?:(\d+)?'([hdbHDB]))?([0-9a-fA-F_]+)\s*", lit)
    if not m:
        raise ValueError(lit)
    base = {'h': 16, 'd': 10, 'b': 2}[(m.group(2) or 'd').lower()]
    return int(m.group(3).replace('_', ''), base)


def parse_cluster(src: str):
    """{inst: dict(master, bits [msb..lsb] tie names, kslice)} for every tile of the cluster source"""
    tiles = {}
    for m in re.finditer(r'^\s*(qfd_tile_\w+)\s+(u_t_(\d+)_(\d+))\s*\((.*?)\);', src, re.S | re.M):
        master, inst, body = m.group(1), m.group(2), m.group(5)
        t = re.search(r'\.tile_id\(\{\s*cid\s*,([^}]*)\}\)', body)
        if not t:
            raise ValueError(f'{inst}: no tile_id({{cid, ...}}) strap')
        names = [x.strip() for x in t.group(1).split(',')]
        bits = []
        for n in names:
            k = re.fullmatch(r'(th|tl)_(\d+)_(\d+)', n)
            if not k or (k.group(2), k.group(3)) != (m.group(3), m.group(4)):
                raise ValueError(f'{inst}: tile_id bit {n} is not this tile\'s own tie')
            bits.append(1 if k.group(1) == 'th' else 0)
        ks = 0
        for b in bits:
            ks = (ks << 1) | b
        tiles[inst] = dict(master=master, ties=names, kslice=ks, width=len(bits))
    return tiles


def parse_die(text: str):
    """[(inst, cid or None, cid_text)] for every qfd_c_b16_dv instance of die.v"""
    out = []
    for m in re.finditer(r'^\s*' + CLUSTER + r'\s+(?:#\(.*?\)\s*)?(\S+)\s*\((.*?)\);', text, re.S | re.M):
        inst, body = m.group(1), m.group(2)
        c = re.search(r'\.cid\(([^()]*)\)', body)
        if not c:
            out.append((inst, None, '<unconnected>'))
            continue
        try:
            out.append((inst, _int(c.group(1)), c.group(1).strip()))
        except ValueError:
            out.append((inst, None, c.group(1).strip()))
    return out


def module_index(root: Path):
    idx = {}
    for d in SEARCH:
        for f in sorted((root / d).glob('*.sv')):
            for m in re.finditer(r'^\s*module\s+(\w+)', f.read_text(errors='replace'), re.M):
                idx.setdefault(m.group(1), f)
    return idx


def module_text(path: Path, name: str) -> str:
    s = path.read_text(errors='replace')
    m = re.search(r'^\s*module\s+' + name + r'\b', s, re.M)
    e = s.find('endmodule', m.end())
    return s[m.start():e]


def rom_tile_children(text: str):
    """child modules instantiated with .ROM_TILE(ROM_TILE) in their parameter list"""
    kids = set()
    for m in re.finditer(r'\.ROM_TILE\(\s*ROM_TILE\s*\)', text):
        pre = text[:m.start()]
        h = pre.rfind('#(')
        if h < 0:
            continue
        head = re.sub(r'`(ifndef|ifdef|else|endif)\b[^\n]*', ' ', pre[:h])
        w = re.findall(r'(\w+)\s*$', head)
        if w:
            kids.add(w[0])
    return kids


def chain_scan(root: Path, masters):
    """per tile master: the module path that carries ROM_TILE to a leaf forming the qtile INSTANCE (or the failure)"""
    idx = module_index(root)
    res = {}
    for top in sorted(masters):
        paths, fails, seen = [], [], set()

        def walk(mod, trail):
            if mod in seen and mod not in LEAVES:
                return
            seen.add(mod)
            if mod not in idx:
                fails.append(f'{"/".join(trail)}: module source not found')
                return
            txt = module_text(idx[mod], mod)
            if not re.search(r'parameter\s+integer\s+ROM_TILE\b', txt):
                fails.append(f'{"/".join(trail)}: no ROM_TILE parameter')
                return
            if mod in LEAVES:
                if 'qtile_t%0d_b%0d_c' not in txt:
                    fails.append(f'{mod}: leaf does not form INSTANCE qtile_t%0d_b%0d_c..')
                else:
                    paths.append(trail)
                return
            kids = rom_tile_children(txt)
            if not kids:
                fails.append(f'{"/".join(trail)}: ROM_TILE not passed to any child')
            for k in sorted(kids):
                walk(k, trail + [k])

        walk(top, [top])
        res[top] = dict(ok=bool(paths) and not fails, leaf_paths=paths, fails=fails)
    return res


def load_manifest(path: Path, rank):
    doc = json.loads(path.read_text())
    if doc.get('schema') == 'opentallas.qwen-tp8-native-code-masks.v1':
        rows = [r for r in doc['rank_manifests'] if rank is None or r['rank'] == rank]
        if len(rows) != 1:
            raise ValueError(f'{path}: rank {rank} not in the mask set')
        sub = Path(rows[0]['manifest'])
        if not sub.is_absolute() or not sub.exists():
            sub = path.parent / f"rank{rows[0]['rank']}" / 'manifest.json'
        return load_manifest(sub, rows[0]['rank'])
    if doc.get('schema') != 'opentallas.qwen-tp8-native-code-mask-rank.v1':
        raise ValueError(f'{path}: not a code-mask manifest')
    if rank is not None and doc['rank'] != rank:
        raise ValueError(f'{path}: rank {doc["rank"]} != {rank}')
    cols = {}
    for p in doc['pairs']:
        for c in p['columns']:
            cols[c['instance']] = c
    return path, doc, cols


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for blk in iter(lambda: f.read(1 << 22), b''):
            h.update(blk)
    return h.hexdigest()


def run(die_v: Path, root: Path, masks: Path | None, rank, prefix: str, only, hash_sample: int):
    fails = []
    tiles = parse_cluster((root / CLUSTER_SRC).read_text())
    if len(tiles) != TILES_PER_CLUSTER or sorted(t['kslice'] for t in tiles.values()) != list(range(TILES_PER_CLUSTER)):
        fails.append(f'cluster source: {len(tiles)} tiles, kslices {sorted(t["kslice"] for t in tiles.values())} != 0..15')
    clusters = parse_die(die_v.read_text())
    if only:
        miss = sorted(set(only) - {c[0] for c in clusters})
        if miss:
            fails.append(f'--only instances not in die.v: {miss}')
        clusters = [c for c in clusters if c[0] in only]
    if not clusters:
        fails.append(f'no {CLUSTER} instance in {die_v}')
    bind, vh = [], [f'// rom_bind.vh -- generated by tools/qwen_split/die_rom_bind.py from {die_v.name} (sim only: ROM_TILE = '
                    f'tile_id strap = 16 cid + kslice; masks +OT_ROM_DIR=<mask dir>)']
    if prefix.startswith('`'):
        vh += ['`ifndef OT_ROM_BIND_TOP', '`define OT_ROM_BIND_TOP u_die', '`endif']
    for inst, cid, ctext in clusters:
        if cid is None:
            fails.append(f'{inst}: cid strap not a constant ({ctext})')
            continue
        for tn, t in sorted(tiles.items()):
            rt = (cid << t['width']) | t['kslice']
            strap = cid * TILES_PER_CLUSTER + t['kslice']
            if rt != strap:
                fails.append(f'{inst}.{tn}: ROM_TILE {rt} != strap {strap}')
            vh.append(f'defparam {prefix}{inst}.{tn}.ROM_TILE = {rt};')
            bind.append(dict(path=f'{inst}.{tn}', cluster=inst, cid=cid, tile=tn, master=t['master'], kslice=t['kslice'],
                             ROM_TILE=rt, macros=[f'qtile_t{rt}_b{b}_c{c}' for b in range(BANKS) for c in range(COLS)]))
    vals = [b['ROM_TILE'] for b in bind]
    dup = sorted({v for v in vals if vals.count(v) > 1})
    if dup:
        fails.append(f'duplicate ROM_TILE values {dup[:10]}')
    full = not only
    if full and len(clusters) == DIE_CLUSTERS and sorted(vals) != list(range(DIE_CLUSTERS * TILES_PER_CLUSTER)):
        fails.append(f'full die: ROM_TILE set != 0..{DIE_CLUSTERS * TILES_PER_CLUSTER - 1} '
                     f'(min {min(vals, default=None)} max {max(vals, default=None)} n {len(vals)})')
    if full and len(clusters) != DIE_CLUSTERS:
        fails.append(f'full die: {len(clusters)} clusters != {DIE_CLUSTERS}')
    chain = chain_scan(root, {t['master'] for t in tiles.values()})
    for mst, r in chain.items():
        if not r['ok']:
            fails.append(f'ROM_TILE chain {mst}: {r["fails"][:3] or "no leaf reached"}')
    mrec = None
    if masks is not None:
        mpath, doc, cols = load_manifest(masks, rank)
        mdir = mpath.parent / 'masks'
        want = [m for b in bind for m in b['macros']]
        missing = [m for m in want if m not in cols]
        if missing:
            fails.append(f'mask manifest lacks {len(missing)} of {len(want)} macro instances (e.g. {missing[:3]})')
        present = [m for m in want if m in cols]
        bad_file = [m for m in present if not (mdir / cols[m]['file']).is_file() or (mdir / cols[m]['file']).stat().st_size == 0]
        if bad_file:
            fails.append(f'{len(bad_file)} mask files missing or empty (e.g. {bad_file[:3]})')
        ok_files = [m for m in present if m not in bad_file]
        hashed = ok_files if hash_sample <= 0 else random.Random(0).sample(ok_files, min(hash_sample, len(ok_files)))
        bad_sha = [m for m in hashed if sha(mdir / cols[m]['file']) != cols[m]['sha256']]
        if bad_sha:
            fails.append(f'{len(bad_sha)} mask files do not match their manifest sha256 (e.g. {bad_sha[:3]})')
        mrec = dict(manifest=str(mpath), manifest_sha256=sha(mpath), rank=doc['rank'], mask_dir=str(mdir),
                    partial_stages=doc.get('partial_stages', []), macros_bound=len(want), macros_in_manifest=len(present),
                    files_ok=len(ok_files), hashed=len(hashed), hash_mode='full' if hash_sample <= 0 else f'sample {hash_sample}',
                    checkpoint_revision=doc.get('checkpoint_revision'))
    verdict = 'PASS' if not fails else 'FAIL'
    audit = dict(verdict=verdict, fails=fails, clusters=len(clusters), tiles=len(bind), macros=len(bind) * BANKS * COLS,
                 rom_tile_min=min(vals, default=None), rom_tile_max=max(vals, default=None), full_die=full,
                 chain={k: dict(ok=v['ok'], leaf_paths=[' > '.join(p) for p in v['leaf_paths']][:4], fails=v['fails'])
                        for k, v in chain.items()},
                 masks=mrec or 'not given (structural audit only: a bench without +OT_ROM_DIR masks still reads ZERO ROMs)')
    doc = dict(schema='opentallas.qwen_split.rom_bind.v1', die_v=str(die_v), die_v_sha256=sha(die_v),
               cluster_source=CLUSTER_SRC, cluster_source_sha256=sha(root / CLUSTER_SRC), prefix=prefix, audit=audit,
               tiles=bind)
    return verdict, doc, '\n'.join(vh) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('die_v', type=Path)
    ap.add_argument('--root', type=Path, default=Path('.'))
    ap.add_argument('--masks', type=Path, default=None, help='code-mask manifest (tools/qwen_code_rom/build.py)')
    ap.add_argument('--rank', type=int, default=None)
    ap.add_argument('--out-dir', type=Path, default=None, help='default: beside die.v')
    ap.add_argument('--prefix', default='`OT_ROM_BIND_TOP.')
    ap.add_argument('--only', default='', help='comma list of cluster instances (single-cluster vehicles)')
    ap.add_argument('--hash-sample', type=int, default=0, help='0 = hash every mask file')
    a = ap.parse_args(argv)
    only = [x for x in a.only.split(',') if x]
    verdict, doc, vh = run(a.die_v, a.root, a.masks, a.rank, a.prefix, only, a.hash_sample)
    od = a.out_dir or a.die_v.parent
    od.mkdir(parents=True, exist_ok=True)
    (od / 'rom_bind.vh').write_text(vh)
    (od / 'rom_bind.json').write_text(json.dumps(doc, indent=1) + '\n')
    au = doc['audit']
    m = au['masks']
    print(f"ROM_BIND_AUDIT {verdict} clusters={au['clusters']} tiles={au['tiles']} macros={au['macros']} "
          f"rom_tile={au['rom_tile_min']}..{au['rom_tile_max']} chain_ok={sum(v['ok'] for v in au['chain'].values())}/"
          f"{len(au['chain'])} masks=" + (f"{m['files_ok']}/{m['macros_bound']} hashed {m['hashed']} rank {m['rank']} "
                                           f"partial {m['partial_stages'][:3]}{'...' if len(m['partial_stages']) > 3 else ''}"
                                           if isinstance(m, dict) else 'none')
          + ('' if verdict == 'PASS' else f" fails={au['fails'][:4]}"))
    return 0 if verdict == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
