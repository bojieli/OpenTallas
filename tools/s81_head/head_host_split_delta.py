#!/usr/bin/env python3
"""DH55-HSPLIT (COORD ruling (a), GEOM-111, 2026-11-02): split HEAD type hd_host into two abutted types.

hd_host_w = lane0 + HBC1 + host276 rx/tx + frame mux + job-active pin (ot_s81hd_host_w_core), at the host origin;
hd_host_e = lane1 only (ot_s81hd_host_e_core), at origin x + 648.  Two 648 x 570.24 slots in the old footprint.
Seam = two new abutted die ports (one lane each):
  host_l1rx__0  host_e.l1_rx_o -> host_w.l1_rx_i  558 = {flt[3:0], rx_v, rx_d[552:0]}  (+1 cycle, W landing register)
  host_l1tx__0  host_w.l1_tx_o -> host_e.l1_tx_i  554 = {tx_v, tx_d[552:0]}           (+1 cycle, W face register)
The six die ports of host are re-pointed (coll_*0 / h_tx / h_rx -> host_w, coll_*1 -> host_e).

Writes NEW plan / sidecar copies only (never the canonical files).  Geometric records are split exactly (buses,
hard-core origins, edge clocks, reset taps, start capture).  Records DERIVED by the CA / START compose (clock
landing contract, count straps, reset_start_raw_exports, die landing network, sidecar count_aligned / collector)
cannot be split by geometry: with --raw they are dropped for the two new types (head_n3_split_delta precedent,
status RAW_RECOMPOSE_REQUIRED); the report lists them.
"""
import argparse, copy, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/s81_head'))
from head_host_plan_delta import MESH_SOURCES, SOURCES as HOST_SOURCES

W_CORE = 'rtl/dsrom_sys/s81_head/ot_s81hd_host_w_core.sv'
E_CORE = 'rtl/dsrom_sys/s81_head/ot_s81hd_host_e_core.sv'
# W keeps the whole original closure (HBC, host276, frame mux in ot_s81hd_host_ep_core.sv) plus its split core.
W_SOURCES = list(dict.fromkeys(HOST_SOURCES + [W_CORE]))
# E = one safe8 mesh lane: the mesh-lane closure only.
E_SOURCES = list(dict.fromkeys(MESH_SOURCES + [E_CORE]))

OLD, PART = 'hd_host', 'host'


def plan_sources(old_sources, east):
    """Physical kit read-set from the base type's own list (macro _bb.v black boxes, no simulation models, no file
    gen.py supplies itself): W = base + W core; E = the base files of the lane closure + E core."""
    def stem(f):
        return f[:-5] + '.v' if f.endswith('_bb.v') else f
    keep = set(E_SOURCES) if east else None
    out = [f for f in old_sources if keep is None or stem(f) in keep]
    return out + [E_CORE if east else W_CORE]
TW, TE = 'hd_host_w', 'hd_host_e'
PW, PE = 'host_w', 'host_e'
SPLIT_X = 648.0                       # 12000 ASAP7 sites (0.054 um), 150 x 4.32 um lattice
SEAM = dict(rx=dict(bus_w='l1_rx_i', bus_e='l1_rx_o', width=558, window=[196.0, 376.0], lane='host_l1rx'),
            tx=dict(bus_w='l1_tx_o', bus_e='l1_tx_i', width=554, window=[384.0, 564.0], lane='host_l1tx'))
W_BUSES, E_BUSES = {'coll_i0', 'coll_o0', 'h_tx_i', 'h_rx_o'}, {'coll_i1', 'coll_o1'}
# plan convention (schema.lane_natural): source out boundary flop + destination in boundary flop = 2.  The E-side
# flop of each seam is the lane's own existing flop (RX: lsc_r0m/r1m rd_q/rv_q/flt_q drive l1_rx_o; TX: the lane's
# txd_p / kf input flops land l1_tx_i), so each direction adds ONE data cycle (the W landing / W face register).
SEAM_LAT = {'cycles': 2, 'stations': 0, 'boundary': 2, 'faces': 1, 'fixed': 0, 'clock_landing': 0, 'natural': 2,
            'pad': 0}
