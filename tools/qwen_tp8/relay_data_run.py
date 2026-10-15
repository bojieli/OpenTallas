#!/usr/bin/env python3
"""Build the tp8b Qwen die once and record what the data-relay plan needs (relay-data 2026-10-13):
relay stages per bus, the generator's own pin-to-pin reach gate, the fine cut scan (results/arch/qwen_tp8_1012/cuts.py,
CAP_MODE v3: bits per cut vs usable tracks, relay pin faces included as hop endpoints) and relay_token_cost.

usage (repo root): python3 tools/qwen_tp8/relay_data_run.py OUTDIR   -> OUTDIR/relay_run.json, OUTDIR/rom_tp8b.json
Set OT_RELAY_DUMP=FILE for the allocator's per-chain dump, OT_RELAY_GATE=warn to record misses instead of raising."""
import json, os, sys, time
from pathlib import Path
sys.path.insert(0, 'tools'); sys.path.insert(0, 'results/arch/qwen_tp8_1012')
import die_top_lint as D, cuts as C
import qwen_rom_fulldie_b3r2 as G

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True); t = time.time()
D.QWEN_RECIPE = 'tp8b'; D._QW.clear(); D.QSRC = None
v, m = D.load_qwen()[:2]
ins = [dict(n=i.name, m=getattr(i, 'master', ''), x=i.x, y=i.y, w=i.w, h=i.h) for i in m['insts']]
json.dump(dict(insts=ins, buses=[(b, c, bits, [e[0] for e in eps]) for b, c, bits, eps in m['buses']]), open(out / 'rom_tp8b.json', 'w'))
C.CAP_MODE = 'v3'
C.CLUSTER_PLAN = getattr(v, 'CLUSTER_PLAN', 'A')     # r8: 'M6' = die M6 over the M5-capped tiles (horizontal buses)
A = C.Net(str(out / 'rom_tp8b.json'))
fine = [dict(ax=r['ax'], pos=float(r['pos']), win=[float(q) for q in r['win']] if isinstance(r['win'], (list, tuple)) else r['win'],
             bits=float(r['bits']), usable=float(r['usable']), util=float(r['util']), fam={str(k): float(x) for k, x in r['fam'].items()})
        for r in A.fine(top=40)]
try:
    cost = (dict(qualified=False,cycles_per_ar_token=None,
                 reason='OT_RELAY_SKIP: no placed relay stages; no performance evidence')
            if (m.get('r21_relays') or {}).get('skipped') else G.relay_token_cost(v,m))
except Exception as e:   # noqa: BLE001
    import traceback
    cost = dict(error=repr(e), trace=traceback.format_exc()[-1500:])
r = dict(m.get('r21_relays') or {})
rec = dict(schema='opentallas.qwen-tp8.relay-data-run.v1', recipe='tp8b' + ('+split_compute' if os.environ.get('OT_TP8_SPLIT') else ''), split_compute=m.get('split_compute'), die=m['die'], build_s=round(time.time() - t),
           relays={k: r.get(k) for k in ('pitch_um', 'max_um', 'relays', 'masters', 'classes', 'clock_nets_missing', 'repaired',
                                         'unrepaired', 'cut_over', 'off_plan', 'rip_up', 'gap_tier', 'wall_avoid', 'retry', 'jog_fix', 'pair_check', 'relay_flop_bits', 'relay_area_mm2', 'reach_um',
                                         'max_pin_to_pin_um', 'over_reach')},
           tp8b_kv={k: (m.get('tp8b_kv') or {}).get(k) for k in ('kept_relays', 'torn_chains', 'pin_moves')},
           stage_of=m.get('r21_stage_of'), masters=sorted({i['m'] for i in ins if '_rly' in i['m']}),
           cuts=dict(tool='results/arch/qwen_tp8_1012/cuts.py', cap_mode='v3', cluster_plan=C.CLUSTER_PLAN, rule='bits / usable tracks <= 0.60',
                     worst=max((f['util'] for f in fine), default=None), fine_top=fine), relay_token_cost=cost)
# r8: the reset tree of the same build (as reset_tree_run.py) and, with --case, the die case for pinreg_audit.py --case
pos = G._pin_pos(v, m)
rst = []
for bid, cl, bits, eps in m['buses']:
    if len(eps) < 2 or not (cl == 'reset' or bid.startswith(('rst', 'arst')) or '_rst_' in bid):
        continue
    rst.append((round(G._hp([pos(*e) for e in eps]), 1), bid, cl, len(eps)))
rst.sort(reverse=True)
rec['reset'] = dict(reset_tree=m.get('tp8_reset_tree'), reset_named_nets=len(rst),
                    reset_named_over_500=[q for q in rst if q[0] > 500.0], reset_named_worst=rst[:12])
