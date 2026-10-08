#!/usr/bin/env python3
"""Refresh an existing S81 die STA kit with newer views WITHOUT regenerating its netlist (CLAUDE S81-ASSEMBLE 2026-10-08).

die_sta.py kit rebuilds die.v from the generator; for m221pq_r3 that no longer reproduces the routed case's netlist
(fe09924a8 generator, same options: different relay / station masters), so the GRT SPEF would not match.  This keeps
the kit's die.v / clocks / latency and swaps views in place:
  * every lib path re-rooted to --views-root;
  * masters whose TT lib was an SS stand-in ("SS as TT") take the view's _tt.lib when it now exists;
  * S81-PH slabs with an assembled view (physical/s81_ph_views/assembled/<slab>) take it: the slab cell leaves the
    interim libs, the assembled lib joins libs_<corner>.txt, and the routed insertion the kit had ADDED to the slab's
    clock pins (interim convention) is subtracted again (the tile ETM arcs carry the tiles' insertion);
  * kit.json / index.json updated (schema of die_sta.py --index-out).

  * --rebalance (s81-die-timing 2026-10-08): rewrite the pin latencies to the balanced die tree of die_sta.py
    (balance_latency: every flop at its planned arrival; closed / assembled views' in-arc insertion subtracted, the
    interim routed-insertion add of sta_v2/v3 undone) and the die hold uncertainty 75 -> 50 (rule H1).

  kit_swap_views.py --kit OLD_KIT --views-root SRC --out NEW_KIT [--index-out index.json] [--rebalance --measured J]
"""
import argparse
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path

CORNERS = dict(ss=0, ff=1, tt=2)          # insertion_added_ps order in kit.json is [ss, ff, tt]


def drop_cells(lib, cells):
    out, skip, depth = [], False, 0
    for ln in lib.splitlines(keepends=True):
        m = re.match(r'^ cell \((\w+)\) \{', ln)
        if m and m.group(1) in cells:
            skip, depth = True, 0
        if skip:
            depth += ln.count('{') - ln.count('}')
            if depth <= 0 and '}' in ln:
                skip = False
            continue
        out.append(ln)
    return ''.join(out)


