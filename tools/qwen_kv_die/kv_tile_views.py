#!/usr/bin/env python3
"""KV-FACELAND-WIRE 10-19: bind the CLOSED views of the static KV die's generated control tiles (qkd_kvs_attn / _ctl / _emb /
_grp / _grp_h / _pc / _pc_h) in place of their ASSUMED frames, ONLY where the closed netlist is the tile the die schedules.

Before this tool the kvs_* tiles were frames in every KV die (views.json bound only dcal / hgs / hss / kvs_hroot /
pv16_vport / rst_region) while OT_KV_FACE_LAND=1 charged the kvs_attn (fin / i_ctl / reset) and hr_core_queue edges in the
compiler: schedule != netlist.  Per die tile master this tool

  1. finds every kit physical/ref_tile/<kit> whose spec top is the master (or <master>_fl) with a CLOSED view
     (views/<vm>/<vm>.lef + _tt.lib + _ff.lib + insertion.json), vm = <master>_fl when the tile is selected in
     OT_KV_FACE_LAND, else <master>;
  2. IDENTITY: the view's source commit (its closure-loop route name) -> the kit spec AT that commit; the tile module text in
     the kit's tile file at that commit must equal the module in the die's tile file (kv_static_die.RTL_FILE, comments and
     whitespace ignored), and every other kit source must be byte-identical (git blob) between that commit and HEAD;
  3. EDGES (per-tile kv_static_params check): the cycles the closed netlist adds at its faces must equal what the die's
     static schedule charges for the tile:
       pin registers (recipe-3 pin_regs, effective spec): +in / +out on every data pin   -- the die charges 0 today
       face-land wrapper landed buses (rtl/lib/face_land header 'landed buses: fin +1, i_ctl +1') -- the die charges
         kv_static_die.FACE_LAND_TILES[tile] buses when selected, else 0
       reset release (face-land relay +3, ref_tile reset_landing stages): startup only, checked against
         kv_static_die.FACE_LAND_RST_BUDGET (as kv_static_programme._face_land does), recorded
  4. emits --view <master>=<dir> for bind_views.py for every PASS view (newest source commit wins), records every refusal
     (the frame stays ASSUMED, reason in RUN/tile_views.json), and FAILS (exit 3) when a tile selected in OT_KV_FACE_LAND
     has no die instance (hr_core_queue lives inside the qkd_host_rt frame) or no PASS _fl view: the compiler would charge
     edges no netlist has.

    select:  kv_tile_views.py select --out RUN/tile_views.json            (stdout: the bind_views --view args)
    check:   kv_tile_views.py check --record RUN/tile_views.json --views RUN/libs/views.json [--die-bound die_bound.v]
             (every PASS view bound by bind_views; every selected face-land tile bound to its _fl module) -> exit 1 on FAIL
kv_static_params.py runs check() on the die chain's die_bound.v when RUN/tile_views.json exists.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'tools'))

SCHEMA = 'opentallas.qwen_kv.tile_views.v1'
REF = 'physical/ref_tile'
SKIP = ('qkd_kvs_hroot',)      # bound by kvsys_prep OT_KV_HROOT_VIEW (labelled stand-in), not here
# tiles of the face-land table that are NOT top-level die instances of the static die (host cluster children of the
# qkd_host_rt frame; ASTK strip relays placed by kv_astk_expand)
NOT_TOP = {'hr_core_queue': 'child of the host cluster: the KV die instantiates the qkd_host_rt FRAME (host cluster parent '
                            'not built / bound), so no qkd_hr_core_queue instance exists to bind its _fl view',
           'astk_rly_296': 'expanded ASTK strip child (kv_astk_expand binds qkd_astk_rly_296_fl)'}


def _ksd():
    import kv_static_die as KSD
    return KSD


def git(*a):
    r = subprocess.run(['git', '-C', str(ROOT), *a], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def show(rev, path):
    if rev == 'HEAD' and (ROOT / path).exists():
        return (ROOT / path).read_text(errors='replace')
    return git('show', f'{rev}:{path}')


def blob(rev, path):
    o = git('rev-parse', f'{rev}:{path}')
    return o.strip() if o else None


def module_text(text, name):
    if not text:
        return None
    t = re.sub(r'/\*.*?\*/', '', re.sub(r'//[^\n]*', '', text), flags=re.S)
    m = re.search(r'\bmodule\s+' + re.escape(name) + r'\b(.*?)\bendmodule', t, re.S)
    return re.sub(r'\s+', ' ', m.group(1)).strip() if m else None


def view_source(vdir):
    """the closure-loop route's source commit (provenance/view_export.abstract.json orfs_dir .../<kit>-<tag>-<sha9>/...)"""
    p = vdir / 'provenance' / 'view_export.abstract.json'
    if not p.exists():
        return None, None
    m = re.search(r'closure-loop/([^/"]+)-([0-9a-f]{9})/', p.read_text(errors='replace'))
    if not m:
        return None, None
    full = git('rev-parse', '--verify', '-q', m.group(2) + '^{commit}')
    return (full.strip() if full else None), m.group(1) + '-' + m.group(2)


