#!/usr/bin/env python3
"""die-evidence-2 r25gp-power (2026-10-09): compose the R25GP die's peak power from MEASURED block power.

Inputs
  --kv DIR       r25gp_block_power.tcl outputs (<tag>.kv + <tag>.src: OpenSTA report_power at TT 0.70 V / 25 C,
                 the route's own SDC at 0.833 ns, activity points a20 / a10 / a00)
  --out FILE     results/physical/die_evidence_20261009/hbm_r25gp_power.json

Composition
  * every die instance takes its master's MEASURED power where a recipe below names routed blocks (a hierarchical
    master is the sum of its routed parts x their counts in the parent netlist), else the floorplan ASSUMPTION
    (tools/hbm_accel_die_fp.py DENS / DENS_OVR x the instance's shaved outline); 'class' entries take the
    area-weighted measured W/mm2 of measured siblings of the same kind (say so in the record);
  * relay stations (kind waypoint): the measured station W/mm2 (if measured) x the waypoint area, with the
    per-flop estimate (2.6 fJ per flop-cycle x relay flop-bits) as a cross-check;
  * die wires (buses between instances, not inside any block): bits x Manhattan length (instance centres) x
    0.2 fF/um x 1.6 x V^2 x f x activity / 2.
Options
  (a) ICG: a clock-gated idle block pays leakage only; ungated it pays its measured clocked floor (a00);
  (b) per-region duty from the HGI token timelines (results/arch/hgi_sim_20261009, DS-V4.1 1M and Qwen3-8B P8191);
  (c) activity 0.1 (a10) instead of 0.2.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_accel_die_fp as F  # noqa: E402

V, FREQ = 0.70, 1.2e9
WIRE_F_PER_UM = 0.2e-15 * 1.6
FLOP_J = 2.6e-15
LIMIT = 474.56
PTS = ('a20', 'a10', 'a00')

# master -> list of (measured block tag, count, note)
RECIPES = {
    'hfd_attn_half_lo': [('attn_lo', 1, 'half top (post-CTS, placement parasitics)'), ('attn_quad', 2, 'ot_attn_tile_m6h1q'),
                         ('attn_hgrp', 8, 'ot_attn_hgrp_m6h1 (4 per quad)'), ('attn_bank_ew', 11, 'ot_attn_bank_ew544'),
                         ('attn_bank_sn', 68, 'ot_attn_bank_sn544')],
    'hfd_attn_half_hi': [('attn_hi', 1, 'half top (post-CTS, placement parasitics)'), ('attn_quad', 2, 'ot_attn_tile_m6h1q'),
                         ('attn_hgrp', 8, 'ot_attn_hgrp_m6h1 (4 per quad)'), ('attn_bank_ew', 6, 'ot_attn_bank_ew544'),
                         ('attn_bank_sn', 46, 'ot_attn_bank_sn544')],
    'hfd_sm': [('sm_tile_w', 8, 'ot_hbm_accel_smh_tile_w'), ('sm_tile_e', 8, 'ot_hbm_accel_smh_tile_e'),
               ('sm_be_w', 4, 'ot_hbm_accel_smh_be_w'), ('sm_be_e', 4, 'ot_hbm_accel_smh_be_e'),
               ('sm_front_n', 1, 'ot_hbm_accel_smh_front_n'), ('sm_front_n', 1, 'PROXY: front_c (INT8 front) taken as front_n'),
               ('sm_front_s', 1, 'ot_hbm_accel_smh_front_s')],
    'hfd_su': [('su_lane', 192, 'ot_su12_light x 192 lanes (tools/hbm_hub_quarter_gen.py su: 6 chains x 8 groups x 2 x 2)'),
               ('@flops', 247252, 'quarter envelope registers (su/rtl/plan.json flops) at 2.6 fJ per flop-cycle')],
    'hfd_sfu': [('sfu_lane', 32, 'ot_su12_sfu x 32 lanes'), ('@flops', 60498, 'quarter envelope registers at 2.6 fJ')],
    'hfd_hc': [('hc_lane', 88, 'ot_dsrom_su_hcpost_lane x 88 lanes'), ('@flops', 19870, 'quarter envelope registers at 2.6 fJ')],
    'hfd_cmdproc_n': [('cmdproc_n', 1, '')],
    'hfd_cmdproc_s': [('cmdproc_s', 1, '')],
    'hfd_barrier': [('barrier', 1, '')],
    'hfd_quant': [('quant', 1, 'hgi_quant c360p route')],
    'hfd_mtp': [('mtp', 1, 'hfd_mtp_x_stop route (bare controller)')],
    'hfd_su_full': [('su_full', 1, 'post-CTS, placement parasitics')],
    'hfd_vm_ne': [('vm8v_see', 2, 'PROXY: two VM8V halves (vm8v_see measured)')],
    'hfd_vm_nw': [('vm8v_see', 2, 'PROXY: two VM8V halves (vm8v_see measured)')],
    'hfd_vm_se': [('vm8v_see', 2, 'PROXY: two VM8V halves (vm8v_see measured)')],
    'hfd_vm_sw': [('vm8v_see', 2, 'PROXY: two VM8V halves (vm8v_see measured)')],
}
for b in range(6):
    RECIPES[f'hfd_index_q_b{b}'] = [(f'idxq_b{b}', 1, '')]
for f in ('SE', 'SW'):
    for s in range(9):
        RECIPES[f'hfd_svc_{f}_s{s}'] = [(f'svc_{f}_s{s}', 1, '')]
# proxies when the named block is missing: master -> block whose W/mm2 is applied to the master's outline
DENSITY_PROXY = {'hfd_cmdproc_s': 'cmdproc_n'}
CLASS_OF = {'svc': 'svc', 'index_q': 'index_q'}

# region -> duty source per workload (unit busy / token cycles), see duty()
UNIT_OF_MASTER = [('hfd_sm', 'SM'), ('hfd_attn', 'ATT'), ('hfd_su_full', 'SU'), ('hfd_su_red', 'SU'), ('hfd_su', 'SU+FUSED'),
                  ('hfd_sfu', 'SFU'), ('hfd_hc', 'HC'), ('hfd_idx', 'IDX'), ('hfd_index_q', 'IDX'), ('hfd_svc', 'SVC'),
                  ('hfd_coll', 'COLL'), ('hfd_vm', 'COLL'), ('hfd_quant', 'SU'), ('hfd_router', 'SM'), ('hfd_loader', 'DMA'),
                  ('hfd_mtp', 'ARGMAX'), ('hfd_cmdproc', 'ON'), ('hfd_barrier', 'ON')]
UNIT_OF_BUS = {'phy_dfi': 'SVC', 'weight': 'SM', 'weight_req': 'SM', 'x_trunk': 'SM', 'x_leaf': 'SM', 'result_leaf': 'SM',
               'result_trunk': 'SM', 'control': 'ON', 'control_leaf': 'ON', 'expert_req': 'SM', 'loader_mem': 'DMA',
               'kv_rows': 'ATT', 'attn_query': 'ATT', 'attn_packet': 'ATT', 'attn_chain': 'ATT', 'attn_root': 'ATT',
               'attn_out': 'ATT', 'hub': 'SU+FUSED', 'link': 'COLL', 'host': 'ON', 'clock_trunk': 'ON', 'reset_tree': 'ON',
               'index_native': 'IDX'}


def load_kv(d: Path):
    out = {}
    for f in sorted(d.glob('*.kv')):
        kv = dict(l.split('=', 1) for l in f.read_text().splitlines() if '=' in l)
        if 'a20.total.total' not in kv:
            continue
        try:
            vals = {k: float(v) for k, v in kv.items() if k.startswith(PTS)}
        except ValueError:
            continue
        bad = lambda pt: any(math.isnan(x) or math.isinf(x) for k, x in vals.items() if k.startswith(pt + '.'))
        extrap = False
        if bad('a20') and not bad('a10') and not bad('a00'):
            # multi-clock station routes: OpenSTA returns Inf at the 0.2 point only; power is linear in the data
            # activity, so a20 = 2 a10 - a00 (labelled a20_extrapolated)
            for k in [k for k in vals if k.startswith('a20.')]:
                vals[k] = 2 * vals['a10.' + k[4:]] - vals['a00.' + k[4:]]
            extrap = True
        if any(math.isnan(x) or math.isinf(x) for x in vals.values()):
            continue
        src = {}
        sf = f.with_suffix('.src')
        if sf.exists():
            for l in sf.read_text().splitlines():
                p = l.split()
                src[p[0]] = p[1:]
        tag = f.stem
        w, h = float(kv['die_w_um']), float(kv['die_h_um'])
        r = dict(tag=tag, outline_um=[w, h], area_mm2=round(w * h / 1e6, 6), parasitics=kv['parasitics'],
                 clock=kv['clock'], clock_period_ns=float(kv['clock_period_ns']), registers=int(kv['registers']),
                 icg_cells=int(kv['icg_cells']), insts=int(kv['insts']),
                 macro_libs={k[10:]: v for k, v in kv.items() if k.startswith('macro_lib.')},
                 macro_missing_lib=kv.get('macro_missing_lib', ''), source=src, a20_extrapolated=extrap)
        for pt in PTS:
            r[pt] = {g: {p: vals[f'{pt}.{g}.{p}'] for p in ('internal', 'switching', 'leakage', 'total')}
                     for g in ('total', 'sequential', 'combinational', 'clock', 'macro')}
        r['w'] = {pt: r[pt]['total']['total'] for pt in PTS}
        r['leak_w'] = r['a20']['total']['leakage']
        r['w_per_mm2_a20'] = r['w']['a20'] / r['area_mm2']
        r['clock_share_a20'] = r['a20']['clock']['total'] / r['w']['a20']
        r['clocked_floor_share_a20'] = (r['w']['a00'] - r['leak_w']) / r['w']['a20']
        out[tag] = r
    return out


def flop_w():
    return FLOP_J * FREQ


def duty_tables():
    """Unit busy fraction of the token, per workload (HGI pathfinding timelines)."""
    base = ROOT / 'results/arch/hgi_sim_20261009'
    tabs = {}
    for name, f in (('ds_v41_1M', 'ds_native_timing_1M.json'), ('qwen3_8b_P8191', 'qwen_timing_P8191_v10.json')):
        d = json.loads((base / f).read_text())
        x = d['result']['S0'] if 'S0' in d['result'] else d['result']
        T = x['total_cycles']
        u = {k: v['busy'] / T for k, v in x['per_unit'].items()}
        t = dict(SM=u.get('SM', 0), ATT=u.get('ATT', 0), SU=u.get('SU', 0), FUSED=u.get('FUSED', 0), HC=u.get('HC', 0),
                 IDX=u.get('IDX', 0), COLL=u.get('COLL', 0), DMA=u.get('DMA', 0), ARGMAX=u.get('ARGMAX', 0),
                 SFU=u.get('SFU', u.get('SU', 0)))
        t['SU+FUSED'] = min(1.0, t['SU'] + t['FUSED'])
        t['SVC'] = min(1.0, t['SM'] + t['DMA'])          # the stream service runs while weights / KV stream
        t['ON'] = 1.0
        tabs[name] = dict(source=f'results/arch/hgi_sim_20261009/{f}', grade=d.get('grade', ''),
                          token_cycles=T, duty={k: round(v, 4) for k, v in t.items()})
    env = {k: max(tabs[w]['duty'][k] for w in tabs) for k in tabs['ds_v41_1M']['duty']}
    tabs['envelope_max'] = dict(source='per-unit max of the two workloads', duty=env)
    return tabs


def unit_of(master, kind):
    if kind == 'waypoint':
        return 'ON'
    for p, u in UNIT_OF_MASTER:
        if master.startswith(p):
            return u
    return 'ON'


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--kv', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    B = load_kv(Path(a.kv))
    v = F.variant_arg('r25gp')
    m = F.build(v, network_probe=bool(v and v.get('sm_physical_grid')))
    assumed = F.die_power(m)

    # ---- per master: assumed and measured
    rows = defaultdict(lambda: dict(n=0, area_mm2=0.0, assumed_w=0.0))
    for it in m['insts']:
        r = rows[it.master]
        r['n'] += 1
        r['kind'] = it.kind
        r['area_mm2'] += (it.w + F.SHAVE) * (it.h + F.SHAVE) / 1e6
        r['assumed_w'] += F.inst_power(it)
        r['outline_um'] = [it.w, it.h]
    # class densities from measured siblings
    cls_meas = defaultdict(lambda: [0.0, {pt: 0.0 for pt in PTS}, 0.0])
    for mst, r in rows.items():
        rec = RECIPES.get(mst)
        if rec and all(t.startswith('@') or t in B for t, _, _ in rec) and len(rec) == 1:
            c = 'svc' if r['kind'] == 'svc' else ('index_q' if mst.startswith('hfd_index_q') else None)
            if c:
                b = B[rec[0][0]]
                cls_meas[c][0] += b['area_mm2']
                for pt in PTS:
                    cls_meas[c][1][pt] += b['w'][pt]
                cls_meas[c][2] += b['leak_w']
    cls_dens = {c: dict(area_mm2=x[0], w_per_mm2={pt: x[1][pt] / x[0] for pt in PTS}, leak_per_mm2=x[2] / x[0])
                for c, x in cls_meas.items() if x[0] > 0}

    masters = {}
    for mst, r in sorted(rows.items(), key=lambda kv: -kv[1]['assumed_w']):
        if r['kind'] in ('phy', 'link', 'serdes_slab', 'host_slab'):
            masters[mst] = dict(kind=r['kind'], n=r['n'], area_mm2=round(r['area_mm2'], 4), assumed_w=0.0,
                                basis='own supply (PHY / SerDes / host): not on the core grid (generator rule)',
                                w={pt: 0.0 for pt in PTS}, leak_w=0.0, grade='excluded')
            continue
        if r['kind'] == 'waypoint':
            continue
        rec = RECIPES.get(mst)
        per = None
        grade, parts, basis = 'assumed', [], None
        if rec and all(t.startswith('@') or t in B for t, _, _ in rec):
            per = {pt: 0.0 for pt in PTS}
            leak = 0.0
            for t, c, note in rec:
                if t == '@flops':
                    for pt in PTS:
                        per[pt] += c * flop_w() * (1.0 if pt != 'a00' else 0.7)
                    parts.append(dict(part='envelope registers (estimate)', count=c, w_each=flop_w(), note=note))
                    continue
                b = B[t]
                for pt in PTS:
                    per[pt] += c * b['w'][pt]
                leak += c * b['leak_w']
                parts.append(dict(part=t, count=c, w_each_a20=round(b['w']['a20'], 6), note=note))
            grade = 'measured' if not any('PROXY' in n for _, _, n in rec) else 'measured (with proxy part)'
            if any(t == '@flops' for t, _, _ in rec):
                grade = 'measured lanes + estimated envelope'
        elif mst in DENSITY_PROXY and DENSITY_PROXY[mst] in B:
            b = B[DENSITY_PROXY[mst]]
            per = {pt: b['w'][pt] / b['area_mm2'] * r['area_mm2'] / r['n'] for pt in PTS}
            leak = b['leak_w'] / b['area_mm2'] * r['area_mm2'] / r['n']
            grade = f"proxy density ({DENSITY_PROXY[mst]} measured W/mm2)"
        else:
            c = 'svc' if r['kind'] == 'svc' else ('index_q' if mst.startswith('hfd_index_q') else None)
            if c in cls_dens:
                per = {pt: cls_dens[c]['w_per_mm2'][pt] * r['area_mm2'] / r['n'] for pt in PTS}
                leak = cls_dens[c]['leak_per_mm2'] * r['area_mm2'] / r['n']
                grade = f'class density (area-weighted measured {c} siblings)'
        if per is None:
            dens = r['assumed_w'] / r['area_mm2'] if r['area_mm2'] else 0.0
            masters[mst] = dict(kind=r['kind'], n=r['n'], area_mm2=round(r['area_mm2'], 4),
                                assumed_w=round(r['assumed_w'], 3), grade='assumed',
                                basis=f'floorplan density {dens:.3f} W/mm2 (DENS / DENS_OVR)',
                                w={'a20': round(r['assumed_w'], 3)}, leak_w=None)
            continue
        tot = {pt: per[pt] * r['n'] for pt in PTS}
        masters[mst] = dict(kind=r['kind'], n=r['n'], area_mm2=round(r['area_mm2'], 4), assumed_w=round(r['assumed_w'], 3),
                            grade=grade, parts=parts, w_each={pt: round(per[pt], 6) for pt in PTS},
                            w={pt: round(tot[pt], 3) for pt in PTS}, leak_w=round(leak * r['n'], 5),
                            w_per_mm2_outline_a20=round(tot['a20'] / r['area_mm2'], 4))

    # ---- relay stations (waypoints)
    wp_area = sum(r['area_mm2'] for r in rows.values() if r['kind'] == 'waypoint')
    wp_n = sum(r['n'] for r in rows.values() if r['kind'] == 'waypoint')
    wp_assumed = sum(r['assumed_w'] for r in rows.values() if r['kind'] == 'waypoint')
    stn = [t for t in ('stn_r4', 'stn_r27', 'mcast_r5', 'meso_r1') if t in B]   # relay station masters measured
    I = {it.name: it for it in m['insts']}
    bus = defaultdict(lambda: dict(bits=0, bit_um=0.0, flop_bits=0))
    for name, cls, nb, eps in [b_[:4] for b_ in m['buses']]:
        pts = [(I[i].x + I[i].w / 2, I[i].y + I[i].h / 2) for i, _ in eps if i in I]
        if len(pts) < 2:
            continue
        ls = [abs(pts[0][0] - p[0]) + abs(pts[0][1] - p[1]) for p in pts[1:]]
        bus[cls]['bits'] += nb
        bus[cls]['bit_um'] += nb * sum(ls)
        bus[cls]['flop_bits'] += nb * sum(math.ceil(l / 504.0) for l in ls)
    flop_bits = sum(b_['flop_bits'] for b_ in bus.values())
    if stn:
        sa = sum(B[t]['area_mm2'] for t in stn)
        sd = {pt: sum(B[t]['w'][pt] for t in stn) / sa for pt in PTS}
        wp = {pt: sd[pt] * wp_area for pt in PTS}
        wp_grade = f'measured station density ({", ".join(stn)}: {sd["a20"]:.3f} W/mm2 at a20) x waypoint area'
    else:
        wp = {'a20': flop_bits * flop_w(), 'a10': flop_bits * flop_w() * 0.85, 'a00': flop_bits * flop_w() * 0.7}
        wp_grade = 'estimate: relay flop-bits x 2.6 fJ per flop-cycle'
    relay = dict(instances=wp_n, area_mm2=round(wp_area, 4), assumed_w=round(wp_assumed, 3), grade=wp_grade,
                 w={pt: round(x, 3) for pt, x in wp.items()},
                 cross_check_flop_estimate=dict(relay_flop_bits=flop_bits, stage_um=504.0, j_per_flop_cycle=FLOP_J,
                                                w=round(flop_bits * flop_w(), 2),
                                                note='bits x ceil(Manhattan centre-to-centre / 504 um) per sink'))
    # ---- die wires
    wires = {}
    for cls, b_ in sorted(bus.items()):
        c = b_['bit_um'] * WIRE_F_PER_UM
        wires[cls] = dict(bits=b_['bits'], bit_m=round(b_['bit_um'] / 1e6, 2), cap_nf=round(c * 1e9, 3),
                          w_at_activity_1=0.5 * c * V * V * FREQ)
    wire_w = {pt: sum(x['w_at_activity_1'] for x in wires.values()) * act for pt, act in (('a20', 0.2), ('a10', 0.1), ('a00', 0.0))}

    # ---- totals
    def tot(pt, measured_only=None):
        s = 0.0
        for mst, r in masters.items():
            if measured_only is True and r['grade'] == 'assumed':
                continue
            if measured_only is False and r['grade'] != 'assumed':
                continue
            s += r['w'].get(pt, r['w']['a20'])
        return s
    def grp(g):
        if g.startswith('measured'):
            return 'measured'
        if g.startswith(('proxy', 'class')):
            return 'proxy_or_class_density'
        return g
    measured_a20 = tot('a20', True)
    assumed_a20 = tot('a20', False)
    total_a20 = measured_a20 + assumed_a20 + relay['w']['a20'] + wire_w['a20']

    # ratio for assumed blocks at other points / floors: area-weighted mean of measured blocks
    mb = [r for r in masters.values() if r['grade'] not in ('assumed', 'excluded')]
    r10 = sum(r['w']['a10'] for r in mb) / sum(r['w']['a20'] for r in mb)
    r00 = sum(r['w']['a00'] for r in mb) / sum(r['w']['a20'] for r in mb)
    rleak = sum(r['leak_w'] for r in mb) / sum(r['w']['a20'] for r in mb)

    def mpt(r, pt):
        if r['grade'] == 'excluded':
            return 0.0
        if r['grade'] == 'assumed':
            return r['w']['a20'] * dict(a20=1.0, a10=r10, a00=r00)[pt]
        return r['w'][pt]

    def mleak(r):
        if r['grade'] == 'excluded':
            return 0.0
        return r['leak_w'] if r['leak_w'] is not None else r['w']['a20'] * rleak

    total = {pt: sum(mpt(r, pt) for r in masters.values()) + relay['w'][pt] + wire_w[pt] for pt in PTS}
    leak_total = sum(mleak(r) for r in masters.values())

    # ---- options
    D = duty_tables()
    opts = {}
    for wl, tab in D.items():
        du = tab['duty']
        no_icg = icg = 0.0
        per_unit = defaultdict(float)
        for mst, r in masters.items():
            if r['grade'] == 'excluded':
                continue
            d = du[unit_of(mst, r['kind'])]
            pk, fl, lk = mpt(r, 'a20'), mpt(r, 'a00'), mleak(r)
            no_icg += fl + d * (pk - fl)
            icg += lk + d * (pk - lk)
            per_unit[unit_of(mst, r['kind'])] += lk + d * (pk - lk)
        # relays: always clocked (no ICG in the stations); duty-weighted data part
        no_icg += relay['w']['a00'] + du['ON'] * (relay['w']['a20'] - relay['w']['a00'])
        icg += relay['w']['a00'] + du['ON'] * (relay['w']['a20'] - relay['w']['a00'])
        wd = sum(wires[c]['w_at_activity_1'] * 0.2 * du[UNIT_OF_BUS.get(c, 'ON')] for c in wires)
        no_icg += wd
        icg += wd
        opts[wl] = dict(duty=du, source=tab['source'], no_icg_w=round(no_icg, 1), with_icg_w=round(icg, 1),
                        wire_w=round(wd, 1))
    floor_w = sum(mpt(r, 'a00') - mleak(r) for r in masters.values())
    proposed = {}
    for k in ('sm', 'attn_tile', 'svc', 'hub', 'spine'):
        mm = [r for r in masters.values() if r['kind'] == k and r['grade'].startswith('measured')]
        if mm:
            proposed[k] = dict(measured_w_per_mm2=round(sum(r['w']['a20'] for r in mm) / sum(r['area_mm2'] for r in mm), 3),
                               measured_area_mm2=round(sum(r['area_mm2'] for r in mm), 2),
                               measured_masters=len(mm), current=F.DENS.get(k))
    if relay['grade'].startswith('measured'):
        proposed['waypoint'] = dict(measured_w_per_mm2=round(relay['w']['a20'] / wp_area, 3), current=F.DENS['waypoint'])

    rec = dict(
        schema='opentallas.hbm_r25gp_power.v1', die='HBM generic die R25GP (tools/hbm_accel_die_fp.py plan --ds-var r25gp)',
        generator_sha256=hashlib.sha256((ROOT / 'tools/hbm_accel_die_fp.py').read_bytes()).hexdigest(),
        die_mm2=round(m['geo']['W'] * m['geo']['H'] / 1e6, 2), instances=len(m['insts']),
        cooling_limit_w=LIMIT,
        method=dict(
            tool='OpenSTA report_power (openroad/orfs:asap7lock), scripts/r25gp_block_power.tcl via scripts/r25gp_power_run.sh',
            corner='TT 0.70 V / 25 C, ASAP7 RVT + LVT + SLVT TT NLDM liberties (VT-swapped routes), macro own _tt.lib',
            clock="each route's own SDC (0.833 ns, 1.2 GHz); clock nets toggle every cycle",
            activity_points=dict(a20='set_power_activity -global -activity 0.2 and -input -activity 0.2: every non-clock '
                                     'net (register outputs, internal nets, inputs) at 0.2 transitions per cycle -- the '
                                     "floorplan densities' 'peak in-phase' point (the stated point)",
                                 a10='the same at 0.1 (option c)', a00='data idle (0.0), clock running: the clocked floor'),
            parasitics='6_final.spef where the route finished; placement-estimated (setRC) on post-CTS databases (labelled)',
            relay_and_wires=f'die wires: bits x Manhattan centre-to-centre x 0.2 fF/um x 1.6, 0.5 C V^2 f x activity; '
                            f'relay flops 2.6 fJ per flop-cycle (Qwen tile study) as the cross-check'),
        assumed_generator=dict(peak_in_phase_w=assumed['peak_in_phase_w'], by_kind=assumed['by_kind'], basis=assumed['basis']),
        blocks=B, masters=masters, relay_stations=relay, die_wires=dict(by_class=wires, w={k: round(x, 2) for k, x in wire_w.items()}),
        total=dict(
            peak_in_phase_a20_w=round(total['a20'], 1), a10_w=round(total['a10'], 1), clocked_idle_a00_w=round(total['a00'], 1),
            leakage_w=round(leak_total, 2),
            a20_split=dict(measured_masters_w=round(measured_a20, 1), assumed_masters_w=round(assumed_a20, 1),
                           relay_w=relay['w']['a20'], die_wires_w=round(wire_w['a20'], 1)),
            a20_by_grade={g: round(sum(r['w']['a20'] for r in masters.values() if grp(r['grade']) == g), 1)
                          for g in ('measured', 'proxy_or_class_density', 'assumed')},
            measured_share_of_a20=round(measured_a20 / total['a20'], 3),
            assumed_share_of_a20=round(assumed_a20 / total['a20'], 3),
            verdict=('PASS' if total['a20'] <= LIMIT else 'FAIL') + f" at the peak in-phase point: {total['a20']:.1f} W vs {LIMIT} W",
            assumed_point_ratios_from_measured=dict(a10_over_a20=round(r10, 3), a00_over_a20=round(r00, 3),
                                                    leak_over_a20=round(rleak, 4))),
        options=dict(
            a_icg=dict(rtl_icg_cells_in_measured_blocks=sum(b['icg_cells'] for b in B.values()),
                       clocked_floor_w=round(floor_w, 1),
                       note='No measured HBM-die block instantiates an ICG (icg_cells 0 in every route; no ot_hdc_cg in '
                            'rtl/hbm_accel, the attention or the svc RTL). At peak in phase every block is active, so ICG '
                            'cannot lower the a20 number; it removes the clocked floor of idle blocks under the duty mix '
                            '(b), where with_icg_w applies.'),
            b_duty_mix=opts,
            c_activity_0p1=dict(w=round(total['a10'], 1))),
        proposed_dens=proposed,
    )
    Path(a.out).write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(total=rec['total'], options={k: (v if k != 'b_duty_mix' else {w: {kk: vv for kk, vv in x.items() if kk != 'duty'} for w, x in v.items()}) for k, v in rec['options'].items()}, proposed=proposed), indent=1))
    for mst, r in masters.items():
        if r['grade'] != 'excluded':
            print(f"{mst:28s} {r['kind']:9s} n={r['n']:3d} A={r['area_mm2']:8.3f} assumed={r['assumed_w']:7.2f} a20={r['w']['a20']:7.2f}  {r['grade']}")
    print('relay', relay['w'], relay['grade'], '| wires', {k: round(x, 1) for k, x in wire_w.items()})


if __name__ == '__main__':
    main()
