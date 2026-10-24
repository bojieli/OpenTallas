#!/usr/bin/env python3
"""CORE-HBM-SPLIT (2026-10-23): one RTL top per FUNCTIONAL split-piece type, canonical port names, replicas merged.

For every member-set piece (whole module instances of an over-cap master) the top is generated from the as-built
hierarchical netlist of its master (the netlists the HBM-P5 ports_cut.json was cut from): split_conn.analyse gives
every member-pin bit (boundary / member<->member / constant / open); all replicas of a type are checked to have the
same structure (signature equal except strap constants, which become strap inputs); the wrapper instantiates the RTL
modules (the PIN_REG / twin variants the split.json 'rtl' names) and wires them exactly as the master does.

    python3 build_split_tops.py --net DIR --only sfu_lane,...   (writes rtl/hbm_accel/cores_split/<master>/<top>.sv
                                                                 and <scratch>/split_tops.json: ports + cut maps)
"""
import argparse, json, os, re, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import split_conn as sc                                           # noqa: E402
import netcut, gen_core_ports as g                                # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))


def sfu_lane(n, m):
    sfu = g.find_paths(n, m, r'ot_su12_sfu'); maps = g.find_paths(n, m, r'sfu_lane_map')
    out = {}
    for k in range(16):
        inc = [p for p in sfu + maps if f'g_lane[{k}].' in p]
        out[f'{m}__lane{k}'] = (inc, [])
    return out


def tkm_tile(n, m):
    tiles = g.find_paths(n, m, r'tkm_tile_e86')
    rx = re.compile(r'g_tiles\[(\d+)\]')
    return {m + '__tile' + rx.search(tp).group(1): ([tp], []) for tp in tiles}


def bankq_lanes(n, m):
    lg = sorted(g.find_paths(n, m, r'hcp_lanes'), key=lambda p: int(re.search(r'\[(\d+)\]\D*$', p).group(1)))
    return {f'{m}__lanes0_2': (lg[0:3], []), f'{m}__lanes3_5': (lg[3:6], [])}


def score_tail(n, m):
    out = {}
    for tp in g.find_paths(n, m, r'idx_tail_native'):
        out[m + '__tail' + re.search(r'ge\[(\d+)\]', tp).group(1)] = ([tp], [])
    return out


PIECES = {
    'sfu_lane': dict(
        master='ot_hgi_sfu_core_split3', top='ot_hgi_sfu_split3_lane_core', pieces=sfu_lane,
        rtl={'u_map': ('ot_hgi_sfu_lane_map', ''),
             'u_sfu': ('ot_su12_sfu_sp2', '#(.GSH(1),.KIMM(1),.DENR(1),.DRING(3))')},
        straps=[('u_map', 'lane_j')],
        src='rtl/hbm_accel/generic/peers/sfu_sp2/ot_hgi_sfu_arithmetic_grid_sp2.sv g_lane[j] (g_mono u_map + u_sfu; '
            'the twin _sp2 lane = RDX 2, store-side pin registers priced by HBM-P5)'),
    'tkm_tile': dict(
        master='ot_hgi_coll_tkm_m_tp192', top='ot_hgi_coll_tkm_tp192_tile_core', pieces=tkm_tile,
        rtl={'u_tile': ('ot_hgi_coll_tkm_tile_e86', '')},
        straps=[('u_tile', 'tid')],
        src='rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm_static_p.sv g_tiles[t].e86.u_tile (tile unchanged by '
            'PIPE 1; clk_r0..3 = tile_clk)'),
    'score_tail': dict(
        master='ot_hbm_idx_score_quarter_static', top='ot_hbm_idx_tail_native', pieces=score_tail,
        rtl=None, straps=[],
        src='rtl/hbm_accel/index/quad_1017/ot_hbm_idx_score_quarter_static_h.sv ge[e] tail (ot_hbm_idx_tail_native, '
            'verbatim in the _h twin)'),
    'bankq_lanes3': dict(
        master='ot_hbm_hc_bankq_static', top='ot_hbm_hc_bankq_lanes3_core', pieces=bankq_lanes,
        masters=['ot_hbm_hc_bankq_static', 'ot_hbm_hc_bankq_ft_static', 'ot_hbm_hc_bankq0_static',
                 'ot_hbm_hc_bankq_term_static'],
        rtl={'u_lg0': ('ot_hdc_v41x_hcp_lanes', ''), 'u_lg1': ('ot_hdc_v41x_hcp_lanes', ''),
             'u_lg2': ('ot_hdc_v41x_hcp_lanes', '')},
        straps=[('u_lg0', 'fst'), ('u_lg1', 'fst'), ('u_lg2', 'fst')],
        src='rtl/hdc/v41x/ot_hdc_v41x_hcp.sv ot_hdc_v41x_hcp_stage g_grp[gg].u_lg x3 (hard child, no parameter '
            'overrides in every bankq variant; bankq0 = first stage: fst 1, s_i tied 0 at the parent)'),
}


