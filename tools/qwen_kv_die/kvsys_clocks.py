#!/usr/bin/env python3
"""qwen-split/kvsys v1.1 (2026-10-14): insertion-compensated (phi - R) die clocks for the KV/system die STA.

Every CTS sink pin of the die case (a pin of a clock net n_clk_core_* / n_clk_hbm_*) becomes a clock source point with
source latency -R, R = the bound view's measured boundary-mean insertion (insertion.json, per corner; the owner die clock
delivery rule 10-13: the die delivers the clock at each tile's clock pin at phi - R).  Masters without a closed view
(frames, relays, per-child entries of a wires-only parent) are explicit ideal zero-insertion assumptions.  Each child
clock entry of a wires-only parent frame (qkd_ectl ck_a/b/c, qkd_rhead ck_f/k/s/t*/l*) is its OWN sink point, so a
measured child view later enters with its own R without a die change.  Budgets: tools/qwen_tp8/die_sta_libs.clock_tcl
(setup 60 + 90 ps skew, 150 when either end has TT R > 300 ps; hold H1 100 ps).

    kvsys_clocks.py --case CASE --views LIBS/views.json --out LIBS
writes LIBS/clocks_<c>.tcl (c = tt ff ss) for sta_tcl.py (OT_STA_CLOCKS=LIBS/clocks_{corner}.tcl) and LIBS/clocks.json.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_kv_die'))
import qwen_die_element_lib as E   # noqa: E402
from qwen_tp8.die_sta_libs import clock_tcl, measured_clock_refs   # noqa: E402
import kv_die as K   # noqa: E402

CORNERS = ('tt', 'ff', 'ss')


def domain(net):
    n = net[2:] if net.startswith('n_') else net
    m = re.match(r'clk_hbm_(\w+?)(?:__.*)?$', n)
    if m:
        return 'hclk_' + m.group(1)
    if n.startswith('clk_core_'):
        return 'stream'
    for family in ('host', 'ingest', 'phy'):
        if n == 'clk_' + family or n.startswith('clk_' + family + '_'):
            return family
    raise ValueError(f'unknown actual KV clock family: {net}')


def periods_for(doms):
    # ns analog-model half periods -> full periods in ps. HOST PHY1043
    # differs from native UCIe, whose FDI shares the core833.334 family.
    text=(ROOT/'rtl/qwen_sys/split_20261014/qkd_pll_analog_model.sv').read_text()
    halves={name:float(value) for name,value in re.findall(r'\b(CORE_HALF|HBM_HALF|HOST_HALF|ING_HALF|PHY_HALF)\s*=\s*([0-9.]+)',text)}
    expected={'stream':'CORE_HALF','host':'HOST_HALF','ingest':'ING_HALF','phy':'PHY_HALF'}
    return {d:round(2000.0*halves['HBM_HALF' if d.startswith('hclk_') else expected[d]], 6) for d in doms}



def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--case', type=Path, required=True)
    ap.add_argument('--views', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(argv)
    K._set_geometry(True)
    views = json.loads(a.views.read_text())['views']
    leaves, src = {}, {}
    for mst, r in views.items():
        if not r.get('bound'):
            continue
        vd = ROOT / r['view']
        # v1.3: a die-placed leaf (kv_expand.py) is instantiated under its own module name with its RTL pins: identity
        b = K.BINDINGS[mst] if not r.get('expanded_from') else None
        per = {}
        for c in CORNERS:
            lib = next(vd.glob(f'*_{c}.lib'), None)
            if lib is None:
                continue
            try:
                refs = measured_clock_refs(lib, vd / 'insertion.json', c)
            except ValueError:
                if c == 'ss':
                    continue          # SS: sensitivity only; a view without an SS boundary measurement skips it
                raise
            for rpin, rr in refs.items():
                if b is None:
                    per.setdefault(c, {})[rpin] = rr
                    per[c][f'{rpin}[0]'] = rr
                    continue
                dps = [dp for dp, ps in b['ports'].items() if rpin in ps]
                if len(dps) != 1:
                    raise ValueError(f'{mst}: clock pin {rpin} binds to {dps}')
                per.setdefault(c, {})[f'{dps[0]}[0]'] = rr
        leaves[mst] = per
        src[mst] = dict(view=r['view'], R_ps={c: v for c, v in per.items()})
    # pin names as the case LEFs draw them: generated frames / bound views 'p[0]', the real PHY abstract scalar 'clk'
    lefpins = {}
    for f in [a.case / 'elements.lef'] + sorted(a.case.glob('phy*.lef')):
        cur = None
        for ln in open(f):
            t = ln.split()
            if t[:1] == ['MACRO']:
                cur = t[1]
            elif t[:1] == ['PIN'] and cur:
                lefpins.setdefault(cur, set()).add(t[1])
    txt = (a.case / 'die.v').read_text()
    doms, sinks = {}, 0
    for m in re.finditer(r'^\s+(\w+) (\S+) \((.*?)\);', txt, re.M):
        mst, inst, body = m.group(1), m.group(2), m.group(3)
        if mst in ('wire', 'module'):
            continue
        for p in re.finditer(r'\.(\S+?)\(([^(){}]*)\)', body):
            port, net = p.group(1).lstrip('\\').strip(), p.group(2).strip()
            if not net.startswith('n_clk_') or port.startswith('pll'):
                continue          # pll_* = the clock SOURCE pins (PLL / HBM controller PLL outputs), not sinks
            pin = port if port in lefpins.get(mst, ()) else f'{port}[0]'
            if mst in src:
                if pin not in leaves[mst].get('tt', {}):
                    raise ValueError(f'{inst}/{pin}: bound view {mst} has no measured clock pin {pin}')
            else:
                if port not in E.CLOCKS and not mst.startswith('ot_'):
                    raise ValueError(f'{inst}/{port}: clock net {net} on a non-clock port')
                leaves.setdefault(mst, {c: {} for c in CORNERS})
                for c in CORNERS:
                    leaves[mst][c][pin] = 0.0
            doms.setdefault(domain(net), []).append((f'{inst}/{pin}', mst, pin))
            sinks += 1
    a.out.mkdir(parents=True, exist_ok=True)
    for c in CORNERS:
        if all(c in leaves[m_] for m_ in leaves):
            (a.out / f'clocks_{c}.tcl').write_text(clock_tcl(doms, leaves, c, periods=periods_for(doms)))
    rec = dict(schema='opentallas.qwen_kvsys_clocks.v1', sinks=sinks, domains={d: len(v) for d, v in doms.items()},
               source_periods_ps=periods_for(doms), period_source='qkd_pll_analog_model real half-periods; no implicit domain fallback',
               measured=src, assumed_ideal=sorted(m_ for m_ in leaves if m_ not in src),
               per_child_entries=dict(qkd_ectl=K.ECTL_CLK, qkd_rhead=K.HEAD_CLK, qkd_ahub=K.AHUB_CLK, qkd_land=K.KS.LAND_CLK,
                                      qkd_astk=K.KS.ASTK_CLK),
               rule='phi - R per sink, R = insertion.json boundary mean of the bound view (per corner); frames ideal (R 0)')
    (a.out / 'clocks.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({k: rec[k] for k in ('sinks', 'domains')} | dict(measured=list(src))))


if __name__ == '__main__':
    main()