def rebalance(a, K, vr):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from die_sta import balance_latency, measured_insertion, closed_libs
    pm = {m.group(2).lstrip('\\'): m.group(1) for m in
          re.finditer(r'^\s*(\w+)\s+(\\?\S+)\s*\(', (a.out / 'die.v').read_text(), re.M)}
    rows, lat = {}, {}
    for c, ci in CORNERS.items():
        for ln in (a.out / f'latency_{c}.tcl').read_text().splitlines():
            m = re.match(r'set_clock_latency ([-\d.]+) \[get_pins -quiet \{(\S+) ', ln)
            if m:
                k_ = m.group(2)
                rows[k_] = ln
                lat.setdefault(k_, [0.0, 0.0, 0.0])[ci] = float(m.group(1))
    pin_master = {k_: pm[k_.split('/')[0]] for k_ in lat}
    for k_, v in lat.items():         # undo the interim routed-insertion add (planned arrival back)
        add = K['masters'].get(pin_master[k_], {}).get('insertion_added_ps')
        if add:
            lat[k_] = [v[i] - add[i] for i in range(3)]
    mi = measured_insertion(a.measured or vr / 'results/rtl/budgets_20261006/measured_insertion.json')
    libs = dict(ss={m_: (vr / r['libs']['ss'].split(' ')[0], r['view']) for m_, r in K['masters'].items()
                    if r.get('libs', {}).get('ss')})
    K['routed_insertion'] = dict(K.get('routed_insertion') or {}, **balance_latency(lat, pin_master, K['masters'], mi, libs))
    for c, ci in CORNERS.items():
        (a.out / f'latency_{c}.tcl').write_text(''.join(
            f'set_clock_latency {v[ci]:.1f} [get_pins -quiet {{{k_} {k_}[0]}}]\n' for k_, v in sorted(lat.items())))
        t = (a.out / f'sta_{c}.tcl').read_text().replace('set_clock_uncertainty -hold 75.0 ', 'set_clock_uncertainty -hold 50.0 ')
        (a.out / f'sta_{c}.tcl').write_text(t)
    K['hold_uncertainty_ps'] = 50.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--kit', type=Path, required=True)
    ap.add_argument('--views-root', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--index-out', type=Path)
    ap.add_argument('--rebalance', action='store_true')
    ap.add_argument('--measured', type=Path, help='measured_insertion.json (default: <views-root>/results/rtl/'
                    'budgets_20261006/measured_insertion.json)')
    a = ap.parse_args()
    if a.out.exists():
        shutil.rmtree(a.out)
    shutil.copytree(a.kit, a.out)
    K = json.loads((a.kit / 'kit.json').read_text())
    old_root = K['views_root'].rstrip('/')
    vr = a.views_root.resolve()
    asm = {d.name: d for d in (vr / 'physical/s81_ph_views/assembled').iterdir() if (d / 'assembled.json').exists()}
    swapped = [m for m in asm if m in K['masters']]
    # instance names of the swapped slabs (die.v: "<master> <inst> (")
    inst = defaultdict(list)
    pat = re.compile(r'^\s*(' + '|'.join(map(re.escape, swapped)) + r')\s+(\S+)\s*\(', re.M) if swapped else None
    if pat:
        for m in pat.finditer((a.kit / 'die.v').read_text()):
            inst[m.group(1)].append(m.group(2).lstrip('\\'))
    tt_fixed = []
    for c, ci in CORNERS.items():
        libs = []
        for ln in (a.kit / f'libs_{c}.txt').read_text().split():
            if ln.startswith(old_root):
                ln = str(vr) + ln[len(old_root):]
            libs.append(ln)
        if c == 'tt':
            for mst, r in K['masters'].items():
                t = r.get('libs', {}).get('tt', '')
                if t.endswith('(SS as TT)'):
                    ss = vr / t.split(' ')[0]
                    tt = ss.with_name(ss.name.replace('_ss.lib', '_tt.lib'))
                    if tt.exists():
                        libs = [str(tt) if x == str(ss) else x for x in libs]
                        r['libs']['tt'] = str(tt.relative_to(vr))
                        tt_fixed.append(mst)
        for mst in swapped:
            libs.insert(-1, str(asm[mst] / f'{mst}_{c}.lib'))
        libs = list(dict.fromkeys(libs))
        (a.out / f'libs_{c}.txt').write_text('\n'.join(libs) + '\n')
        (a.out / f'interim_{c}.lib').write_text(drop_cells((a.kit / f'interim_{c}.lib').read_text(), set(swapped)))
        lat = (a.kit / f'latency_{c}.tcl')
        if lat.exists():
            L = []
            for ln in lat.read_text().splitlines():
                m = re.match(r'set_clock_latency ([-\d.]+) \[get_pins -quiet \{(\S+)/', ln)
                if m:
                    for mst in swapped:
                        add = K['masters'][mst].get('insertion_added_ps')
                        if add and m.group(2) in inst[mst]:
                            ln = ln.replace(f'set_clock_latency {m.group(1)} ', f'set_clock_latency {float(m.group(1)) - add[ci]:.1f} ', 1)
                L.append(ln)
            (a.out / f'latency_{c}.tcl').write_text('\n'.join(L) + '\n')
    for mst in swapped:
        aj = json.loads((asm[mst] / 'assembled.json').read_text())
        K['masters'][mst] = dict(view='assembled', libs={c: str((asm[mst] / f'{mst}_{c}.lib').relative_to(vr)) for c in CORNERS},
                                 tiles=K['masters'][mst].get('tiles'), instances=inst[mst],
                                 insertion_removed_ps=K['masters'][mst].get('insertion_added_ps'),
                                 glue_worst_ps=aj['glue_worst_ps'], tiles_ss_as_tt=aj['corners']['tt']['tiles_ss_as_tt'])
    if a.rebalance:
        rebalance(a, K, vr)
    n = defaultdict(int)
    for v in K['masters'].values():
        n[v['view']] += 1
    K['counts'] = dict(n)
    K['views_root'] = str(vr)
    K['swap'] = dict(from_kit=str(a.kit), assembled=swapped, tt_extracted=tt_fixed)
    (a.out / 'kit.json').write_text(json.dumps(K, indent=1) + '\n')
    (a.out / 'src_root').write_text(str(vr) + '\n')
    if a.index_out:
        idx = json.loads((a.kit / 'index.json').read_text()) if (a.kit / 'index.json').exists() else {}
        cnt = {k: v.get('instances', 1) for k, v in idx.get('masters', {}).items()}
        idx.update(counts=dict(n), masters={k: dict(v, instances=cnt.get(k, 1) if not isinstance(v.get('instances'), list)
                                                     else len(v['instances'])) for k, v in sorted(K['masters'].items())},
                   swap=K['swap'], views_root=str(vr))
        idx['instances'] = {k: sum(m['instances'] for m in idx['masters'].values() if m['view'] == k) for k in n}
        a.index_out.parent.mkdir(parents=True, exist_ok=True)
        a.index_out.write_text(json.dumps(idx, indent=1) + '\n')
    print(json.dumps(dict(counts=dict(n), assembled={m: inst[m] for m in swapped}, tt_extracted=tt_fixed)))


if __name__ == '__main__':
    main()
