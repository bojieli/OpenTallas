#!/usr/bin/env python3
"""el1013-lkep-split: specs + exact pin files of the ot_lkep_sub partition (wires-only parent over the closed retry macro
and three M5 leaves, one clock entry per child).  Run in the repo root:  python3 physical/ref_tile_specs/lkep/mk_lkep_split.py

Frame (um, sub 842.4 x 518.4; every origin on the 2.16 lattice, the macro on 43.2 because it has M6 pins):
  macro u_rp  (216.0, 129.6) 501.12 x 300.24   W = in, S = tx, N = rx, E = out / ack / fb / status
  ti    u_ti  ( 21.6, 151.2) W of the macro: E face = the macro W pins at their own y (M4), S face = the sub S pins
  ts    u_ts  (237.6,  82.08) under the macro: N face = the macro S pins at their own x (M5), S face = the sub S pins
  rp    u_rq  (432.0, 453.6) above the macro: S face = the macro N pins at their own x + the macro E-face buses (which
              leave E and turn N in the 125-um E channel), N face = the sub N pins
Every macro-facing leaf pin sits on the track of the macro pin it meets (a straight wire across a 21.6-um gap); M5 pins
keep off the leaf's own M5 PG stripes (pair every 5.4 um).  Sub pins are the leaf pins dropped straight to the face.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SD = Path(__file__).resolve().parent
MACRO_VIEW = 'physical/ref_tile/hbm_retry545_ref/views/ot_hbm_link_retry_pipeline'
SUB = (842.4, 518.4)
MX, MY = 216.0, 129.6
LEAF = dict(ti=dict(top='ot_lkep_ti', at=(21.6, 151.2), wh=(172.8, 151.2)),
            ts=dict(top='ot_lkep_ts', at=(237.6, 82.08), wh=(237.6, 25.92)),
            rp=dict(top='ot_lkep_rp', at=(432.0, 453.6), wh=(386.64, 34.56)))
W, SW, EW, QD, NSL = 545, 12, 24, 16, 9
TW = W + SW + EW
SRC = ['rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv', 'rtl/hbm_accel/tu/lk_ep_20261010/ot_crc_par.sv',
       'rtl/hbm_accel/tu/lk_ep_20261010/ot_hbm_lk_ep.sv', 'rtl/hbm_accel/tu/lk_ep_20261010/ot_lkep_sub.sv']
T = 0.048                                   # M4 / M5 track pitch; tracks at 0.012 + 0.048 k in any frame on the 2.16 lattice


def trk(v):
    return round(0.012 + T * round((v - 0.012) / T), 4)


def pg_blocked(x):
    """leaf M5 PG pair: stripes 0.12 wide, 0.072 apart, pitch 5.4, first pair at core x0 (2.16) + 0.30"""
    r = (x - 2.16 - 0.30) % 5.4
    return r < 0.312 + 0.20 or r > 5.4 - 0.20


def bus(n, w):
    return [f'{n}[{i}]' for i in range(w)] if w > 1 else [n]


def lef_pins(lef):
    wd = ht = None; pins = {}; cur = ly = None; use = 'SIGNAL'
    for ln in Path(lef).read_text().splitlines():
        t = ln.split()
        if not t: continue
        if t[0] == 'SIZE': wd, ht = float(t[1]), float(t[3])
        elif t[0] == 'PIN': cur, ly, use = t[1], None, 'SIGNAL'
        elif t[0] == 'USE' and cur: use = t[1]
        elif t[0] == 'LAYER' and cur: ly = t[1]
        elif t[0] == 'RECT' and cur and cur not in pins and use == 'SIGNAL':
            x0, y0, x1, y1 = map(float, t[1:5]); pins[cur] = (ly, (x0 + x1) / 2, (y0 + y1) / 2)
        elif t[0] == 'OBS' or (t[0] == 'END' and len(t) > 1 and t[1] == cur): cur = None
    return wd, ht, pins


class Face:
    """pins of one leaf: face -> {name: coordinate along the face}; one track per pin, M5 pins off the PG stripes"""
    def __init__(self, wh):
        self.wh = wh; self.p = {f: {} for f in 'NSEW'}; self.used = {f: set() for f in 'NSEW'}

    def free(self, f, v):
        k = round((v - 0.012) / T)
        lim = self.wh[0] if f in 'NS' else self.wh[1]
        return 2.5 < v < lim - 2.5 and k not in self.used[f] and k - 1 not in self.used[f] and k + 1 not in self.used[f] \
            and not (f in 'NS' and pg_blocked(v))

    def put(self, f, name, v):
        """nearest free track to v (macro-aligned pin)"""
        v0 = trk(v)
        for d in range(0, 400):
            for sgn in (1, -1):
                c = round(v0 + sgn * d * T, 4)
                if self.free(f, c):
                    self.p[f][name] = c; self.used[f].add(round((c - 0.012) / T)); return abs(c - v)
        raise SystemExit(f'no track for {name} on {f} near {v}')

    def run(self, f, names, lo, step=2):
        """names in order from lo upward, at least `step` tracks apart"""
        c = trk(lo)
        for n in names:
            while not self.free(f, c):
                lim = self.wh[0] if f in 'NS' else self.wh[1]
                if c >= lim - 2.5:
                    raise SystemExit(f'face {f} {self.wh} exhausted at {n}, allocated {len(self.p[f])} pins')
                c = round(c + T, 4)
            self.p[f][n] = c; self.used[f].add(round((c - 0.012) / T)); c = round(c + step * T, 4)
        return c

    def tcl(self, head):
        w, h = self.wh; L = [head]
        for f in 'SNWE':
            for n, c in sorted(self.p[f].items(), key=lambda t: t[1]):
                if f in 'NS':
                    L.append(f'place_pin -pin_name {{{n}}} -layer M5 -location {{{c:.4f} {0.0 if f == "S" else h:.4f}}} -pin_size {{0.024 0.192}} -force_to_die_boundary')
                else:
                    L.append(f'place_pin -pin_name {{{n}}} -layer M4 -location {{{0.0 if f == "W" else w:.4f} {c:.4f}}} -pin_size {{0.192 0.024}} -force_to_die_boundary')
        return '\n'.join(L) + '\n'


def main():
    mw, mh, mp = lef_pins(ROOT / MACRO_VIEW / 'ot_hbm_link_retry_pipeline.lef')
    assert (mw, mh) == (501.12, 300.24)
    mabs = {n: (ly, MX + x, MY + y) for n, (ly, x, y) in mp.items()}

    def mface(names):
        return [(n, mabs[n]) for n in names]
    F = {k: Face(v['wh']) for k, v in LEAF.items()}
    jog = {}
    # ---- ti: macro W face on its E face (M4, same y), sub S pins on its S face
    ox, oy = LEAF['ti']['at']
    mapw = [('in_valid', 'm_in_v')] + [(f'in_data[{i}]', f'm_in_d[{i}]') for i in range(W)] + [('in_ready', 'm_in_r'), ('rst_n', 'm_rst_n')] + \
           [(f'session[{i}]', f'm_session[{i}]') for i in range(EW)]
    jog['ti.E'] = max(F['ti'].put('E', ln, mabs[mn][2] - oy) for mn, ln in sorted(mapw, key=lambda t: mabs[t[0]][2]))
    ti_s = bus('w_d', W) + bus('w_oh', NSL * QD) + ['adm', 'icr_ret'] + bus('session', EW) + ['rst_n', 'clk']
    F['ti'].run('S', ti_s, 10.0)
    # ---- ts: macro S face on its N face (M5, same x), sub S pins straight below where the track is free
    ox, oy = LEAF['ts']['at']
    maps = [('tx_valid', 'm_tx_v'), ('tx_ready', 'm_tx_r')] + [(f'tx_data[{i}]', f'm_tx_d[{i}]') for i in range(W)] + \
           [(f'tx_seq[{i}]', f'm_tx_s[{i}]') for i in range(SW)] + [(f'tx_session[{i}]', f'm_tx_e[{i}]') for i in range(EW)]
    jog['ts.N'] = max(F['ts'].put('N', ln, mabs[mn][1] - ox) for mn, ln in sorted(maps, key=lambda t: mabs[t[0]][1]))
    F['ts'].run('S', ['tx_v'] + bus('tx_d', TW) + ['tx_cr', 'rst_n', 'clk'], 60.0)
    # ---- rp: macro N face on its S face (same x); the macro E-face buses on its S face over the E channel; sub N pins
    ox, oy = LEAF['rp']['at']
    mapn = [('rx_valid', 'm_rx_v'), ('rx_ready', 'm_rx_r'), ('rx_ue', 'm_rx_ue')] + [(f'rx_data[{i}]', f'm_rx_w[{i}]') for i in range(W)] + \
           [(f'rx_seq[{i}]', f'm_rx_w[{W + i}]') for i in range(SW)] + [(f'rx_session[{i}]', f'm_rx_w[{W + SW + i}]') for i in range(EW)]
    jog['rp.S'] = max(F['rp'].put('S', ln, mabs[mn][1] - ox) for mn, ln in sorted(mapn, key=lambda t: mabs[t[0]][1]))
    mape = [('out_valid', 'm_out_v'), ('out_ready', 'm_out_r')] + [(f'out_data[{i}]', f'm_out_d[{i}]') for i in range(W)] + \
           [(f'ack_seq[{i}]', f'm_ack_s[{i}]') for i in range(SW)] + [('ack_nak', 'm_ack_n')] + [(f'ack_session[{i}]', f'm_ack_e[{i}]') for i in range(EW)] + \
           [('fb_valid', 'm_fb_v'), ('fb_good', 'm_fb_good'), ('fb_nak', 'm_fb_n')] + [(f'fb_seq[{i}]', f'm_fb_s[{i}]') for i in range(SW)] + \
           [(f'fb_session[{i}]', f'm_fb_e[{i}]') for i in range(EW)] + [('fault', 'm_fault')] + [(f'replay_count[{i}]', f'm_rep[{i}]') for i in range(32)]
    # lowest macro pin -> the track nearest the macro (the inner L), so the E-channel wires nest without a detour
    e_lo = MX + mw + 7.2 - ox
    e_end = F['rp'].run('S', [ln for mn, ln in sorted(mape, key=lambda t: -mabs[t[0]][2])], e_lo)
    assert e_end < LEAF['rp']['wh'][0] - 2.5, e_end
    rp_n = bus('ak', SW + EW + 1) + ['fb_v'] + bus('fb_d', SW + 1) + ['rx_v'] + bus('rx_d', TW) + ['o_v'] + bus('o_d', W) + \
           ['o_cr', 'st_fault', 'st_drop'] + bus('st_rep', 32) + bus('session', EW) + ['rst_n', 'clk']
    F['rp'].run('N', rp_n, 20.0, step=4)
    for k, f in F.items():
        (SD / f'lkep_{k}_pins.tcl').write_text(f.tcl(f'# physical/ref_tile_specs/lkep/mk_lkep_split.py: {LEAF[k]["top"]} exact pins (macro-facing pins on the macro pin tracks)'))

    def base(names):
        out = []
        for n in names:
            b = n.split('[')[0]
            if b not in out: out.append(b)
        return out
    bench = lambda nm, seed, defs, exp: dict(
        name=nm, cmd=f"LOSTRP=2 MAXCYC=8000 JOBS=8 bash rtl/hbm_accel/tu/lk_ep_20261010/run_bench.sh {{RUN}}/{nm} 3 1500 300 {seed} -DOT_LKEP_LOCKSTEP {defs}".strip(),
        expect=exp, pass_regex='LKEP_BENCH PASS', threads=8, peak_ram_gb=8)
    rate = dict(name='lkrate_loop', cmd='JOBS=8 bash rtl/hbm_accel/tu/lk_ep_20261010/run_rate.sh {RUN}/b_rate 6000', expect='pass',
                pass_regex=r'LKRATE PASS FS 0 TXQ 32 N 6000 A->B 0\.749 B->A 0\.749', threads=8, peak_ram_gb=8)
    mut = dict(ti=['OT_LKEP_MUT_SEAM_L0', 'OT_LKEP_MUT_SEAM_CR'], ts=['OT_LKEP_MUT_SEAM_TX'], rp=['OT_LKEP_MUT_SEAM_RX'])
    what = dict(ti='TX-in leaf at the retry macro W face: TX queue bank, l0 relays, TX pin buffer, admission-credit relay, macro reset + session copies (14,085 flops)',
                ts='TX-out leaf at the retry macro S face: TX-out pin half (capture, credit counter, RL relays)',
                rp='RX leaf at the retry macro N + E faces: RX relays, RX pin buffer, RX-out pin half, ack / feedback relays, status')
    route = dict(ti=dict(pd=0.5, threads=16, peak_ram_gb=32), ts=dict(pd=0.5, threads=8, peak_ram_gb=16, m5_pg_pitch=5.4),
                 rp=dict(pd=0.5, threads=16, peak_ram_gb=24))
    for k, v in LEAF.items():
        f = F[k]
        spec = dict(
            name=f'lkep_{k}_ref', top=v['top'], kind='tile', sources=SRC, clock_port='clk', reset_ports=['rst_n'],
            outline=dict(w=v['wh'][0], h=v['wh'][1]), macros=[],
            pins={fc: base([n for n, c in sorted(f.p[fc].items(), key=lambda t: t[1])]) for fc in 'NSEW' if f.p[fc]},
            io_tcl=f'physical/ref_tile_specs/lkep/lkep_{k}_pins.tcl', refglob='*',
            io_flop_at_pins=dict(cols=6, allow_none=True), route=route[k],
            job=dict(owner='Codex:hbm_lkep', branch='claude/el1013-lkep-split', tag='s1',
                     views_to=f'physical/ref_tile/lkep_{k}_ref/views', record_to=f'results/rtl/ref_tile/lkep_{k}_ref',
                     extra_paths=['results/rtl/hbm_retry_txrx_pin_20261010', 'rtl/common', 'rtl/hbm_accel/tu', 'rtl/hbm_accel/ha2_ar',
                                  'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2', 'physical/ref_tile_specs/lkep'],
                     purpose=f'ot_lkep_sub split (owner clock rule; lkep_sub_cx-r1-31def6706: 21,881 sinks on one cluster spine that never '
                             f'converged): {what[k]}. One of three M5 leaves under the wires-only ot_lkep_sub (one clock entry per child); no '
                             f'register added or removed, every sub-face pin a flop; macro-facing pins on the macro pin tracks. Bench = '
                             f'tb_hfd_lk_ep built from this commit with the flat one-root tile in lockstep on the same pins (every output, '
                             f'every edge), stage mutants of this leaf, and the link rate (0.749 kept).',
                     benches=[bench('lkep_lockstep_s1', 1, '', 'pass'), bench('lkep_lockstep_s3', 3, '', 'pass'), bench('lkep_lockstep_s7', 7, '', 'pass')] +
                             [bench('lkep_' + m.lower().replace('ot_lkep_', ''), 1, '-D' + m, 'fail') for m in mut[k]] + [rate]))
        (SD / f'lkep_{k}_ref.json').write_text(json.dumps(spec, indent=1) + '\n')
    # ---- the sub: wires only.  Sub pins = the leaf pins dropped straight to the face (same x)
    ren = dict(ti=dict(clk='clk_ti'), ts=dict(clk='clk_ts'), rp=dict(clk='clk_rp', rst_n='rst_n_r', session='session_r'))
    S = Face(SUB); dup = {}
    for k, fc in (('ti', 'S'), ('ts', 'S'), ('rp', 'N')):
        ox = LEAF[k]['at'][0]
        for n, c in sorted(F[k].p[fc].items(), key=lambda t: t[1]):
            b = n.split('[')[0]; nn = ren[k].get(b, b) + n[len(b):]
            if nn in S.p[fc]:                      # rst_n feeds ti and ts from ONE sub pin (ti's)
                dup[nn] = k; continue
            S.put(fc, nn, ox + c)
    S.put('S', 'clk', MX - 10.8)                    # macro clock entry: up the ti | macro gap to the macro W-face clk pin
    (SD / 'lkep_sub_pins.tcl').write_text(S.tcl('# physical/ref_tile_specs/lkep/mk_lkep_split.py: ot_lkep_sub pins = the leaf pins dropped straight to the S / N face'))
    cuts = [
        dict(seam='ti E face -> macro W pins (in 547 + reset + session 24), 21.6-um gap, straight M4', bits=len(mapw), tracks=round(LEAF['ti']['wh'][1] / T), cut=round(len(mapw) / (0.5 * LEAF['ti']['wh'][1] / T), 3)),
        dict(seam='macro S pins -> ts N face (tx 583), 21.6-um gap, straight M5', bits=len(maps), tracks=round(LEAF['ts']['wh'][0] / T), cut=round(len(maps) / (0.5 * LEAF['ts']['wh'][0] / T), 3)),
        dict(seam='rp S face -> macro N pins (rx 584), 23.76-um gap, straight M5', bits=len(mapn), tracks=round(110.0 / T), cut=round(len(mapn) / (0.5 * 110.0 / T), 3)),
        dict(seam='macro E pins -> E channel (x 717.12-842.4) -> rp S face: every bus leaves E on its own M4 / M6 track and turns N on its own M5 track', bits=len(mape),
             tracks=round((SUB[0] - MX - mw - 2.16) / T), cut=round(len(mape) / (0.5 * (SUB[0] - MX - mw - 2.16) / T), 3)),
        dict(seam='sub S pins -> ti S face (w_d / w_oh / adm / credit / session), 151 um straight M5 in the free W column', bits=len(ti_s), tracks=round(LEAF['ti']['wh'][0] / T), cut=round(len(ti_s) / (0.5 * LEAF['ti']['wh'][0] / T), 3)),
    ]
    hops = dict(sub_S_to_ti=LEAF['ti']['at'][1], sub_S_to_ts=LEAF['ts']['at'][1], rp_to_sub_N=round(SUB[1] - LEAF['rp']['at'][1] - LEAF['rp']['wh'][1], 2),
                macro_E_to_rp=round(max(abs(MX + mw + 7.2 + 64 - (MX + mw)) + abs(LEAF['rp']['at'][1] - mabs[mn][2]) for mn, _ in mape), 1),
                ti_to_macro=21.6, macro_to_ts=21.6, rp_to_macro=round(LEAF['rp']['at'][1] - MY - mh, 2),
                macro_clk_entry=round(mabs['clk'][2] + 10.8, 1))
    sub = dict(
        name='lkep_sub_w_ref', top='ot_lkep_sub', kind='cluster', sources=SRC, defines=['OT_LKEP_HARD_LEAVES'], hard_define='OT_LKEP_HARD_LEAVES',
        clock='entries', clock_port='clk', clock_ports=['clk', 'clk_ti', 'clk_ts', 'clk_rp'], reset_ports=['rst_n', 'rst_n_r'],
        outline=dict(w=SUB[0], h=SUB[1]), child_lattice_um=2.16, macros=[],
        children=[dict(view=MACRO_VIEW, count=1, inst='u_rp', at=[MX, MY], orient='R0')] +
                 [dict(view=f'physical/ref_tile/lkep_{k}_ref/views/{v["top"]}', count=1, inst={'ti': 'u_ti', 'ts': 'u_ts', 'rp': 'u_rq'}[k], at=list(v['at']), orient='R0') for k, v in LEAF.items()],
        pins={fc: base([n for n, c in sorted(S.p[fc].items(), key=lambda t: t[1])]) for fc in 'NS'},
        io_tcl='physical/ref_tile_specs/lkep/lkep_sub_pins.tcl', refglob='*', route=dict(pd=0.5, threads=16, peak_ram_gb=48),
        structural_change='the 21,881-sink cluster spine (never converged: leaf arrival 4.8-8.0 ns at iteration 5) is removed: ot_lkep_sub is a wires-only '
                          'parent over the closed retry macro and three face-anchored M5 leaves (ti 14.1k / ts 1.8k / rp 6.0k sinks) with their own '
                          'roots, one clock entry per child, no leaf-to-leaf net, every sub pin a leaf flop dropped straight to the face; outline '
                          '820.8 x 777.6 -> 842.4 x 518.4, TX pins S / RX pins N.',
        cut_analysis=dict(outline_um=list(SUB), rule='demand / (tracks at 50 % reserve) <= 0.60; one layer (M4 or M5, 0.048 pitch) counted', cuts=cuts, hops_um=hops,
                          max_macro_aligned_jog_um={k: round(v, 3) for k, v in jog.items()}),
        job=dict(owner='Codex:hbm_lkep', branch='claude/el1013-lkep-split', tag='w1', views_to='physical/ref_tile/lkep_sub_w_ref/views',
                 record_to='results/rtl/ref_tile/lkep_sub_w_ref', extra_paths=['results/rtl/hbm_retry_txrx_pin_20261010', 'rtl/common', 'rtl/hbm_accel/tu', 'rtl/hbm_accel/ha2_ar',
                                                                             'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2', 'physical/ref_tile_specs/lkep'],
                 purpose='ot_lkep_sub as a wires-only parent (one clock entry per child) over the closed retry macro and the three closed M5 leaves.',
                 benches=[bench('lkep_lockstep_s1', 1, '', 'pass'), bench('lkep_lockstep_s3', 3, '', 'pass'), bench('lkep_lockstep_s7', 7, '', 'pass')] +
                         [bench('lkep_' + m.lower().replace('ot_lkep_', ''), 1, '-D' + m, 'fail') for ms in mut.values() for m in ms] + [rate]))
    (SD / 'lkep_sub_w_ref.json').write_text(json.dumps(sub, indent=1) + '\n')
    assert all(c['cut'] <= 0.60 for c in cuts), cuts
    print('pins', {k: {fc: len(f.p[fc]) for fc in 'NSEW' if f.p[fc]} for k, f in F.items()}, 'sub', {fc: len(S.p[fc]) for fc in 'NS'})
    print('jog', {k: round(v, 3) for k, v in jog.items()}, 'rp E group end', round(e_end, 2), 'of', LEAF['rp']['wh'][0])
    print('cuts', [(c['bits'], c['cut']) for c in cuts], 'hops', hops)


if __name__ == '__main__':
    main()