SEAM_PREEXISTING_FLOPS = 1
DERIVED = ['clock.landing_contract (per type; E needs its own landing origin/START + collector root on the seam)',
           'clock.landing_network (die): host ends re-pointed by bus; seam collector/START edges for host_e missing', 'count_straps', 'reset_start_raw_exports',
           'clock.start_capture_um (hd_host_e)', 'sidecar count_aligned / collector entries for host_w/host_e',
           'reset.in_sites / reset wavefront offsets', 'latency lanes of the re-pointed host ports (gen.py latency)']


def _east(xy):
    return [round(xy[0] - SPLIT_X, 6), xy[1]]


def _split_x(items, key):
    w, e = [], []
    for it in items:
        xy = key(it)
        (w if xy[0] < SPLIT_X else e).append(it)
    return w, e


def split_type(old, raw=True, cells_e_frac=0.42):
    W, H = old['outline_um']
    if (W, H) != [1296.0, 570.24] and (W, H) != (1296.0, 570.24):
        raise ValueError(f'hd_host outline changed: {old["outline_um"]}')
    if [c['module'] for c in old['contents']] != ['ot_s81hd_host_ep_core']:
        raise ValueError('hd_host content changed; recompose explicitly')
    out = {}
    for tn in (TW, TE):
        east = tn == TE
        t = copy.deepcopy(old)
        t['module'] = 'ot_s81hd_host_e_ep' if east else 'ot_s81hd_host_w_ep'
        t['outline_um'] = [SPLIT_X, H]
        t['cells'] = round(old['cells'] * (cells_e_frac if east else 1 - cells_e_frac))
        params = dict(old['contents'][0].get('params', {}))
        if east:
            params = {k: v for k, v in params.items() if k == 'CH_B'}
            t['contents'] = [dict(inst='u_core', module='ot_s81hd_host_e_core', status='new',
                                  bind={'ck': 'clk', 'rst_n': 'rst_n'}, params=params,
                                  note='DH55-HSPLIT: lane1 (CH_B[1]) only; seam l1_rx_o (E RX pin flops) / l1_tx_i (lane tx pin flops)')]
            t['sources'] = plan_sources(old.get('sources', []), True)
        else:
            t['contents'] = [dict(inst='u_core', module='ot_s81hd_host_w_core', status='new',
                                  bind=dict(old['contents'][0]['bind']), params=params,
                                  note='DH55-HSPLIT: lane0 + HBC1 + host276 + frame mux; seam landing/launch registers at the E face')]
            t['sources'] = plan_sources(old.get('sources', []), False)
        t['note'] = old.get('note', '') + (' | DH55-HSPLIT 11-02: %s half of hd_host (COORD GEOM-111 ruling (a)); '
                                          'cells = proportional pre-synth estimate' % ('E lane1' if east else 'W lane0+HBC+host276+mux'))
        # buses: original face windows (E: S face shifted by -648) + the seam
        buses = []
        for b in old['buses']:
            if (b['name'] in E_BUSES) != east:
                continue
            nb = copy.deepcopy(b)
            if east:
                if nb['face'] not in ('S', 'N'):
                    raise ValueError('E bus not on a horizontal face: ' + nb['name'])
                nb['window_um'] = [round(v - SPLIT_X, 6) for v in nb['window_um']]
            if not (0 <= nb['window_um'][0] < nb['window_um'][1] <= (H if nb['face'] in 'EW' else SPLIT_X)):
                raise ValueError(f'{tn}.{nb["name"]} window outside the half: {nb["window_um"]}')
            buses.append(nb)
        for s in SEAM.values():
            name = s['bus_e'] if east else s['bus_w']
            d = 'out' if name.endswith('_o') else 'in'
            buses.append(dict(name=name, dir=d, width=s['width'], kind='data', leaf='u_core.' + name,
                              face='W' if east else 'E', window_um=list(s['window']), layers=['M4', 'M6'], order='lsb_low'))
        t['buses'] = buses
        # hard cores: lane0 -> W (same origin), lane1 -> E (origin - 648)
        lane = 'u_core.u_lane1.' if east else 'u_core.u_lane0.'
        hcs = []
        for h in old['hard_cores']:
            if not h['inst'].startswith(('u_core.u_lane0.', 'u_core.u_lane1.')):
                raise ValueError('unexpected hard core ' + h['inst'])
            if h['inst'].startswith(lane):
                nh = copy.deepcopy(h)
                if east:
                    nh['origin_um'] = _east(nh['origin_um'])
                x0, y0 = nh['origin_um']; w, hh = nh['outline_um']
                if not (0 <= x0 and x0 + w <= SPLIT_X and 0 <= y0 and y0 + hh <= H):
                    raise ValueError('macro outside the half: ' + nh['inst'])
                hcs.append(nh)
        t['hard_cores'] = hcs
        # clock: one tap at the half's centre; edge clocks by face ownership
        ck = t['clock']
        ck['tap_um'] = [SPLIT_X / 2, H / 2]
        ew, ee = _split_x(old['clock'].get('edge_clocks', []), lambda r: r['tap_um'])
        ck['edge_clocks'] = [dict(r, tap_um=_east(r['tap_um'])) for r in ee] if east else ew
        if east:
            ck.pop('start_capture_um', None)
        # reset: local taps by x; START role bootstrap on both (lane1 carries the pre-START CSR frames)
        rw, re_ = _split_x(old['reset'].get('local_taps_um', []), lambda r: r)
        t['reset']['local_taps_um'] = [_east(r) for r in re_] if east else rw
        t['reset']['start_role'] = 'bootstrap'
        if raw:
            ck.pop('landing_contract', None)
            for k in ('count_straps', 'reset_start_raw_exports'):
                t.pop(k, None)
        out[tn] = t
    return out


