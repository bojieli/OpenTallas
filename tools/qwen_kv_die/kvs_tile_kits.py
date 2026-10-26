#!/usr/bin/env python3
"""KV-INTEG/KITS-A 2026-10-18 (RTL-BUILD-KV item M1): physical kits of the KV die's three singleton static tiles
kvs_ctl / kvs_attn / kvs_emb (masters qkd_kvs_ctl / qkd_kvs_attn / qkd_kvs_emb), generated MECHANICALLY from the tile
generator so a regenerated tile (FAULT adds qkd_attn_fault_root to kvs_attn, BOOT changes the ctl fan root) re-kits with
one command:

    source /home/ubuntu/wt/kvj-g2-env.sh; export OT_KV_HROOT=1 OT_KV_FANFOLD=1 OT_KV_TILE_KITS=1
    python3 tools/qwen_kv_die/kvs_tile_kits.py [--tiles ctl,attn,emb] [--no-rtl] [--tag a1]
    python3 tools/ref_tile/ref_tile.py gen tools/ref_tile/specs/qkd_kvs_<t>.json      (done by this script)

Per tile (top-down contract, memory top-down-hierarchy-contract):
  * hierarchy: a child whose module has a CLOSED view of the SAME source + parameters (KIT_VIEWS, checked by sha256 of
    the view's source binding) is a hard child (kind cluster, view from physical/ref_tile/<kit>/views); every other
    child is flattened into the tile (all of them are small glue / calendars without macros).  The closed views of
    qkd_kv_native_programme (p2) and qkd_kv_static_writer_native (r3) are NOT used: both were closed on older RTL with
    VMAP=0; the die instantiates VMAP=1 (writer programme / writer of the static V map).
  * pins: the die's own faces (kv_static_die.KVS_FACES / pin_face under OT_KV_TILE_KITS), one clock port 'ck'.
  * pin registers OFF (reason in the spec): every tile <-> tile / die-master hop is priced in the compiled join ages
    with the die relays only (kv_relays / die_ages.json); a tile pin register would add an unpriced edge to every one.
    The children's boundary nets are their own registers (gate path classes in->reg / reg->out confirm it).
  * outline: square-ish, from the gate-measured std area at util 0.50 and from the densest face at <= 5.5 pins/um
    (the die frame record kv_static_die.FRAME is ASSUMED; the new size is printed for KV-PLAN3).
"""
import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

TILES = dict(ctl='kvs_ctl', attn='kvs_attn', emb='kvs_emb')
MASTER = dict(ctl='qkd_kvs_ctl', attn='qkd_kvs_attn', emb='qkd_kvs_emb')
# closed views usable as hard children: module -> (view dir, rtl file, source commit of the CLOSED job: the tree's file
# must be byte-identical to it)
KIT_VIEWS = {
    'qkd_embedding_row_tx': ('physical/ref_tile/qkd_embedding_row_tx/views/qkd_embedding_row_tx',
                             'rtl/qwen_sys/static_embedding_20261014/qkd_embedding_row_tx.sv',
                             'b97c79344'),    # closure-loop job qkd_embedding_row_tx-r2-b97c79344 (CLOSED 10-17)
}
# hard child orientation / placement inside the cluster: row_tx's emb_tx face (LEF W) toward the D2D end (tile E)
CHILD_ORIENT = {'qkd_embedding_row_tx': 'MY'}
# lower-left origin on the 43.2-um child lattice: row_tx (216 x 151.2) 43.2 um off the E face, the join logic W / S of it
CHILD_AT = {'qkd_embedding_row_tx': lambda w, h: [w - 216.0 - 43.2, 86.4]}
PIN_DENSITY = 5.5            # pins / um on the densest face (owner <= 6)
UTIL = 0.50
LAT = 43.2                   # hard-child lattice; outlines snapped to it
# gate-measured standard-cell area (um2) per tile, filled after the first remote gate (None: first gate measures it)
STD_AREA = {'ctl': None, 'attn': None, 'emb': None}
SEED_OUTLINE = {'ctl': (475.2, 475.2), 'attn': (302.4, 302.4), 'emb': (388.8, 302.4)}