# Remainder pieces (a module minus a member): hand-placed tops from gen_split_rtl.py, explicit cut -> canonical map.
MANUAL = {
    'pgslice_side_softplus': dict(
        master='ot_hbm_su_static_pgslice_lg__pv0', top='ot_hbm_su_side_softplus_core',
        file='rtl/hbm_accel/cores_split/ot_hbm_su_static_pgslice_lg/ot_hbm_su_side_softplus_core.sv',
        pieces={'ot_hbm_su_static_pgslice_lg__side_softplus': {
            'clk_side': 'clk', 'rst_n': 'rst_n', 'u_sp_v': 'v', 'u_sp_x': 'x', 'u_sp_fault': 'fault', 'u_sp_r': 'r'}},
        src='u_side.u_sp of ot_hbm_su_static_side_s (HBM-P5-RTLB twin): ot_hbm_su_static_side_softplus_s #(LM 3, LA 3, FREG 1)'),
    'pgslice_side_rest': dict(
        master='ot_hbm_su_static_pgslice_lg__pv0', top='ot_hbm_su_side_rest_core',
        file='rtl/hbm_accel/cores_split/ot_hbm_su_static_pgslice_lg/ot_hbm_su_side_rest_core.sv',
        pieces={'ot_hbm_su_static_pgslice_lg__side_rest': {
            'clk_side': 'clk_r', 'rst_n': 'rst_n', 'x_u_u_slice_g_lane_0_g_plain_u_lane_ci_sfu': 'fn',
            'x_u_u_slice_g_lane_0_g_plain_u_lane_cs_sfu': 'fn_out', 'x_u_u_slice_g_lane_0_g_plain_u_lane_side_v': 'v',
            'x_u_u_slice_g_lane_0_g_plain_u_lane_side_x': 'x', 'x_u_u_slice_g_side_pipe_u_side_u_sp_fault': 'sp_fault',
            'x_u_u_slice_g_side_pipe_u_side_u_sp_r': 'sp_r', 'glue': 'fault',
            'x_u_u_slice_g_lane_0_g_plain_u_lane_side_y': 'y', 'x_u_u_slice_g_side_pipe_u_side_u_sp_v': 'sp_v'}},
        src='ot_hbm_su_static_side_s (HBM-P5-RTLB twin) minus u_sp, generated by gen_split_rtl.py'),
    'score_hcol_h0': dict(
        master='ot_hbm_idx_score_quarter_static', top='ot_hidx_score_hcol', params={'HALF': 0, 'MUT': 0},
        file='rtl/hdc/v41x/ot_hbm_idx_chunk_rt_h.sv', match=r'^ot_hbm_idx_score_quarter_static__r\dc\d_k\dh0$',
        src='HBM-P4-SPLIT twin ot_hidx_score_hcol #(HALF 0) (rtl/hdc/v41x/ot_hbm_idx_chunk_rt_h.sv); the cut port list IS '
            'the twin port list.  HALF changes the per-head delay depth and the seed head, so h0 and h1 are 2 types'),
    'score_hcol_h1': dict(
        master='ot_hbm_idx_score_quarter_static', top='ot_hidx_score_hcol', params={'HALF': 1, 'MUT': 0},
        file='rtl/hdc/v41x/ot_hbm_idx_chunk_rt_h.sv', match=r'^ot_hbm_idx_score_quarter_static__r\dc\d_k\dh1$',
        src='HBM-P4-SPLIT twin ot_hidx_score_hcol #(HALF 1) (rtl/hdc/v41x/ot_hbm_idx_chunk_rt_h.sv); see score_hcol_h0'),
}


