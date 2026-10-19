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
# Q-DIEPLAN3 2026-10-16 (Codex 20:18 audit: 25 q3h data hops passed the centroid relay gate with worst-bit lengths
# 422-444 um > the measured 414-um reach): OT_PIN_BIT_REACH_UM = the hard per-BIT reach of every data hop of the FINAL
# (relayed) netlist, judged on the emitted pin rows (len_max = the longest bit of the bundle). Every row over it is
# written to pin_bit_reach.json first; then the build fails (OT_PIN_BIT_REACH_GATE=warn records only). Relay-skip
# smokes judge the unrelayed graph and only report.
_lim = os.environ.get('OT_PIN_BIT_REACH_UM')
if _lim and 'pin_align' in rec and not rec['pin_align'].get('error'):
    _lim = float(_lim)
    _over = sorted(({k: r_.get(k) for k in ('bus', 'cls', 'bits', 'drv', 'drv_port', 'load', 'load_port', 'kind',
                                            'len_mean', 'len_max', 'jog_max', 'at')}
                    for r_ in rows if r_.get('cls') not in ('clock_trunk', 'reset', 'constant')
                    and float(r_.get('len_max') or 0) > _lim), key=lambda r_: -float(r_['len_max']))
    _skip = os.environ.get('OT_RELAY_SKIP') == '1'
    (out / 'pin_bit_reach.json').write_text(json.dumps(dict(limit_um=_lim, relay_skip=_skip, over=len(_over),
                                                            rows=_over), indent=1, default=str) + '\n')
    rec['pin_bit_reach'] = dict(limit_um=_lim, over=len(_over), worst=_over[:5], relay_skip=_skip)
    if _over and not _skip and os.environ.get('OT_PIN_BIT_REACH_GATE', 'fail') != 'warn':
        (out / 'relay_run.json').write_text(json.dumps(rec, indent=1) + '\n')
        raise SystemExit(f'pin bit reach: {len(_over)} data hops over {_lim} um (worst-bit), worst '
                         f"{[(r_['bus'], r_['len_max']) for r_ in _over[:6]]}; see {out / 'pin_bit_reach.json'}")