def effective(spec):
    """ref_tile.py defaults (recipe >= 3): kind tile -> pin_regs on; reset_ports -> reset_landing 2 stages"""
    rec = int(spec.get('recipe') or 0)
    pr = spec.get('pin_regs')
    if isinstance(pr, dict):
        pin = bool(pr.get('enable'))
    else:
        pin = rec >= 3 and spec.get('kind') == 'tile'
    lat = (pr or {}).get('latency_cycles') if isinstance(pr, dict) else None
    rl = spec.get('reset_landing')
    if isinstance(rl, dict):
        rst = int(rl.get('stages', 2)) if rl.get('enable') else 0
    else:
        rst = 2 if (rec >= 3 and spec.get('reset_ports')) else 0
    return dict(pin_regs=pin, pin_in=(lat or {}).get('input', 1) if pin else 0,
                pin_out=(lat or {}).get('output', 1) if pin else 0, reset_landing_stages=rst)


def wrapper_edges(text):
    """face_land.py wrapper header: 'landed buses: fin +1, i_ctl +1' and 'release +3 ck edges'"""
    if not text:
        return {}, 0
    m = re.search(r'landed buses:\s*([^\n(]*)', text)
    buses = {k: int(v) for k, v in re.findall(r'(\w+)\s*\+(\d+)', m.group(1))} if m else {}
    r = re.search(r'release \+(\d+) ck edges', text)
    return buses, int(r.group(1)) if r else 0


def candidates(master, vm):
    out = []
    for kd in sorted((ROOT / REF).glob('qkd_kvs_*')):
        vdir = kd / 'views' / vm
        sp = kd / 'spec.json'
        if not sp.exists() or not (vdir / f'{vm}.lef').exists():
            continue
        try:
            top = json.loads(sp.read_text()).get('top')
        except ValueError:
            continue
        if top in (master, master + '_fl'):
            out.append((kd.name, vdir))
    return out


