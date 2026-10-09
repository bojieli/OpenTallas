#!/usr/bin/env python3
"""Assembled timing views for the S81-PH partitioned die slabs (CLAUDE S81-ASSEMBLE, 2026-10-08).

The S81 die places dsfd_ctrl / dsfd_svc / dsfd_sp_capture / dsfd_bk_collector as single masters; S81-PH hardened each as
tiles (physical/s81_ph_views/closed/<tile>/<tile>_{ss,tt,ff}.lib, write_timing_model ETMs of the routed tiles).  With every
tile of a slab closed, the slab's die-facing timing is the tile timing: a die-facing slab pin IS a tile pin (tools/budgets/
tiles.py: "the slab pin is the tile pin", inherit, length 0), so the assembled ETM of a slab takes, per slab die port,
the worst arc over every tile pin bit that implements it (setup / hold / recovery / removal: max constraint; clk->q:
max delay at SS / TT, min delay at FF), tables copied verbatim (tile clock insertion is inside them: the die must NOT
add the routed insertion of an assembled master again).  Tile clock pins map to the slab clock pins by name (capture's
serial-clock ckv arcs map to the slab's only die clock 'ck', as the die netlist feeds the slab one clock).

The master-level glue (inter-tile hops inside the slab, invisible at the die ports) is checked here, flop to flop, from
the same tile ETMs: setup  T - unc_setup(60) - skew(90 intra) >= cq + 1.135 ps/um x L (x TT/SS ratio of the tile's routed clock tree at TT) + receiver 41 + setup  (SS wire model; ETM delays at the smallest load), hold  cq_min(FF) + 0.112 ps/um x L - hold - unc_hold(75) >= 0.  Collector lane <-> merger
stations are the die's common-clock station view (dsfd_stnh_512x1); svc chains are dsfd_svc_stn tiles.  Two clock
conventions are reported: raw (each ETM's routed insertion inside its arcs and an unskewed die tree: the die STA
convention for closed views) and _bal (the die tree delivers each tile early by its own max/min_clock_tree_path, i.e.
equal flop arrival: what die CTS of the tile clock pins would target).  The result goes to
results/rtl/s81_assembled_views_20261008/<slab>/ (lib per corner + glue.json); die_sta.py reads the libs as 'assembled'.

  assemble_views.py --out results/rtl/s81_assembled_views_20261008
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TILES = ROOT / 'physical/s81_ph_views/closed'
T_PS = 833.333
UNC_S, UNC_H, SKEW_INTRA = 60.0, 50.0, 90.0    # glue: signoff 60 + intra-region skew 90 (budget sheet); hold 25 + 25
# (s81-die-timing 2026-10-08: was 25 + 50; rule H1 drops the link hold term, as in die_sta.py)
_SVC = json.loads((ROOT / 'physical/s81_ph_views/svc/composition.json').read_text())
SVC_HOP = max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for c in _SVC['station_chains'] for a, b in zip(c['xy'], c['xy'][1:]))
SVC_HUB = 43.2     # the first station abuts the IO hub (composition: x = hub x - station width)
CAP_S = 562.0 / 2  # capture ctl <-> group S hop with one common-clock station (KST 1)
WIRE_SS, WIRE_FF_CREDIT, RCV = 1.135, 0.112, 41.0   # tools/budgets/common.py (receiver repeater 41)
STN = 'dsfd_stnh_512x1'

# slab die port -> [(tile, [tile pins])]; clock pins: slab clock -> tile clock names that map to it
SLABS = {
    'dsfd_ctrl': dict(
        clocks={'cks': ['cks'], 'ckh': ['ckh']},
        ports={'rd': [('dsfd_ctrl_pc', ['r_data', 'r_tag', 'r_beat', 'rv'])],
               'rst': [('dsfd_ctrl_pc', ['rst']), ('dsfd_ctrl_ctr', ['rst'])]},
        # phy (inout, the abutted HBM3E PHY face) stays without arcs, as in the interim model
        glue=[('dsfd_ctrl_pc', 'co_w', 'dsfd_ctrl_pc', 'ci_w', 265.584 - 121.068, 0, 'status chain PC p -> p+1'),
              ('dsfd_ctrl_pc', 'co_w', 'dsfd_ctrl_ctr', 'co_w', 4155.486 - (3983.76 + 121.068), 0, 'PC 15/16 -> ctr')]),
    'dsfd_svc': dict(
        clocks={'ck': ['ck']},
        ports={'ad': [('dsfd_svcio_ad', ['ad'])], 'af': [('dsfd_svcio_ad', ['af'])],
               'od': [('dsfd_svcio_od', ['od'])], 'of': [('dsfd_svcio_od', ['of'])],
               'xd': [('dsfd_svcio_x', ['xd'])], 'xf': [('dsfd_svcio_x', ['xf'])],
               'q': [('dsfd_svcio_q', ['q'])],
               'rd': [('dsfd_svc_pc', ['r_data', 'r_tag', 'r_beat', 'rv'])],
               'rst': [(t, ['rst']) for t in ('dsfd_svc_pc', 'dsfd_svc_stn', 'dsfd_svcio_ad', 'dsfd_svcio_od',
                                              'dsfd_svcio_q', 'dsfd_svcio_x')]},
        glue=[('dsfd_svc_stn', 'q_w', 'dsfd_svc_stn', 'q_e', SVC_HOP, 0, 'quadrant station chain, station -> station'),
              ('dsfd_svc_stn', 'od_ev', 'dsfd_svc_stn', 'od_wv', SVC_HOP, 0, 'od chain, station -> station'),
              ('dsfd_svc_stn', 'od_ed', 'dsfd_svc_stn', 'od_wd', SVC_HOP, 0, 'od chain data'),
              ('dsfd_svc_stn', 'od_wr', 'dsfd_svc_stn', 'od_er', SVC_HOP, 0, 'od chain ready'),
              ('dsfd_svc_stn', 'a0_ev', 'dsfd_svc_stn', 'a0_wv', SVC_HOP, 0, 'a0 chain, station -> station'),
              ('dsfd_svc_stn', 'a0_ed', 'dsfd_svc_stn', 'a0_wd', SVC_HOP, 0, 'a0 chain data'),
              ('dsfd_svc_stn', 'a0_wr', 'dsfd_svc_stn', 'a0_er', SVC_HOP, 0, 'a0 chain ready'),
              ('dsfd_svcio_q', 'q_q', 'dsfd_svc_stn', 'q_e', SVC_HUB, 0, 'IO hub -> first station (q)'),
              ('dsfd_svc_stn', 'od_ed', 'dsfd_svcio_od', 'od_d', SVC_HUB, 0, 'last station -> IO hub (od)'),
              # S81-TAIL 2026-10-08: the valid bit travels the same hub hop as the data (the glue had only od_ed / a0_ed,
              # so od_v / a0_v had no link and kept the fixed 254.7 split: svcio_od od_v R 292.1 -> -37.4 unlinked)
              ('dsfd_svc_stn', 'od_ev', 'dsfd_svcio_od', 'od_v', SVC_HUB, 0, 'last station -> IO hub (od valid)'),
              ('dsfd_svcio_od', 'od_r', 'dsfd_svc_stn', 'od_er', SVC_HUB, 0, 'IO hub ready -> station (od)'),
              ('dsfd_svc_stn', 'a0_ed', 'dsfd_svcio_ad', 'a0_d', SVC_HUB, 0, 'last station -> IO hub (a0)'),
              ('dsfd_svc_stn', 'a0_ev', 'dsfd_svcio_ad', 'a0_v', SVC_HUB, 0, 'last station -> IO hub (a0 valid)'),
              ('dsfd_svcio_ad', 'a0_r', 'dsfd_svc_stn', 'a0_er', SVC_HUB, 0, 'IO hub ready -> station (a0)'),
              ('dsfd_svcio_od', 'bad', 'dsfd_svcio_ad', 'fi', 430.0, 0, 'u_od.bad -> u_ad.fi (fault)')]),
    'dsfd_sp_capture': dict(
        clocks={'ck': ['ck', 'ckv']},
        ports={'f_gather': [('dsfd_capt_g2', ['f_row']), ('dsfd_capt_ctl', ['f_ctl'])],
               't_vm': [('dsfd_capt_x', ['t_vm', 't_st'])],
               'rst': [('dsfd_capt_g2', ['rst']), ('dsfd_capt_ctl', ['rst']), ('dsfd_capt_x', ['rst', 'rsv'])]},
        glue=[('dsfd_capt_ctl', 't_k', STN, 'di0', CAP_S, 1, 'ctl -> S station (t_k)'),
              (STN, 'do0', 'dsfd_capt_g2', 'f_k', CAP_S, 1, 'S station -> group (f_k)'),
              ('dsfd_capt_g2', 't_sb', STN, 'di0', CAP_S, 1, 'group -> S station (t_sb)'),
              (STN, 'do0', 'dsfd_capt_ctl', 'f_sb', CAP_S, 1, 'S station -> ctl (f_sb)'),
              ('dsfd_capt_ctl', 't_sn', STN, 'di0', CAP_S, 1, 'ctl status -> S station (t_sn)'),
              (STN, 'do0', 'dsfd_capt_x', 'f_sn', CAP_S, 1, 'S station -> x tile (f_sn)'),
              ('dsfd_capt_g2', 't_w', 'dsfd_capt_x', 'f_w', 118.8, 0, 'group -> x tile (neighbour)'),
              ('dsfd_capt_x', 't_ho', 'dsfd_capt_g2', 'f_ho', 118.8, 0, 'x tile -> group (neighbour)')]),
    'dsfd_bk_collector': dict(
        clocks={'ck': ['ck']},
        ports={'cSW': [('dsfd_colt_lane', ['c_in'])], 'vd': [('dsfd_colt_mrg', ['vd'])],
               'vf': [('dsfd_colt_mrg', ['vf'])], 'rst': [('dsfd_colt_lane', ['rst']), ('dsfd_colt_mrg', ['rst'])]},
        # 2,970.6 um lane <-> merger, 7 common-clock stations each way: 8 segments of 371.3 um; the stations are the
        # die's common-clock station (closed view dsfd_stnh_512x1: do0 clk->q, di0 setup / hold)
        glue=[('dsfd_colt_lane', 't_w', STN, 'di0', 2970.6 / 8, 7, 'lane -> first station'),
              ('dsfd_colt_lane', 't_f', STN, 'di0', 2970.6 / 8, 7, 'lane -> first station (fwd)'),
              (STN, 'do0', 'dsfd_colt_mrg', 'f_w', 2970.6 / 8, 7, 'last station -> merger'),
              (STN, 'do0', 'dsfd_colt_mrg', 'f_f', 2970.6 / 8, 7, 'last station -> merger (fwd)'),
              ('dsfd_colt_mrg', 't_cr', STN, 'di0', 2970.6 / 8, 7, 'merger credit -> first station'),
              (STN, 'do0', 'dsfd_colt_lane', 'f_cr', 2970.6 / 8, 7, 'last station -> lane credit'),
              (STN, 'do0', STN, 'di0', 2970.6 / 8, 7, 'station -> station')]),
}


def _blocks(s, kw):
    """yield (name, body) for every `kw("name") { ... }` / `kw (name) {` group at any depth"""
    for m in re.finditer(r'\b' + kw + r'\s*\(\s*"?([^")]*)"?\s*\)\s*\{', s):
        i, d = m.end(), 1
        while d:
            c = s[i]
            d += (c == '{') - (c == '}')
            i += 1
        yield m.group(1), s[m.end():i - 1], m.start()


class Lib:
    def __init__(self, path):
        s = path.read_text()
        self.path = path
        self.templates = {n: b for n, b, _ in _blocks(s, 'lu_table_template')}
        self.pins = {}            # bit pin name -> dict(direction, cap, arcs=[dict(related, type, text, worst)])
        for n, b, _ in _blocks(s, 'pin'):
            if n in ('VDD', 'VSS'):
                continue
            d = re.search(r'direction\s*:\s*(\w+)', b).group(1)
            cap = float((re.search(r'\bcapacitance\s*:\s*([\d.]+)', b) or [0, 0])[1])
            arcs = []
            for _, tb, _ in _blocks(b, 'timing'):
                rel = re.search(r'related_pin\s*:\s*"([^"]+)"', tb)
                if not rel:           # clock pins: min / max_clock_tree_path (insertion, already inside the data arcs)
                    continue
                rel = rel.group(1)
                ty = re.search(r'timing_type\s*:\s*(\w+)', tb).group(1)
                # per table (rise / fall): values over the output load index (delays) or scalar (constraints)
                tabs = [[float(x) for x in re.findall(r'-?[\d.]+(?:e-?\d+)?', g)] for g in re.findall(
                    r'(?:cell_rise|cell_fall|rise_constraint|fall_constraint)\s*\([^)]*\)\s*\{[^}]*?values\s*\(([^)]*)\)', tb)]
                tabs = [t for t in tabs if t]
                # vmax / vmin: at the smallest load (a pin driving its first repeater: the glue wire model); vsel at
                # 5.76 fF (index 2), used to pick the worst bit for the die-facing arc
                arcs.append(dict(related=re.sub(r'\[\d+\]$', '', rel), type=ty, text=tb,
                                 vmax=max((t[0] for t in tabs), default=0.0), vmin=min((t[0] for t in tabs), default=0.0),
                                 vsel=max((t[min(2, len(t) - 1)] for t in tabs), default=0.0),
                                 vsel_min=min((t[min(2, len(t) - 1)] for t in tabs), default=0.0)))
            self.pins[n] = dict(direction=d, cap=cap, arcs=arcs)

    def bits(self, base):
        return [n for n in self.pins if re.sub(r'\[\d+\]$', '', n) == base]


def lib_for(tile, corner):
    d = TILES / tile if (TILES / tile).exists() else ROOT / 'physical/s81_die_views/views' / tile   # die station view
    p = d / f'{tile}_{corner}.lib'
    if p.exists():
        return p, False
    return d / f'{tile}_ss.lib', True       # tile without a TT extraction: its SS ETM (pessimistic, marked)


def worst_arcs(libs, srcs, corner, clockmap):
    """per (timing_type, slab clock): the worst arc over every bit of every source tile pin"""
    best = {}
    for tile, pins in srcs:
        L = libs[tile]
        for p in pins:
            for b in L.bits(p):
                for a in L.pins[b]['arcs']:
                    ck = clockmap.get(a['related'])
                    if ck is None:
                        continue
                    k = (a['type'], ck)
                    use_min = corner == 'ff' and a['type'] in ('rising_edge', 'falling_edge', 'combinational')
                    score = -a['vsel_min'] if use_min else a['vsel']
                    if k not in best or score > best[k][0]:
                        best[k] = (score, a, tile, b)
    return best


def assemble(slab, spec, ports, corner):
    """ports: slab die port -> (direction, width) from the die generator.  Returns (lib text, record)"""
    tiles = sorted({t for v in spec['ports'].values() for t, _ in v})
    libs, ss_as = {}, []
    for t in tiles:
        p, fb = lib_for(t, corner)
        libs[t] = Lib(p)
        if fb:
            ss_as.append(t)
    clockmap = {tc: sc for sc, tcs in spec['clocks'].items() for tc in tcs}
    name = f'{slab}_asm_{corner}'
    L = [f'library ({name}) {{', ' delay_model : table_lookup;', ' time_unit : "1ps";', ' voltage_unit : "1V";',
         ' current_unit : "1mA";', ' pulling_resistance_unit : "1kohm";', ' leakage_power_unit : "1pW";',
         ' capacitive_load_unit (1, ff);', ' nom_process : 1.0;', ' nom_temperature : 25.0;', ' nom_voltage : 0.70;',
         ' input_threshold_pct_rise : 50; input_threshold_pct_fall : 50; output_threshold_pct_rise : 50;',
         ' output_threshold_pct_fall : 50; slew_lower_threshold_pct_rise : 10; slew_lower_threshold_pct_fall : 10;',
         ' slew_upper_threshold_pct_rise : 90; slew_upper_threshold_pct_fall : 90;']
    for t in tiles:
        for tn, tb in libs[t].templates.items():
            L.append(f' lu_table_template ({t}__{tn}) {{{tb}}}')
    for w in sorted({w for _, w in ports.values()}):
        L.append(f' type (b{w}) {{ base_type : array; data_type : bit; bit_width : {w}; bit_from : {w - 1}; bit_to : 0; '
                 'downto : true; }')
    L.append(f' cell ({slab}) {{')
    rec = dict(ports={}, tiles_ss_as_tt=ss_as, libs={t: str(libs[t].path.relative_to(ROOT)) for t in tiles})
    for p, (d, w) in sorted(ports.items()):
        L.append(f'  bus ({p}) {{ bus_type : b{w}; direction : {d};')
        if p in spec['clocks']:
            L.append('   clock : true; capacitance : 1.0;')
        elif p in spec['ports']:
            best = worst_arcs(libs, spec['ports'][p], corner, clockmap)
            caps = [libs[t].pins[b]['cap'] for t, ps in spec['ports'][p] for pp in ps for b in libs[t].bits(pp)]
            if d == 'input':
                L.append(f'   capacitance : {max(caps or [1.0]):.4f};')
            arcs = {}
            for (ty, ck), (_, a, t, b) in sorted(best.items()):
                txt = re.sub(r'related_pin\s*:\s*"[^"]+"', f'related_pin : "{ck}"', a['text'])
                for tn in libs[t].templates:
                    txt = re.sub(r'\(\s*' + re.escape(tn) + r'\s*\)', f'({t}__{tn})', txt)
                L.append(f'   timing () {{{txt}}}')
                arcs[f'{ty}/{ck}'] = dict(tile=t, bit=b, ps_at_5p76fF=round(a['vsel_min'] if (corner == 'ff' and ty.endswith('edge')) else a['vsel'], 1))
            rec['ports'][p] = arcs
        else:
            rec['ports'][p] = 'no arcs (as interim)'
        L.append('  }')
    L += [' }', '}']
    return '\n'.join(L) + '\n', rec


def arc_of(lib, pin, kind, corner):
    """worst constraint / clk->q of a tile pin (all bits): kind 'cq' (max at ss/tt, min at ff), 'su', 'ho'"""
    v = []
    for b in lib.bits(pin):
        for a in lib.pins[b]['arcs']:
            if kind == 'cq' and a['type'] in ('rising_edge', 'falling_edge'):
                v.append(a['vmin'] if corner == 'ff' else a['vmax'])
            elif kind == 'su' and a['type'].startswith('setup'):
                v.append(a['vmax'])
            elif kind == 'ho' and a['type'].startswith('hold'):
                v.append(a['vmax'])
    if not v:
        return None
    return min(v) if (kind == 'cq' and corner == 'ff') else max(v)


def glue_checks(spec):
    """flop-to-flop inter-tile hops of the slab: setup at TT and SS, hold at FF"""
    out = []
    cache = {}

    def L(t, c):
        if (t, c) not in cache:
            cache[(t, c)] = Lib(lib_for(t, c)[0])
        return cache[(t, c)]
    def tt_ratio(t):
        # TT / SS buffered-wire delay ratio, measured on the tile's own routed clock tree (a repeater chain):
        # max_clock_tree_path TT / SS of the tile ETMs
        v = []
        for c in ('tt', 'ss'):
            p, fb = lib_for(t, c)
            m = re.search(r'max_clock_tree_path;\s*cell_rise\(scalar\)\s*\{\s*values\("([\d.]+)', p.read_text())
            v.append(float(m.group(1)) if m and not fb else None)
        return v[0] / v[1] if None not in v else 1.0
    def ins(t, c, kind='max'):
        p, _ = lib_for(t, c)
        m = re.search(kind + r'_clock_tree_path;\s*cell_rise\(scalar\)\s*\{\s*values\("([\d.]+)', p.read_text())
        return float(m.group(1)) if m else 0.0
    for lt, lp, ct, cp, um, stn, what in spec['glue']:
        rt = tt_ratio(lt)
        r = dict(tt_wire_ratio=round(rt, 3), what=what, launch=f'{lt}.{lp}', capture=f'{ct}.{cp}',
                 length_um=round(um, 1), stations=stn)
        for c in ('tt', 'ss'):
            cq = arc_of(L(lt, c), lp, 'cq', c)
            su = arc_of(L(ct, c), cp, 'su', c)
            if cq is None or su is None:
                r[f'{c}_setup'] = f'missing arc (cq {cq}, setup {su})'
                continue
            w = WIRE_SS * (rt if c == 'tt' else 1.0)
            r[f'{c}_setup'] = round(T_PS - UNC_S - SKEW_INTRA - (cq + w * um + RCV + su), 1)
            # balanced: the die tree delivers each tile's clock early by its own routed insertion (flop arrival equal)
            r[f'{c}_setup_bal'] = round(r[f'{c}_setup'] + ins(lt, c) - ins(ct, c), 1)
        cq = arc_of(L(lt, 'ff'), lp, 'cq', 'ff')
        ho = arc_of(L(ct, 'ff'), cp, 'ho', 'ff')
        r['ff_hold'] = (round(cq + WIRE_FF_CREDIT * um - ho - UNC_H, 1) if cq is not None and ho is not None
                        else f'missing arc (cq {cq}, hold {ho})')
        if isinstance(r['ff_hold'], float):
            r['ff_hold_bal'] = round(r['ff_hold'] - ins(lt, 'ff', 'min') + ins(ct, 'ff', 'min'), 1)
        out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--glue-only', action='store_true', help='recompute only the glue of existing <out>/<slab>/assembled.json '
                    '(tiles unchanged: the libs stay)')
    ap.add_argument('--ports', type=Path,
                    help='JSON {slab: {port: [direction, width]}} (die_sta.py kit --ports-out)')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    summ = {}
    if a.glue_only:
        for slab, spec in SLABS.items():
            f = a.out / slab / 'assembled.json'
            rec = json.loads(f.read_text())
            g = glue_checks(spec)
            rec.update(glue=g, glue_worst_ps={k: min((x[k] for x in g if isinstance(x.get(k), float)), default=None)
                                             for k in ('tt_setup', 'ss_setup', 'ff_hold', 'tt_setup_bal', 'ss_setup_bal', 'ff_hold_bal')})
            f.write_text(json.dumps(rec, indent=1) + '\n')
            print(slab, json.dumps(rec['glue_worst_ps']))
        return
    P = json.loads(a.ports.read_text())
    for slab, spec in SLABS.items():
        d = a.out / slab
        d.mkdir(parents=True, exist_ok=True)
        ports = {k: tuple(v) for k, v in P[slab].items()}
        rec = dict(slab=slab, method=__doc__.split('\n\n')[1].replace('\n', ' '), corners={})
        for c in ('ss', 'tt', 'ff'):
            txt, r = assemble(slab, spec, ports, c)
            (d / f'{slab}_{c}.lib').write_text(txt)
            rec['corners'][c] = r
        g = glue_checks(spec)
        rec['glue'] = g
        worst = {k: min((x[k] for x in g if isinstance(x.get(k), float)), default=None)
                 for k in ('tt_setup', 'ss_setup', 'ff_hold', 'tt_setup_bal', 'ss_setup_bal', 'ff_hold_bal')}
        rec['glue_worst_ps'] = worst
        (d / 'assembled.json').write_text(json.dumps(rec, indent=1) + '\n')
        summ[slab] = dict(glue_worst_ps=worst, ss_as_tt=rec['corners']['tt']['tiles_ss_as_tt'])
        print(slab, json.dumps(summ[slab]))
    (a.out / 'summary.json').write_text(json.dumps(summ, indent=1) + '\n')


if __name__ == '__main__':
    main()