def need_env():
    want = dict(OT_KV_STATIC_DIE='1', OT_KV_HROOT='1', OT_KV_FANFOLD='1', OT_KV_TILE_KITS='1')
    bad = {k: os.environ.get(k) for k, v in want.items() if os.environ.get(k) != v}
    if bad:
        raise SystemExit(f'kvs_tile_kits: source /home/ubuntu/wt/kvj-g2-env.sh and export {want} (got {bad})')


def module_index():
    """module name -> [rtl files defining it]"""
    out = {}
    for f in sorted((ROOT / 'rtl').rglob('*.sv')) + sorted((ROOT / 'rtl').rglob('*.v')):
        try:
            txt = f.read_text(errors='replace')
        except OSError:
            continue
        for m in re.finditer(r'^\s*module\s+([A-Za-z_]\w*)', txt, re.M):
            out.setdefault(m.group(1), []).append(str(f.relative_to(ROOT)))
    return out


def instantiated(path):
    txt = re.sub(r'//[^\n]*', '', (ROOT / path).read_text(errors='replace'))
    txt = re.sub(r'/\*.*?\*/', '', txt, flags=re.S)
    kw = {'module', 'input', 'output', 'inout', 'wire', 'reg', 'assign', 'always', 'if', 'else', 'begin', 'end', 'case',
          'for', 'generate', 'integer', 'localparam', 'parameter', 'function', 'task', 'logic', 'genvar', 'initial'}
    return {m.group(1) for m in re.finditer(r'^\s*([A-Za-z_]\w*)\s*(?:#\s*\(.*?\))?\s+[A-Za-z_][\w\[\]]*\s*\(', txt,
                                                re.M | re.S) if m.group(1) not in kw}


def closure(top_files, mods, idx, prefer, exclude=()):
    """rtl files needed by the modules mods (transitively), excluding hard-child modules"""
    files, seen, todo = [], set(), list(mods)
    while todo:
        m = todo.pop()
        if m in seen or m in exclude:
            continue
        seen.add(m)
        cand = idx.get(m, [])
        if not cand:
            continue                      # macro / cell (yosys lib) or a hard child
        pick = next((c for c in cand if c in prefer), None) or (cand[0] if len(cand) == 1 else None)
        if pick is None:
            raise SystemExit(f'kvs_tile_kits: module {m} defined in several files {cand}; add it to the preferred set')
        if pick not in files:
            files.append(pick)
        if pick not in top_files:         # the shared tile file: only the tile module's own children (mods) count
            for sub in instantiated(pick):
                todo.append(sub)
    return [f for f in top_files if f not in files] + files


def view_source_sha(rtl, commit):
    """sha256 of the RTL file at the CLOSED job's source commit"""
    blob = subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{commit}:{rtl}'])
    return hashlib.sha256(blob).hexdigest()


def snap(x):
    return math.ceil(x / LAT - 1e-9) * LAT


def outline(t, faces):
    """square-ish outline: area at UTIL (if measured) and the densest face at <= PIN_DENSITY"""
    wmin = max(faces.get('N', 0), faces.get('S', 0)) / PIN_DENSITY
    hmin = max(faces.get('W', 0), faces.get('E', 0)) / PIN_DENSITY
    area = STD_AREA[t]
    if area is None:
        w, h = SEED_OUTLINE[t]
        return snap(max(w, wmin)), snap(max(h, hmin))
    side = math.sqrt(area / UTIL)
    w, h = max(side, wmin), max(side, hmin)
    if w * h < area / UTIL:
        w = area / UTIL / h
    return snap(w), snap(h)