def recipes(a):
    """recipes_split.json + canonical_ports_split.json from split_tops.json (generated tops), MANUAL and the elab checks."""
    tops = json.load(open(a.out))
    cen = json.load(open(os.path.join(HERE, a.census)))['types']
    cut = json.load(open(os.path.join(HERE, '..', 'ports', 'ports_cut.json')))
    R, C = {}, {'schema': 'functional_type -> ports [[name, dir, width, lsb]] (the RTL top, elaborated); '
                          'type_ids -> {type_id: {cut_pin: {canonical_port: bits}}}; straps per type_id',
                'census': a.census, 'types': {}}
    allt = dict(tops)
    for k, v in MANUAL.items():
        pcs = v.get('pieces') or {pm: {p[0]: p[0] for p in cut[pm][pm]} for pm in cut if re.match(v['match'], pm)}
        allt[k] = dict(v, manual=True,
                       pieces={pm: dict(cut_to_canonical=None, map=mp, straps={}) for pm, mp in pcs.items()})
    for ft, v in allt.items():
        el = os.path.join(a.elab, ft)
        if not os.path.exists(el + '.ports'):
            el = os.path.join(a.elab, v['top'])
        if not os.path.exists(el + '.ports'):
            print('NO ELAB', ft); continue
        ports = [[nm, d, int(w), 0] for d, w, nm in (l.split() for l in open(el + '.ports'))]
        files = json.load(open(el + '.files.json'))
        ei = sum(p[2] for p in ports if p[1] == 'input'); eo = sum(p[2] for p in ports if p[1] == 'output')
        pw = {p[0]: p for p in ports}
        tmap, checks = {}, []
        for pm, rec in v['pieces'].items():
            cp = cut[pm][pm]
            ci = sum(p[2] for p in cp if p[1] == 'input'); co = sum(p[2] for p in cp if p[1] == 'output')
            if rec.get('cut_to_canonical') is None:
                m = {c: {rec['map'][c]: w} for c, _, w, _ in cp}
            else:
                m = rec['cut_to_canonical']
            # every canonical bit is covered exactly once by the cut pins, except strap ports
            cov = collections.Counter()
            for c, d in m.items():
                for nm, b in d.items():
                    cov[nm] += b
            strap_bits = sum(pw[s][2] for s in rec.get('straps', {}) if s in pw)
            sub = rec.get('subset_of_reference') or dict(ok=True, tied_in_bits=0, open_out_bits=0)
            st = set(rec.get('straps', {}))
            okmap = all(cov[nm] <= pw[nm][2] for nm in cov) and set(cov) <= set(pw) - st
            gin = sum(pw[nm][2] - cov[nm] for nm in pw if pw[nm][1] == 'input' and nm not in st)
            gout = sum(pw[nm][2] - cov[nm] for nm in pw if pw[nm][1] == 'output')
            ok = (okmap and sub['ok'] and gin == sub['tied_in_bits'] and gout == sub['open_out_bits']
                  and ei == ci + strap_bits + gin and eo == co + gout)
            checks.append(ok)
            for t in cen:
                if t['module'] == pm:
                    tmap[t['type_id']] = dict(cut_pins=m, straps=rec.get('straps', {}), cut_bits=[ci, co],
                                              **({'tied_at_parent': sub['detail']['tied'], 'open_at_parent': sub['detail']['open']}
                                                 if 'detail' in sub else {}),
                                              excluded=t['excluded'], check='PASS' if ok else 'FAIL')
                    R[t['type_id']] = dict(top=v['top'], files=files['files'], defines=v.get('defines', []),
                                           params=v.get('params', {}),
                                           macros=[mm['name'] if isinstance(mm, dict) and 'name' in mm else mm
                                                   for mm in files.get('macros', [])],
                                           functional_type=ft,
                                           port_map_note=f'canonical ports = {v["top"]} ports; cut pin -> canonical map in '
                                                         f'canonical_ports_split.json types.{ft}.type_ids["{t["type_id"]}"]'
                                                         + (f'; straps {rec["straps"]} tied at the parent' if rec.get('straps') else ''),
                                           source=v['src'])
        C['types'][ft] = dict(top=v['top'], master=v['master'], file=v['file'], ports=ports, elab_bits=[ei, eo],
                              port_check='PASS' if all(checks) else 'FAIL', type_ids=tmap)
        print(ft, v['top'], 'elab', ei, eo, 'pieces', len(v['pieces']), 'types', len(tmap), 'PASS' if all(checks) else 'FAIL')
    json.dump(R, open(os.path.join(HERE, 'recipes_split.json'), 'w'), indent=1, sort_keys=True)
    json.dump(C, open(os.path.join(HERE, 'canonical_ports_split.json'), 'w'), indent=1, sort_keys=True)


