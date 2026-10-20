#!/usr/bin/env python3
"""S81-LAND landing bench driver (rtl/dsrom_sys/s81_dv/land/test/tb_s81_land.sv, iverilog).

Skew sweep: four lane geometries whose nominal forwarded-clock lag dL = (N + 1) * DH - LR sits at 0 (phase wrap),
T/2, T (one cycle of age: wrap) and 2T (16-hop lane, wrap); each is swept +-80 ps (the neighbour skew budget) by moving
the block root insertion LR.  The compiler picks ONE K per geometry from its nominal dL (window rule of
LANDING-CONTRACT.md: E = ceil((dL + 80 + margin) / T), K = E + G - R0); every sweep point must deliver the exact word
stream at the predicted compile-time latency N + 1 + E with fault 0.  A calendar slip (gate opened one edge late) must
raise fault.  Mutants: NAIVE (bounded-skew retime register without the ring: latency follows the phase) and SEL (read
slot one late) must FAIL.

  python3 tools/s81_dv/land_bench.py [--out results/arch/s81_dv_1016/landing/bench.json] [--widths 70 276]

S81-DIE7/LAND (10-18) tile mode, the kit benches of the hardened landing tiles: the bench drives the tile's own top
(dsfd_dvland_<W> D 4 / dsfd_dvland_276l D 8 long geometries) and runs ONE variant; the last line is
"LAND_BENCH PASS|FAIL <top> <variant> ..." = that variant's own verdict (a mutant must print FAIL), exit 0 on PASS.
  python3 tools/s81_dv/land_bench.py --tile dsfd_dvland_276 --variant base --out RUN/bench.json

PO-SUBMIT (10-19, COORD HANDOFF 0jz) --rst-land N: the kit's reset landing (ref_tile reset_landing {"enable": true,
"stages": N}: N plain ck flops on rs in front of the core) is modelled in the bench (tb +RL=N); the core release moves
from R0 to R0 + N and the re-derived die calendar (dv_bind landing_reset_stages) opens the hop-0 gate N edges later,
so K and the data latency are unchanged.  Variant mut_rlcal keeps the OLD gate edge (uncompensated calendar) and must
FAIL (latency off by N against the compiler's prediction).
"""
import argparse, json, math, re, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
TB = ROOT / 'rtl/dsrom_sys/s81_dv/land/test/tb_s81_land.sv'
DUT = ROOT / 'rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv'
WRAP = ROOT / 'rtl/dsrom_sys/s81_dv/land/dsfd_dvland.sv'
T, D, R0, G, MARGIN, SKEW = 834, 4, 4, 6, 100, 80
GEOM = [dict(name='dL0_wrap', N=0, DH=100, LR=100), dict(name='dL_halfT', N=3, DH=135, LR=140),
        dict(name='dL_T_wrap_age1', N=6, DH=131, LR=83), dict(name='dL_2T_wrap_16hop', N=15, DH=115, LR=172)]
SWEEP = list(range(-SKEW, SKEW + 1, 20))
# LANDFIX-SQ (10-18) --long: dsfd_dvland_276l (D 8, 6-bit K) on the p4l long lanes; each geometry is swept over its
# measured TT/FF arrival spread (p4l land plan S1 tt - ff, +-half) instead of the +-80 ps neighbour budget.
# LR >= SK + 100 (the sweep moves LR by +-SK; a negative insertion is not a delay).  Long-mode slip test: the hop-0 gate
# opens SLIP_N edges late, SLIP_N = the fewest edges that push the nominal arrival past the window's late edge E T: inside
# the 8-T window a 1-edge slip is self-consistent (the ring absorbs it, latency +1) and the epoch check cannot see it --
# gate slips are the static reset calendar's check; the tile's fault covers window violations.
GEOM_LONG = [dict(name='host_hf_ht_60hop_E28', N=59, DH=405, LR=2400, SK=2300),
             dict(name='seqhost_jw_jd_33hop_E16', N=32, DH=420, LR=1400, SK=1300),
             dict(name='seqhost_cw_23hop_E12', N=22, DH=420, LR=1000, SK=900),
             dict(name='xtier_tv_16hop_E9', N=15, DH=420, LR=800, SK=700)]


def pick_k(dl, skew=SKEW, d=None):
    d = d or D
    e = math.ceil((dl + skew + MARGIN) / T)
    assert dl - skew > (e - d) * T + MARGIN, 'window too narrow for this dL spread'
    return e, e + G - R0