def apply(base, sidecar=None, raw=True):
    p = copy.deepcopy(base)
    old = p['partition_types'][OLD]
    parts = [q for q in p['partitions'] if q['type'] == OLD]
    if [q['name'] for q in parts] != [PART] or parts[0].get('orient', 'R0') != 'R0':
        raise ValueError('expected exactly one R0 host partition of hd_host')
    new = split_type(old, raw=raw)
    del p['partition_types'][OLD]
    p['partition_types'].update(new)
    x0, y0 = parts[0]['origin_um']
    i = p['partitions'].index(parts[0])
    p['partitions'][i:i + 1] = [dict(parts[0], name=PW, type=TW, origin_um=[x0, y0]),
                                dict(parts[0], name=PE, type=TE, origin_um=[round(x0 + SPLIT_X, 6), y0])]
    repointed = []
    for port in p['ports']:
        for side in ('src', 'dst'):
            end = port[side]
            if end['part'] == PART:
                end['part'] = PE if end['bus'] in E_BUSES else PW
                if end['bus'] not in E_BUSES | W_BUSES:
                    raise ValueError(f'unexpected host bus on die port {port["id"]}: {end["bus"]}')
                repointed.append(port['id'])
    if len(repointed) != 6:
        raise ValueError(f'expected 6 host die ports, found {repointed}')
    for s in SEAM.values():
        pid = s['lane'] + '__0'
        if s is SEAM['rx']:
            src, dst = dict(part=PE, bus=s['bus_e']), dict(part=PW, bus=s['bus_w'])
        else:
            src, dst = dict(part=PW, bus=s['bus_w']), dict(part=PE, bus=s['bus_e'])
        p['ports'].append(dict(id=pid, src=src, dst=dst, width=s['width'], kind='data'))
        p['lanes'].append(dict(id=s['lane'], ports=[pid]))
        p.setdefault('latency', {}).setdefault('lanes', {})[s['lane']] = dict(SEAM_LAT)
    ins = p.get('reset', {}).get('in_sites', {})
    if OLD in ins:
        xy = ins.pop(OLD)
        ins[TE] = _east(xy) if xy[0] >= SPLIT_X else list(xy)
        ins[TW] = [600.992, xy[1]] if xy[0] >= SPLIT_X else list(xy)
    tw = p.get('clock', {}).get('tap_window', {}).get('per_type_ps', {})
    if OLD in tw:
        v = tw.pop(OLD); tw[TW] = v; tw[TE] = v
    # die landing network: keep it (its cycle counts feed the latency table) and re-point the host ends by bus
    ln = p.get('clock', {}).get('landing_network')
    if ln:
        for e in ln.get('edges', []):
            for k in ('src', 'dst'):
                end = e.get(k) or {}
                if end.get('part') == PART:
                    end['part'] = PE if end['bus'].endswith(('_coll_i1', '_coll_o1')) else PW
        for u in ln.get('start_tree', {}).get('uses', []):
            if u.get('part') == PART:
                u['part'] = PW            # the landing origin (cland_tstart_in) stays in W
    side = None
    if sidecar is not None:
        side = copy.deepcopy(sidecar)
        for r in side.get('ports', []):
            if r['port'] in repointed:
                for k in ('src', 'dst'):
                    if r[k] == PART:
                        r[k] = PE if r['port'].startswith('coll_HOST1_') else PW
        for s in SEAM.values():
            pid = s['lane'] + '__0'
            a, b = (PE, PW) if s is SEAM['rx'] else (PW, PE)
            side['ports'].append(dict(port=pid, lane=s['lane'], src=a, dst=b, src_region='host', dst_region='host',
                                      width=s['width'], kind='data', added_cycles=0))
        for r in side.get('regions', []):
            if r.get('tag') == 'host':
                r['parts'] = r.get('parts', 0) + 1
    report = dict(schema='opentallas.head_host_split_delta.v1', status='RAW_RECOMPOSE_REQUIRED' if raw else 'GEOMETRIC',
                  types={tn: dict(outline_um=t['outline_um'], macros=len(t['hard_cores']), cells_estimate=t['cells'],
                                  buses={b['name']: [b['dir'], b['width'], b['face'], b['window_um']] for b in t['buses']})
                         for tn, t in new.items()},
                  partitions={PW: [x0, y0], PE: [round(x0 + SPLIT_X, 6), y0]}, repointed_ports=repointed,
                  seam_ports=[s['lane'] + '__0' for s in SEAM.values()],
                  data_cycles_added={'E->W (host1 RX, lane1 fault)': 1, 'W->E (lane1 STATUS TX)': 1},
                  boot_dates=dict(BOOT_HEADER_EDGE='unchanged (lane0 HBC records)', BOOT_COMMIT_EDGE='unchanged',
                                  host1_csr='transport.peer_to_host_frame +1, peer_to_ctl_csr_apply +1 (launch dates 1 earlier for the same apply dates)'),
                  required=DERIVED if raw else [],
                  sidecar_stale=['count_aligned', 'collector'] if raw and sidecar is not None else [])
    return p, side, report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan', type=Path); ap.add_argument('--sidecar', type=Path)
    ap.add_argument('--out', type=Path, required=True, help='output directory (fresh)')
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit('refusing existing output (never overwrite canonical or prior verdicts)')
    base = json.loads(a.plan.read_text())
    side = json.loads(a.sidecar.read_text()) if a.sidecar else None
    p, s, r = apply(base, side)
    a.out.mkdir(parents=True)
    (a.out / 'source_plan.json').write_text(json.dumps(p, indent=1) + '\n')
    if s is not None:
        (a.out / 'source_sidecar.json').write_text(json.dumps(s, indent=1) + '\n')
    (a.out / 'split_report.json').write_text(json.dumps(r, indent=1) + '\n')
    print('HEAD_HOST_SPLIT', r['status'], json.dumps(r['data_cycles_added']))


if __name__ == '__main__':
    main()