rec['instances'] = len(m['insts'])
if m.get('native_static_io_contract'):
    (out / 'native_static_io_contract.json').write_text(json.dumps(m['native_static_io_contract'], indent=1) + '\n')
    rec['native_static_io_contract'] = m['native_static_io_contract']
rec['tree_host_manifest'] = m.get('tree_host_manifest')
if m.get('tree_host_manifest'):
    (out / 'tree_host_manifest.json').write_text(json.dumps(m['tree_host_manifest'], indent=1) + '\n')
rec['inline_pads'] = m.get('tp8_inline_pads')     # split compute C5: node-leg / block-word arrival pads
rec['tp8_tree_pads'] = m.get('tp8_tree_pads')
rec['tp8b_v5'] = {k: (m.get('tp8b_v5') or {}).get(k) for k in ('views', 'pin_align', 'pin_align_die', 'io', 'torn_kv_chains', 'torn_kv_chains_over_reach', 'n_overlaps')}
# r9 (coordinator 2026-10-13): pin alignment of every die bundle on the generator's own pin rectangles (0 FAIL to pass)
try:
    import gzip
    sys.path.insert(0, 'tools/qwen_tp8')
    import pin_align_run as PAR
    pa, rows, pa_line = PAR.record(v, m)
    (out / 'pin_align.json').write_text(json.dumps(pa, indent=1, default=str) + '\n')
    with gzip.open(out / 'pin_align_rows.json.gz', 'wt') as fh:
        json.dump([{k: q for k, q in r_.items() if k != 'why'} for r_ in rows], fh, default=str)
    rec['pin_align'] = dict(verdict=pa['verdict'], bundles=pa['bundles'], by_verdict=pa['by_verdict'], by_kind=pa['by_kind'],
                            jog_over_warn=pa['jog_over_warn'], order_not_preserved=pa['order_not_preserved'], line=pa_line)
except Exception as e:   # noqa: BLE001
    import traceback
    rec['pin_align'] = dict(error=repr(e), trace=traceback.format_exc()[-1200:])