def build(tiles_sel, tag, write_rtl=True):
    need_env()
    import kv_static_die as S
    if write_rtl:
        (ROOT / S.RTL_FILE).write_text(S.rtl_text())
    T = S.all_tiles()
    idx = module_index()
    prefer = set(S.sources()) | {S.RTL_FILE}
    rtl_sha = hashlib.sha256((ROOT / S.RTL_FILE).read_bytes()).hexdigest()
    out = {}
    for t in tiles_sel:
        d, master = TILES[t], MASTER[t]
        tl = T[d]
        mods = sorted({S.ins()[n]['module'] for n in tl['members']})
        hard = [m for m in mods if m in KIT_VIEWS]
        srcs = closure([S.RTL_FILE], [master] + mods, idx, prefer, exclude=hard)
        if S.RTL_FILE not in srcs:
            srcs.insert(0, S.RTL_FILE)
        faces, pins = {}, {f: [] for f in 'NSEW'}
        for pn, v in tl['ports'].items():
            f = S.pin_face(master, pn)
            if f is None:
                raise SystemExit(f'kvs_tile_kits: {master}.{pn} has no face (OT_KV_TILE_KITS unset?)')
            pins[f].append(pn)
            faces[f] = faces.get(f, 0) + v['width']
        for f in pins:
            pins[f] = S.face_order(master, f, pins[f])
        ck = [pn for pn, v in tl['ports'].items() if v['cls'] == 'clock']
        if ck != ['ck']:
            raise SystemExit(f'kvs_tile_kits: {master} clock ports {ck} (expected one ck: OT_KV_TILE_KITS=1)')
        resets = [pn for pn, v in tl['ports'].items() if v['cls'] in ('reset', 'pad')]
        children = []
        for m in hard:
            view, rtl, commit = KIT_VIEWS[m]
            vs = view_source_sha(rtl, commit)
            cur = hashlib.sha256((ROOT / rtl).read_bytes()).hexdigest()
            if vs != cur:
                raise SystemExit(f'kvs_tile_kits: closed view {view} was built on {rtl} sha {vs}, tree has {cur}')
            children.append(dict(view=view, count=1, orient=CHILD_ORIENT.get(m, 'R0'), at=CHILD_AT[m](*outline(t, faces)),
                                 inst='*u_' + next(S.cluster_of(n)[2] for n in tl['members'] if S.ins()[n]['module'] == m)))
        w, h = outline(t, faces)
        name = master
        bench = f'KVS_SIM=verilator bash tools/qwen_kv_die/kvs_tile_bench.sh {{RUN}}/bench/{t}_m{{M}} {t} {{M}}'
        res = os.environ.get('KVS_KIT_RES', 'results/rtl/qwen_kv_die/kvs_kits_1018')
        benches = [dict(name=f'{t}_lockstep', cmd=bench.replace('{M}', '0'), expect='pass', threads=4, peak_ram_gb=8,
                        needs=['verilator'], pass_regex=rf'^KVS_TILE PASS tile={t} .* errors=0 mut=0',
                        min_count_regex=r'checks=(\d+)', pass_witness=f'{res}/{t}_m0.log')]
        for mut in (1, 2, 3):
            benches.append(dict(name=f'{t}_mut{mut}', cmd=bench.replace('{M}', str(mut)), expect='fail', threads=4,
                                peak_ram_gb=8, needs=['verilator'], pass_regex=rf'^KVS_TILE PASS tile={t} ',
                                fail_regex=rf'^KVS_TILE FAIL tile={t} .* mut={mut} ', fail_witness=f'{res}/{t}_m{mut}.log'))
        if t == 'attn' and os.environ.get('OT_KV_ATTN_LAND', '0') == '1':
            # KV-ATTNKIT 10-18: pair lockstep of the registered boundary vs the as-built chain (16 modes) + 4 mutants
            pb = 'bash tools/qwen_kv_die/kvs_attn_land_pair_bench.sh {RUN}/bench/land_pair_%s %s %s "%s"'
            benches.append(dict(name='attn_land_pair', cmd=pb % ('m0', 0, 0, ' '.join(map(str, range(16)))), expect='pass',
                                threads=2, peak_ram_gb=4, needs=['verilator'], pass_regex=r'^KVS_LANDPAIR_ALL PASS bmut=0 fmut=0 ',
                                min_count_regex=r'checks=(\d+)', pass_witness=f'{res}/land_pair_m0.log'))
            for mt, bm, fm, md in (('b5', 5, 0, '0'), ('b6', 6, 0, '8'), ('b4', 4, 0, '13'), ('f5', 0, 5, '0')):
                benches.append(dict(name=f'attn_land_pair_{mt}', cmd=pb % (mt, bm, fm, md), expect='fail', threads=2,
                                    peak_ram_gb=4, needs=['verilator'], pass_regex=r'^KVS_LANDPAIR_ALL PASS ',
                                    fail_regex=rf'^KVS_LANDPAIR_ALL FAIL bmut={bm} fmut={fm} ',
                                    fail_witness=f'{res}/land_pair_{mt}.log'))
        spec = OrderedSpec(
            name=name, top=master, sources=srcs, params={}, reset_ports=['rst_n'] + [r for r in resets if r != 'rst_n'],
            pins={f: pins[f] for f in 'NSEW'},
            pin_regs=dict(enable=False, reason=(
                'Generated wires-only parent of the static join: every tile <-> tile / die-master hop is priced in the '
                'compiled join ages with the die relays only (kv_relays, die_ages.json); a recipe-3 pin register would add '
                'an unpriced edge to every crossing.  The children land / launch their boundary nets in their own flops.')),
            kind='cluster' if children else 'tile', clock_port='ck', layer_cap='M5', macros=[], children=children,
            inter=[], keep_pin_regs=True, inhold=True, outhold=True, io_flop_at_pins=dict(cols=4, allow_none=True),
            route=dict(pd=0.5, threads=8, peak_ram_gb=24, pin_min_tracks=3, m5_pg_pitch=2.7, hold_margin_ns=0.03,
                       io_hold_margin_ns=0.03, macro_halo_um=5.4),     # KITS 10-18: boundary margin >= 0.025
            recipe=3, pin_reg_split=True, hold_pad=dict(cell='HB2xp67_ASAP7_75t_R'),
            outline=dict(w=w, h=h, exact=True),
            structural_change=(
                f'NEW kit (RTL-BUILD-KV M1, KV-INTEG/KITS-A): generated static tile {master} of the KV die '
                f'({len(tl["members"])} children: {", ".join(mods)}; hard: {", ".join(hard) or "none"}), from '
                f'{S.RTL_FILE} (sha256 {rtl_sha[:12]}) by tools/qwen_kv_die/kvs_tile_kits.py; one clock port ck '
                f'(OT_KV_TILE_KITS).  Faces {faces} pins on {w:.1f} x {h:.1f} um (die frame record '
                f'{S.FRAME[t]} ASSUMED -> this outline for KV-PLAN3).'),
            job=dict(owner=os.environ.get('KVS_KIT_OWNER', 'Claude:KV-INTEG2'),
                     branch=os.environ.get('KVS_KIT_BRANCH', 'claude/kv-integ2-kits-1018'), tag=tag,
                     purpose=(f'KV-INTEG/KITS-A 10-18 (RTL-BUILD-KV M1): kit of the generated singleton static tile '
                              f'{master}.  Bench: LOCKSTEP of the kit top (one ck) against the die-bound tile of the '
                              f'same design point without OT_KV_TILE_KITS (per-child clock ports, all on the one die '
                              f'trunk), random inputs from reset + a phase with every child output wire forced random; '
                              f'mutants: a dropped child wire (1), two swapped wire slices (2), a missing child (3).'),
                     benches=benches,
                     extra_paths=['rtl', 'tools', 'results/arch/qwen_kv_static_programme_1017', 'results/arch/qwen_kv_die',
                                  'results/arch/qwen_kv_pvfin_1017', res] + [c['view'] for c in children],
                     views_to=f'physical/ref_tile/{name}/views', record_to=f'results/rtl/ref_tile/{name}'))
        if STD_AREA[t] is not None:
            spec['std_area_um2'] = STD_AREA[t]
        p = ROOT / 'tools/ref_tile/specs' / f'{name}.json'
        p.write_text(json.dumps(spec, indent=1) + '\n')
        out[t] = dict(spec=str(p.relative_to(ROOT)), outline=(w, h), faces=faces, frame=S.FRAME[t], hard=hard,
                      sources=len(srcs))
    return out


def OrderedSpec(**kw):
    return dict(kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tiles', default='ctl,attn,emb')
    ap.add_argument('--tag', default='a1')
    ap.add_argument('--no-rtl', action='store_true', help='do not rewrite the tile RTL file')
    ap.add_argument('--no-gen', action='store_true', help='specs only (no ref_tile.py gen)')
    a = ap.parse_args()
    sel = a.tiles.split(',')
    res = build(sel, a.tag, write_rtl=not a.no_rtl)
    for t, r in res.items():
        print(f'KVS_KIT {t} spec={r["spec"]} outline={r["outline"][0]:.1f}x{r["outline"][1]:.1f} (frame {r["frame"]}) '
              f'faces={r["faces"]} hard={r["hard"]} sources={r["sources"]}')
        if not a.no_gen:
            subprocess.check_call([sys.executable, 'tools/ref_tile/ref_tile.py', 'gen', r['spec']], cwd=ROOT)


if __name__ == '__main__':
    main()