def run(binary, args):
    out = subprocess.run(['vvp', '-n', binary] + [f'+{k}={v}' for k, v in args.items()], capture_output=True, text=True).stdout
    m = re.search(r'OT_LAND (.*)', out)
    return {k: int(v) for k, v in (kv.split('=') for kv in m.group(1).split())} if m else {'error': out[-400:]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=ROOT / 'results/arch/s81_dv_1016/landing/bench.json')
    ap.add_argument('--widths', type=int, nargs='+', default=[70, 276])
    ap.add_argument('--long', action='store_true', help='dsfd_dvland_276l: D 8, KW 6, long-lane geometries (GEOM_LONG)')
    ap.add_argument('--tile', help='S81-DIE7/LAND: drive this hardened tile top (dsfd_dvland_<W> or dsfd_dvland_276l)')
    ap.add_argument('--variant', choices=['base', 'mut_naive', 'mut_sel', 'mut_rlcal'], help='tile mode: run only this variant')
    ap.add_argument('--rst-land', type=int, default=0, help='kit reset landing stages on rs (ref_tile reset_landing.stages)')
    a = ap.parse_args()
    if a.tile:
        m = re.fullmatch(r'dsfd_dvland_(\d+)(l?)', a.tile)
        assert m, f'--tile {a.tile}: not a dsfd_dvland_<W>[l] top'
        a.widths, a.long = [int(m.group(1))], bool(m.group(2))
    d_, kw, nmax, geoms = (8, 6, 64, GEOM_LONG) if a.long else (D, 3, 16, GEOM)
    if a.long and not a.tile:
        a.widths = [276]
    tmp = a.out.parent if a.tile else Path(tempfile.mkdtemp(prefix='s81land_'))
    tmp.mkdir(parents=True, exist_ok=True)
    res = dict(schema='opentallas.s81_land.bench.v1', tb=str(TB.relative_to(ROOT)), dut=str(DUT.relative_to(ROOT)),
               T_ps=T, D=d_, KW=kw, R0=R0, G=G, margin_ps=MARGIN, skew_sweep_ps=SWEEP if not a.long else 'per geometry +-SK, 9 points',
               geometries=geoms, variants={}, rst_land_stages=a.rst_land,
               calendar='re-derived: core release R0 + rst_land, hop-0 gate G + rst_land (K, latency unchanged)' if a.rst_land else 'R0 / G')
    verdict = True
    if a.tile:
        res.update(tile=a.tile, wrapper=str(WRAP.relative_to(ROOT)))
    assert 0 <= a.rst_land <= 8, '--rst-land: 0..8 stages'
    if a.variant == 'mut_rlcal':
        assert a.rst_land > 0, 'mut_rlcal needs --rst-land > 0'
    for var, define in (('base', None), ('mut_naive', 'OT_S81_LAND_MUT_NAIVE'), ('mut_sel', 'OT_S81_LAND_MUT_SEL'), ('mut_rlcal', None)):
        if a.variant and var != a.variant:
            continue
        if var == 'mut_rlcal' and not a.rst_land:
            continue
        rla = dict(RL=a.rst_land, GS=(0 if var == 'mut_rlcal' else a.rst_land))
        vr = dict(runs=[], expect='PASS' if var == 'base' else 'FAIL')
        for w in a.widths:
            b = tmp / f'{var}_{w}'
            cmd = ['iverilog', '-g2012', f'-DTB_W={w}', f'-DTB_D={d_}', f'-DTB_KW={kw}', f'-DTB_NMAX={nmax}', '-o', str(b), str(TB),
                   str(DUT)] + ([f'-D{define}'] if define else []) + ([f'-DTB_TOP={a.tile}', str(WRAP)] if a.tile else [])
            subprocess.run(cmd, check=True)
            for g in geoms:
                dl0 = (g['N'] + 1) * g['DH'] - g['LR']
                sk = g.get('SK', SKEW)
                e, k = pick_k(dl0, sk, d_)
                cyc = {} if not a.long else dict(CYC=320)
                for s in (SWEEP if not a.long else [round(sk * (i - 4) / 4) for i in range(9)]):
                    r = run(str(b), dict(N=g['N'], DH=g['DH'], LR=g['LR'] - s, K=k, R0=R0, G=G, **rla, **cyc))
                    r.update(geom=g['name'], E=e, ok=(r.get('mism', 1) == 0 and r.get('fault', 1) == 0 and r.get('meas') == r.get('pred')))
                    vr['runs'].append(r)
                slip = 1 if not a.long else (e * T - dl0) // T + 1
                r = run(str(b), dict(N=g['N'], DH=g['DH'], LR=g['LR'], K=k, R0=R0, G=G, SLIP=slip, **rla, **cyc))   # calendar slip
                r.update(geom=g['name'], E=e, slip_test=True, ok=(r.get('fault') == 1))
                vr['runs'].append(r)
        sweep = [r for r in vr['runs'] if not r.get('slip_test')]
        vr['sweep_pass'] = sum(r['ok'] for r in sweep); vr['sweep_runs'] = len(sweep)
        vr['slip_fault_raised'] = sum(r['ok'] for r in vr['runs'] if r.get('slip_test'))
        vr['latency_by_geom'] = {}
        for r in sweep:
            vr['latency_by_geom'].setdefault(f"{r['geom']}/w{r['w']}", set()).add(r.get('meas'))
        vr['latency_by_geom'] = {k: sorted(v) for k, v in vr['latency_by_geom'].items()}
        passed = vr['sweep_pass'] == vr['sweep_runs'] and vr['slip_fault_raised'] == len(geoms) * len(a.widths)
        vr['verdict'] = 'PASS' if passed else 'FAIL'
        verdict &= (vr['verdict'] == vr['expect'])
        res['variants'][var] = vr
        print(var, vr['verdict'], f"sweep {vr['sweep_pass']}/{vr['sweep_runs']} slip-fault {vr['slip_fault_raised']}", vr['latency_by_geom'])
    res['verdict'] = 'PASS' if verdict else 'FAIL'
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=1) + '\n')
    print('BENCH', res['verdict'], a.out)
    if a.tile:   # tile mode: the one variant's own verdict (a mutant prints FAIL)
        vr = res['variants'][a.variant or 'base']
        print(f"LAND_BENCH {vr['verdict']} {a.tile} {a.variant or 'base'} D={d_} KW={kw} sweep {vr['sweep_pass']}/{vr['sweep_runs']} "
              f"slip-fault {vr['slip_fault_raised']}/{len(geoms)} latency {vr['latency_by_geom']}")
        raise SystemExit(0 if vr['verdict'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