(out / 'relay_run.json').write_text(json.dumps(rec, indent=1) + '\n')
if '--case' in sys.argv:
    # r9: the chain-ready die case (real case + power abstracts + PDN r5, as `qwen_rom_fulldie_b3r2.py pdn --pdn-rev r5`)
    # of THIS build, so the audited plan and the routed die are one placement
    G.case_pdn(v, m, out / 'case', 63.64, 'r5')
    # r10: pin directions of every die master as the bus list has them (driver first), for the placeholder Liberty
    # views of the die STA (tools/qwen_tp8/die_sta_libs.py); a split bundle's 1-b _cr / _r part runs against its word
    byi = {i.name: i for i in m['insts']}
    split = m.get('port_split') or {}
    join = m.get('port_join') or {}

    def real_ports(master, port):
        if port in join.get(master, {}):
            return [join[master][port][0]]
        return [pn for pn, nb in split.get(master, {}).get(port, ())] or [port]

    dirs = {}
    for bid, cl, bits, eps in m['buses']:
        for k, (inst, port) in enumerate(eps):
            mst, port = getattr(byi[inst], 'master', ''), port.lstrip('*')
            d = 'output' if k == 0 else 'input'
            dirs.setdefault(mst, {}).setdefault(port, d)
            if port in join.get(mst, {}):
                dirs[mst].setdefault(join[mst][port][0], d)
            for sub, nb in (split.get(mst, {}).get(port) or []):
                rev = nb == 1 and sub.endswith(('_cr', '_r'))
                dirs[mst].setdefault(sub, ('input' if d == 'output' else 'output') if rev else d)
    (out / 'case' / 'port_dirs.json').write_text(json.dumps(dirs, indent=0, sort_keys=True) + '\n')
    if m.get('native_static_io_bind'):
        from qwen_split.clock_contract import build as source_clock_contract
        (out / 'case' / 'clock_contract.json').write_text(
            json.dumps(source_clock_contract(m, Path.cwd()), indent=1) + '\n')
    # r10 (OWNER 2026-10-13 18:22, top-down pin assignment): one ASSIGNED pin file per die master that is not a relay /
    # reset repeater, in the form the tile kits consume (ref_tile spec "pins" = ports per face in order along the face,
    # "pin_ranges" = {port: [lo_um, hi_um]} from the face's W / S end, + layer, bits, bit 0 end, direction, die peer).
    # Positions are the generator's own pin rectangles (the pins the relay plan, the cut scan and pin_align judged).
    import re
    M = v.masters(m, 1)
    pw = v.port_widths(m, 1)
    peer = {}
    for bid, cl, bits, eps in m['buses']:
        if cl in ('clock_trunk', 'reset') or len(eps) != 2:
            continue
        (ia, pa), (ib, pb) = eps
        ma, mb = getattr(byi[ia], 'master', ''), getattr(byi[ib], 'master', '')
        for mn, p, other, op in ((ma, pa, mb, pb), (mb, pb, ma, pa)):
            for pn in real_ports(mn, p.lstrip('*')):
                target = '|'.join(f'{other}.{q}' for q in real_ports(other, op.lstrip('*')))
                key = (mn, pn)
                if key in peer and target not in peer[key].split(';'):
                    peer[key] += ';' + target
                else:
                    peer.setdefault(key, target)
    pdir = out / 'pins'
    pdir.mkdir(exist_ok=True)
    index = {}
    # Pin assignments use the same exact RTL names emitted by the case, including
    # cbuf/crom split bundles and the three-source joined head ti bus.
    emit_saved = getattr(v, 'EMIT_SPLIT', False)
    v.EMIT_SPLIT = True
    for name, mst in sorted(M.items()):
        if re.match(r'^(q[fk]d_rly|qfd_rst_rep)', name) or not any(getattr(i, 'master', '') == name for i in m['insts']):
            continue
        g = {}
        rects_ = list(v.pin_rects(mst, 1, {q: pw.get((name, q), 0) for q in mst.order}))
        # v1.3 (compute lead r4): a published pin file must be overlap-free (elements r11: c16s tile / slab files had
        # coincident clock entries and duplicated groups); count same-layer overlapping pin rectangles
        ov_, byL_ = 0, {}
        for nm_, L_, r_ in rects_:
            byL_.setdefault(L_, []).append(r_)
        for L_, lst_ in byL_.items():
            lst_.sort()
            for i_ in range(len(lst_)):
                a_ = lst_[i_]
                for b_ in lst_[i_ + 1:]:
                    if b_[0] >= a_[2]:
                        break
                    if b_[1] < a_[3] and b_[3] > a_[1]:
                        ov_ += 1
        for nm, layer, r in rects_:
            base, _, idx = nm.partition('[')
            cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
            d = dict(W=cx, E=mst.w - cx, S=cy, N=mst.h - cy)
            f = min(d, key=d.get)
            q = g.setdefault(base, dict(face=f, layer=layer, pos=[], xy=[], interior=d[f] > 1.0))
            q['xy'].append((int(idx[:-1]) if idx else 0, round(cx,4), round(cy,4)))
            q['pos'].append((int(idx[:-1]) if idx else 0, round(cy if f in 'EW' else cx, 4)))
        faces, rng, ports = {}, {}, {}
        for base, q in g.items():
            q['pos'].sort()
            lo, hi = min(x for _, x in q['pos']), max(x for _, x in q['pos'])
            ports[base] = dict(face=q['face'], layer=q['layer'], bits=len(q['pos']), range_um=[lo, hi],
                               bit0_at='lo' if q['pos'][0][1] <= q['pos'][-1][1] else 'hi',
                               direction=dirs.get(name, {}).get(base, 'input'), peer=peer.get((name, base)),
                               **({'interior': True, 'positions_xy_um': [[x,y] for _,x,y in sorted(q['xy'])]} if q['interior'] else {}))
            if not q['interior']:
                faces.setdefault(q['face'], []).append((lo, base))
                rng[base] = [lo, hi]
        rec_ = dict(schema='opentallas.qwen-tp8.assigned-pins.v1', master=name, outline=dict(w=mst.w, h=mst.h),
                    instances=sum(1 for i in m['insts'] if getattr(i, 'master', '') == name),
                    pins={f: [b_ for _, b_ in sorted(l)] for f, l in sorted(faces.items())}, pin_ranges=rng, ports=ports,
                    overlapping_pin_pairs=ov_,
                    note='assigned by the die generator (tools/qwen_tp8/relay_data_run.py --case); a real-view master '
                         'lists its view pins')
        (pdir / f'{name}.json').write_text(json.dumps(rec_, indent=1) + '\n')
        index[name] = dict(instances=rec_['instances'], ports=len(ports), bits=sum(q_['bits'] for q_ in ports.values()),
                           overlapping_pin_pairs=ov_)
        if ov_:
            print(f'PIN_OVERLAP FAIL {name}: {ov_} overlapping pin pairs', flush=True)
    v.EMIT_SPLIT = emit_saved
    (pdir / 'INDEX.json').write_text(json.dumps(index, indent=1) + '\n')
r = rec['relays']  # pin rectangle iteration above uses its own local r value
print(json.dumps(dict(relays=r.get('relays'), max_pin_to_pin_um=r.get('max_pin_to_pin_um'), over_reach=len(r.get('over_reach') or []),
                      unrepaired=len(r.get('unrepaired') or []), worst_cut=rec['cuts']['worst'], build_s=rec['build_s'],
                      reset_over_500=len(rec['reset']['reset_named_over_500']), instances=rec['instances'],
                      pin_align=rec['pin_align'].get('by_verdict') or rec['pin_align'].get('error'),
                      cycles_per_ar_token=cost.get('cycles_per_ar_token'), stages=cost.get('stages_r21'))))