def judge(master, vm, kit, vdir, die_rtl, die_text, charge, KSD):
    r = dict(kit=kit, view=str(vdir.relative_to(ROOT)), view_module=vm)
    need = [vdir / f'{vm}.lef', vdir / f'{vm}_tt.lib', vdir / f'{vm}_ff.lib', vdir / 'insertion.json']
    miss = [p.name for p in need if not p.exists()]
    if miss:
        return dict(r, verdict='REFUSE', why=f'view not CLOSED (missing {miss})')
    src, route = view_source(vdir)
    r.update(source_commit=src, route=route)
    if not src:
        hs = json.loads(show('HEAD', f'{REF}/{kit}/spec.json') or '{}')
        e = effective(hs)
        return dict(r, verdict='REFUSE', why=f'view source commit {route} not in this repository (fetch its branch); HEAD kit '
                    f'spec face edges pin_in {e["pin_in"]} / pin_out {e["pin_out"]} vs die 0 / 0')
    spec_txt = show(src, f'{REF}/{kit}/spec.json')
    if not spec_txt:
        return dict(r, verdict='REFUSE', why=f'kit spec absent at the view source {src[:9]}')
    spec = json.loads(spec_txt)
    tfile = [s for s in spec.get('sources', []) if re.search(r'/qkd_kvs_tiles\w*\.sv$', s)]
    if len(tfile) != 1:
        return dict(r, verdict='REFUSE', why=f'kit tile file not unique in the spec sources: {tfile}')
    kmod = module_text(show(src, tfile[0]), master)
    dmod = module_text(die_text, master)
    r.update(kit_tile_file=tfile[0], die_tile_file=die_rtl)
    if kmod is None or dmod is None:
        return dict(r, verdict='REFUSE', why=f'module {master} missing (kit {kmod is not None}, die {dmod is not None})')
    if kmod != dmod:
        import difflib
        d = [x for x in difflib.unified_diff(kmod.split(';'), dmod.split(';'), lineterm='', n=0) if x[:1] in '+-'][2:6]
        return dict(r, verdict='REFUSE', why=f'tile RTL differs: the closed view is {tfile[0]}@{src[:9]} module {master}, '
                    f'the die binds {die_rtl}', diff=[x[:300] for x in d])
    changed = [s for s in spec.get('sources', []) if s not in tfile and blob(src, s) != blob('HEAD', s)]
    if changed:
        return dict(r, verdict='REFUSE', why=f'kit sources changed since the view source {src[:9]}: {changed[:6]}')
    eff = effective(spec)
    wbuses, wrst = ({}, 0)
    if vm.endswith('_fl'):
        wf = [s for s in spec.get('sources', []) if s.startswith('rtl/lib/face_land/')]
        wbuses, wrst = wrapper_edges(show(src, wf[0]) if wf else None)
    got = dict(pin_in=eff['pin_in'], pin_out=eff['pin_out'], land=wbuses)
    want = dict(pin_in=0, pin_out=0, land=charge.get('land', {}))
    rst = wrst + eff['reset_landing_stages']
    r.update(edges=dict(view=got, die_charges=want, reset_release=dict(view=rst, face_land_relay=wrst,
                                                                       reset_landing=eff['reset_landing_stages'],
                                                                       budget=KSD.FACE_LAND_RST_BUDGET)))
    if got != want:
        return dict(r, verdict='REFUSE', why=f'closed view adds edges the die schedule does not charge: view {got} vs die '
                    f'{want} (price them in the die static schedule first, or re-kit without them)')
    if rst > KSD.FACE_LAND_RST_BUDGET:
        return dict(r, verdict='REFUSE', why=f'reset release +{rst} exceeds the region hold budget {KSD.FACE_LAND_RST_BUDGET}')
    return dict(r, verdict='PASS', why='tile RTL identical, sources unchanged, face edges = die charges')


def select():
    KSD = _ksd()
    die_rtl = KSD.RTL_FILE
    die_text = (ROOT / die_rtl).read_text(errors='replace') if (ROOT / die_rtl).exists() else show('HEAD', die_rtl)
    masters = sorted({KSD.KIND_MASTER[t['kind']] for t in KSD.all_tiles().values()})
    sel = set(KSD.FACE_LAND_SEL)
    fl_by_master = {v['master']: k for k, v in KSD.FACE_LAND_TILES.items()}
    tiles, fails = {}, []
    for mst in masters:
        if mst in SKIP:
            tiles[mst] = dict(verdict='SKIP', why='bound by kvsys_prep OT_KV_HROOT_VIEW')
            continue
        fk = fl_by_master.get(mst)
        landed = fk in sel if fk else False
        vm = mst + '_fl' if landed else mst
        charge = {}
        if landed:
            t = KSD.FACE_LAND_TILES[fk]
            charge = dict(land={k: v for k, v in t.items() if k not in ('master', 'kit', 'rst_release')})
        rows = [judge(mst, vm, k, v, die_rtl, die_text, charge, KSD) for k, v in candidates(mst, vm)]
        ok = [x for x in rows if x['verdict'] == 'PASS']
        if ok:
            def when(x):
                o = git('show', '-s', '--format=%ct', x['source_commit'])
                return int(o.strip()) if o else 0
            best = max(ok, key=when)
            tiles[mst] = dict(verdict='BIND', face_land=landed, bind=best, considered=rows)
        else:
            tiles[mst] = dict(verdict='ASSUMED', face_land=landed, why='no closed view passes identity + edges' if rows
                              else f'no closed {vm} view committed', considered=rows)
            if landed:
                fails.append(dict(id='FACE_LAND_VIEW', what=f'{fk}: selected in OT_KV_FACE_LAND but no closed {vm} view passes '
                                  f'(the compiler would charge {charge} on a frame): ' + '; '.join(
                                      f"{x['kit']}: {x['why']}" for x in rows)[:900]))
    for fk in sorted(sel):
        if fk in NOT_TOP and fk != 'astk_rly_296':
            fails.append(dict(id='FACE_LAND_TILE_ABSENT', what=f'{fk}: selected in OT_KV_FACE_LAND but {NOT_TOP[fk]}'))
    return dict(schema=SCHEMA, die_tile_file=die_rtl, face_land_selected=sorted(sel), tiles=tiles,
                bind={m: t['bind']['view'] for m, t in tiles.items() if t['verdict'] == 'BIND'},
                assumed=sorted(m for m, t in tiles.items() if t['verdict'] == 'ASSUMED'),
                fails=fails, status='FAIL' if fails else 'PASS',
                rule='bind a kvs_* tile view only when its closed netlist is the die tile and adds exactly the edges the die '
                     'schedule charges (KV-FACELAND-WIRE)')