def subset(R, V, straps):
    """Variant V is the reference R with some boundary inputs tied to constants at the parent and some boundary outputs
    left open (an end-of-chain replica).  Returns {ok, tied_in_bits, open_out_bits, detail}."""
    tied, opened, bad = collections.Counter(), collections.Counter(), []
    for key, (pdir, rc) in R.pins.items():
        if key in straps:
            continue
        vc = V.pins[key][1]
        for i, (a, b) in enumerate(zip(rc, vc)):
            if a[0] == 'P' and b[0] == 'P':
                continue
            if a == b or (a[0] == 'I' and b[0] == 'I'):
                continue
            if a[0] == 'P' and R.bnd[a[1]]['dir'] == 'input' and b[0] == 'K':
                tied[sc.canon_name(R.bnd[a[1]]['can']) + '=' + b[1]] += 1; continue
            if a[0] == 'P' and R.bnd[a[1]]['dir'] == 'output' and b[0] in ('N', 'I'):
                opened[sc.canon_name(R.bnd[a[1]]['can'])] += 1; continue
            bad.append((key, i, a, b))
    return dict(ok=not bad, tied_in_bits=sum(tied.values()), open_out_bits=sum(opened.values()),
                detail=dict(tied=dict(tied), open=dict(opened), bad=[str(x) for x in bad[:20]]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--net', default='/home/ubuntu/scratch/hbm-p5-pins-1023/net')
    ap.add_argument('--only', default='')
    ap.add_argument('--out', default=os.path.join(HERE, 'split_tops.json'))
    ap.add_argument('--recipes', action='store_true')
    ap.add_argument('--census', default='census_3a7e22238.json')
    ap.add_argument('--elab', default='/home/ubuntu/scratch/core-hbm-1023/split/elab')
    a = ap.parse_args()
    if a.recipes:
        return recipes(a)
    res = json.load(open(a.out)) if os.path.exists(a.out) else {}
    nets = {}
    for key, cfg in PIECES.items():
        if a.only and key not in a.only.split(','):
            continue
        masters = cfg.get('masters') or [cfg['master']]
        m = masters[0]
        order = []
        for mm in masters:
            n = nets.get(mm) or nets.setdefault(mm, netcut.Netlist(os.path.join(a.net, f'{mm}.netlist.v')))
            order += [(k, v, n, mm) for k, v in cfg['pieces'](n, mm).items()]
        pcs = {k: v for k, v, _, _ in order}
        sig0, P0, rec = None, None, {}
        straps = {tuple(s) for s in cfg.get('straps', [])}
        for cut_mod, (inc, exc), n, m in order:
            strip = inc[0].rsplit('/', 1)[0] + '/'
            P = sc.analyse(n, m, inc, exc, strip=strip)
            sig = [s for s in sc.signature(P) if not (isinstance(s[0], tuple) and s[0] in straps)]
            if sig0 is None:
                sig0, P0 = sig, P
            same = sig == sig0
            sub = None if same else subset(P0, P, straps)
            if cfg['rtl'] is None:      # direct: the single member module is the top (every member pin is a core pin)
                assert len(P.members) == 1 and all(cl[0] == 'P' for _, cls in P.pins.values() for cl in cls), cut_mod
                pre = sc.canon_name(P.members[0][2] + '_')
                bmap = collections.defaultdict(collections.Counter)
                for b in P.bnd:
                    bmap[b['cut']][sc.canon_name(b['can'])[len(pre):]] += 1
                bmap = {k: dict(v) for k, v in bmap.items()}
            else:
                _, _, bmap = sc.emit_wrapper(P, cfg['top'], cfg['rtl'], straps)
            strap_v = {f'{r}_{p}'.removeprefix('u_'): ''.join(cl[1] for cl in reversed(P.pins[(r, p)][1]))
                       for r, p in straps}
            rec[cut_mod] = dict(cut_bits=P.cut_bits, same_structure=same, cut_to_canonical=bmap, straps=strap_v)
            if sub is not None:
                rec[cut_mod]['subset_of_reference'] = sub
            print(cut_mod, P.cut_bits, 'same' if same else ('SUBSET ' + json.dumps({k: v for k, v in sub.items() if k != 'detail'}) if sub['ok'] else 'DIFFERENT'), strap_v)
        m = masters[0]
        if cfg['rtl'] is None:
            res[key] = dict(master=m, top=cfg['top'], file=None, pieces=rec, src=cfg['src'], direct=True)
            json.dump(res, open(a.out, 'w'), indent=1)
            continue
        hdr = (f'// GENERATED by physical/die_plan/hbm/cores/harden/build_split_tops.py (CORE-HBM-SPLIT 2026-10-23). Do not edit.\n'
               f'// Functional split-piece type {key}: master {m}; replicas {len(pcs)} ({", ".join(sorted(pcs))[:300]}).\n'
               f'// Members (roles): ' + '; '.join(f'{r} = {cfg["rtl"][r][0]} {cfg["rtl"][r][1]} (as-built {netcut.base(t)} at {p})'
                                                  for p, t, r in P0.members) + '\n'
               f'// Source wiring: {cfg["src"]}\n'
               f'// Wired bit-exactly as the as-built master netlist (split_conn.py); straps = replica constants tied at the parent.\n')
        txt, ports, _ = sc.emit_wrapper(P0, cfg['top'], cfg['rtl'], straps, hdr)
        d = os.path.join(REPO, 'rtl', 'hbm_accel', 'cores_split', m)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, cfg['top'] + '.sv'), 'w').write(txt)
        res[key] = dict(master=m, top=cfg['top'], file=os.path.relpath(os.path.join(d, cfg['top'] + '.sv'), REPO),
                        ports=ports, pieces=rec, src=cfg['src'],
                        rtl={r: list(v) for r, v in cfg['rtl'].items()})
        json.dump(res, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