(out / 'relay_run.json').write_text(json.dumps(rec, indent=1) + '\n')
if '--case' in sys.argv:
    # r9: the chain-ready die case (real case + power abstracts + PDN r5, as `qwen_rom_fulldie_b3r2.py pdn --pdn-rev r5`)
    # of THIS build, so the audited plan and the routed die are one placement
    G.case_pdn(v, m, out / 'case', 63.64, 'r5')
    if m.get('fwd_lanes'):
        # Q-DIE11-RLY 10-18 (OT_SPLIT_FWD_LANES=1): the forwarded half-cycle lanes of this build + the die-STA landing
        # model (LANDING-CONTRACT L5: the lane arrives at the landing's a / ea pins and is captured on the block root
        # ck E edges later: set_multicycle_path -setup E -hold D-1, one E per link at TT and FF)
        fl = m['fwd_lanes']
        (out / 'case' / 'fwd_lanes.json').write_text(json.dumps(fl, indent=1) + '\n')
        sdc = ['# Q-DIE11-RLY forwarded-lane landings (tools/qwen_tp8/relay_data_run.py): ring D %d, one E per link (TT and FF)'
               % fl['D']]
        for r_ in fl['lanes']:
            if r_.get('lane') == 'reset':
                continue          # LANDFIX-SQ forwarded reset lane: no ring, its landing is one single-cycle root capture
            pins = f"{r_['landing']}/a[*]" + ('' if r_['n'] == 1 else f" {r_['landing']}/ea[*]")
            # LANDFIX-SQ 10-18: the MCP is E_sta (the residual edges after the LAST station's launch, as the die STA counts
            # them); dv2f14bn wrote the lane's total E (12-14 on the 26-frame lanes) -> hold edge E - D, FF hold -7.7 ns
            sdc += [f"set_multicycle_path -setup {r_.get('E_sta', r_['E'])} -to [get_pins {{{pins}}}]",
                    f"set_multicycle_path -hold {fl['D'] - 1} -to [get_pins {{{pins}}}]"]
        # NS-CASE 10-18 (ROOT-2115): the landing's K straps k0..k2 are die constants (each on the instance's own
        # tie_hi / tie_lo; lane_latency_audit (b) in the strict bind checks the netlist K == this K): the die STA
        # case-analyses them, as the tile native audit --case k0,k1,k2 excludes them
        sdc += ['set ::ot_case_n 0; set ::ot_case_miss 0',
                'proc ot_case {v p} { set q [get_pins -quiet $p]; if {[llength $q]} { set_case_analysis $v $q; '
                'incr ::ot_case_n } else { incr ::ot_case_miss } }']
        n_case = 0
        for r_ in fl['lanes']:
            if r_.get('lane') == 'reset' or r_.get('K') is None:
                continue
            for i in range(3):
                sdc.append(f"ot_case {(int(r_['K']) >> i) & 1} {{{r_['landing']}/k{i}}}"); n_case += 1
        sdc.append('puts "OT_CASE_STRAPS set $::ot_case_n missing $::ot_case_miss of %d"' % n_case)
        (out / 'case' / 'landing.sdc').write_text('\n'.join(sdc) + '\n')
        if m.get('coll_lane_latency'):
            # Q-COLLCAL 10-18: the SerDes lane cycles of THIS build and the collective calendar that absorbs them
            (out / 'case' / 'coll_lane_latency.json').write_text(json.dumps(m['coll_lane_latency'], indent=1) + '\n')
            rec['coll_lane_latency'] = {k_: m['coll_lane_latency'][k_] for k_ in ('LX', 'verdict', 'fails')}
    if m.get('die_master_params'):
        # Q-COLLCAL 10-18: the elaboration parameters of the die's masters (tools/die_port_bind.py reads DIE_V.params.json:
        # the strict bind elaborates io_collective with the GEN's LX0..2); merged over any sidecar the writer left
        pj = out / 'case' / 'die.v.params.json'
        cur = json.loads(pj.read_text()) if pj.exists() else dict(schema='opentallas.die_params.v1', netlist='die.v', masters={})
        for mst_, prm_ in m['die_master_params'].items():
            cur.setdefault('masters', {}).setdefault(mst_, {}).update(prm_)
        pj.write_text(json.dumps(cur, indent=1, sort_keys=True) + '\n')
        rec['die_master_params'] = m['die_master_params']
        (out / 'relay_run.json').write_text(json.dumps(rec, indent=1) + '\n')
        rec['fwd_lanes'] = {k_: fl[k_] for k_ in ('lanes', 'stations', 'landings', 'masters', 'plain_relays_left',
                                                  'reclassed_reset_hops')} | dict(lanes=len(fl['lanes']), skipped=len(fl['skipped']))
        (out / 'relay_run.json').write_text(json.dumps(rec, indent=1) + '\n')
    # QW-DIEFIX 10-19 (QW-XHEAD XT1: the GEN bound NO tile ROM content -> die-netlist sims read empty code ROMs): every
    # qfd_c_b16_dv tile gets its sim-only ROM_TILE (= tile_id strap) in case/rom_bind.vh + case/rom_bind.json; the
    # structural audit always runs and fails the GEN closed; OT_QWEN_ROM_MASKS=<code-mask manifest> (tools/qwen_code_rom/
    # build.py) adds the per-macro content check (every macro has an existing, non-empty, sha256-matching mask file)
    _dv = out / 'case' / 'die.v'
    if _dv.exists() and 'qfd_c_b16_dv ' in _dv.read_text():
        from qwen_split import die_rom_bind as _RB2
        _mk = os.environ.get('OT_QWEN_ROM_MASKS', '').strip()
        _rbv, _rbd, _rbh = _RB2.run(_dv, Path.cwd(), Path(_mk) if _mk else None,
                                    int(os.environ['OT_QWEN_ROM_RANK']) if os.environ.get('OT_QWEN_ROM_RANK') else None,
                                    '`OT_ROM_BIND_TOP.', [], 0)
        (out / 'case' / 'rom_bind.vh').write_text(_rbh)
        (out / 'case' / 'rom_bind.json').write_text(json.dumps(_rbd, indent=1) + '\n')
        rec['rom_bind'] = {k_: _rbd['audit'][k_] for k_ in ('verdict', 'fails', 'clusters', 'tiles', 'macros')}
        (out / 'relay_run.json').write_text(json.dumps(rec, indent=1) + '\n')
        print(f"ROM_BIND_AUDIT {_rbv} tiles={_rbd['audit']['tiles']} masks="
              f"{'none' if not _mk else _rbd['audit']['masks'].get('files_ok')}", flush=True)
        if _rbv != 'PASS':
            raise SystemExit(f"ROM_BIND_AUDIT FAIL: {_rbd['audit']['fails'][:5]} (case/rom_bind.json)")
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
    # VIS-ROM D-QC-02 (Q-COMPUTE-DIE 10-16): generated frame abstracts wrote every signal pin DIRECTION INOUT (xcol rst_n,
    # every unclosed parent); give each frame pin its die-bus direction (driver first, as die_sta_libs) so GRT/STA and the
    # reset-tree audit see real inputs/outputs. Pins without a die bus stay INOUT (unconnected frame pins).
    from qwen_tp8.frame_pin_directions import apply_frame_directions
    _elef = out / 'case' / 'elements.lef'
    if _elef.exists():
        _text, _audit = apply_frame_directions(_elef.read_text(), dirs)
        _elef.write_text(_text)
        rec['frame_pin_directions_fixed'] = _audit['fixed']
        rec['frame_pin_directions_audit'] = _audit
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
    if m.get('static_link_bind'):
        from qwen_split.static_link_bind import validate_case_masters
        validate_case_masters(M, m)
    if m.get('res_train_bind'):
        from qwen_split.res_train_bind import validate_case_masters as validate_res_train
        validate_res_train(M, m)
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
        # Q-DIE11-RLY: the forwarded-lane frames (qfd_rlyh*/qfd_landh*) DO get assigned pin files (their kits consume them)
        if re.match(r'^(q[fk]d_rly(?!h0?_|r[0l]?_)|qfd_rst_rep)', name) or not any(getattr(i, 'master', '') == name for i in m['insts']):
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