def check(record, views, die_bound_v=None):
    """fails: every PASS view bound by bind_views; every face-landed tile bound to its _fl view (and, on the bound
    netlist, instantiated as <master>_fl)"""
    fails = []
    v = (views or {}).get('views', {})
    txt = Path(die_bound_v).read_text(errors='replace') if die_bound_v and Path(die_bound_v).exists() else None
    for f in record.get('fails', []):
        fails.append(dict(f, id='TILE_VIEWS ' + f['id']))
    for mst, t in record.get('tiles', {}).items():
        if t.get('verdict') != 'BIND':
            continue
        b = v.get(mst) or {}
        if not b.get('bound') or b.get('view') != t['bind']['view']:
            fails.append(dict(id='TILE_VIEW_NOT_BOUND', what=f"{mst}: {t['bind']['view']} passed identity + edges but bind_views "
                              f"did not bind it ({b.get('reason') or b.get('view') or 'no record'})"))
            continue
        if t.get('face_land'):
            if not str(b.get('module', '')).endswith('_fl'):
                fails.append(dict(id='FACE_LAND_VIEW_MODULE', what=f"{mst}: bound view module {b.get('module')} is not the _fl view"))
            if txt is not None and not re.search(r'^\s*' + re.escape(mst + '_fl') + r'\b', txt, re.M):
                fails.append(dict(id='FACE_LAND_NETLIST', what=f'{mst}: the bound netlist does not instantiate {mst}_fl '
                                  '(kv_static_die.bindings face-land module)'))
    return fails


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('select')
    s.add_argument('--out', type=Path, required=True)
    c = sub.add_parser('check')
    c.add_argument('--record', type=Path, required=True)
    c.add_argument('--views', type=Path, required=True)
    c.add_argument('--die-bound', type=Path)
    a = ap.parse_args(argv)
    if a.cmd == 'select':
        rec = select()
        a.out.write_text(json.dumps(rec, indent=1) + '\n')
        for m, t in rec['tiles'].items():
            print(f"KV_TILE_VIEW {m}: {t['verdict']} " + (t['bind']['view'] if t['verdict'] == 'BIND' else t.get('why', ''))
                  + ''.join(f"\n    {x['kit']}/{x['view_module']}: {x['verdict']} {x['why'][:300]}" for x in t.get('considered', [])),
                  file=sys.stderr)
        for f in rec['fails']:
            print(f"KV_TILE_VIEWS FAIL {f['id']}: {f['what']}", file=sys.stderr)
        print(' '.join(f'--view {m}={d}' for m, d in sorted(rec['bind'].items())))
        return 3 if rec['fails'] else 0
    rec = json.loads(a.record.read_text())
    f = check(rec, json.loads(a.views.read_text()), a.die_bound)
    print(f"KV_TILE_VIEWS CHECK {'FAIL' if f else 'PASS'}: bound {sorted(rec.get('bind', {}))} assumed {rec.get('assumed')}"
          + ''.join(f"; {x['id']}: {x['what'][:300]}" for x in f))
    return 1 if f else 0


if __name__ == '__main__':
    sys.exit(main())
