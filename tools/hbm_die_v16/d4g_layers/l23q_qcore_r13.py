#!/usr/bin/env python3
"""HBM-DIE14 10-21 r14 layer (after l23_su_pretree): bind the qcore r13c master on sucore_<q> (H.STA.BLK.16.3 / 16.6).

DRIVE-HBM 23:36 decision: r14 = r13 + l23 SU pre-tree + qcore r13c bind.  l23 sets sucore_<q> (ot_hbm_su_static_qcore)
PRETREE=1 + slice_t[267:0]; the closing qcore is ot_hbm_su_static_qcore_r13 (claude/hbm-qcore9-1020, r13c census PASS
max 32, kit physical/ref_tile/hbm_su_qcore_r13_1020) = the PRETREE=1 form with ONE clock (clk_ctl):
  ports  clk_ctl, rst_n, rf_rd_cmd[53:0], red_cmd[73:0], rf_drain_cmd[1:0], slice_x[127:0], rf_wv/wa/wd, rf_bword[127:0],
         rf_bcmd[35:0], rf_dsec[255:0], red_sv, red_tag[31:0], red_x[31:0], red_rf_v, rr_wv/wa/wd, sfu_x[31:0],
         slice_t[267:0], fault                         (= the GEN2e4 qcore ports - clk_rf[63:0] - clk_red + slice_t)
So per quarter: master -> ot_hbm_su_static_qcore_r13 #(MUT 0, COLLPORT 1, RF_LOCAL 1, PRETREE 1), source + rtl_deps = the
r13 kit RTL, ports clk_rf / clk_red dropped with their clock_resets rows (both were pll_serial = the clk_ctl source).
Every data port / edge is unchanged (checked).  Until the r13c view CLOSES the die binds it as a SYNTH stand-in."""
import argparse, copy, json
from pathlib import Path

QS = ('NW', 'NE', 'SW', 'SE')
NEW = 'ot_hbm_su_static_qcore_r13'
SRC = 'rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_qcore_r13.sv'
DEPS = ['rtl/hbm_accel/generic/adapters/static_su/reduction/ot_hbm_su_red_pretree_r13.sv',
        'rtl/hbm_accel/generic/adapters/static_su/reduction/ot_hbm_su_reduce_static_r13.sv',
        'rtl/hdc/ot_hdc_fp32_add_n32.sv', 'rtl/hdc/ot_hdc_prefix.sv', 'rtl/hdc/ot_hdc_fastfp.sv']
DROP = ('clk_rf', 'clk_red')
PORTS = {'clk_ctl': ('input', 1), 'rst_n': ('input', 1), 'rf_rd_cmd': ('input', 54), 'red_cmd': ('input', 74),
         'rf_drain_cmd': ('input', 2), 'slice_x': ('input', 128), 'rf_wv': ('input', 4), 'rf_wa': ('input', 32),
         'rf_wd': ('input', 128), 'rf_bword': ('output', 128), 'rf_bcmd': ('output', 36), 'rf_dsec': ('output', 256),
         'red_sv': ('output', 1), 'red_tag': ('output', 32), 'red_x': ('output', 32), 'red_rf_v': ('output', 1),
         'rr_wv': ('input', 1), 'rr_wa': ('input', 5), 'rr_wd': ('input', 256), 'sfu_x': ('input', 32),
         'slice_t': ('input', 268), 'fault': ('output', 1)}


def apply(original):
    c = copy.deepcopy(original); I = c['instances']
    rep = dict(layer='l23q_qcore_r13', master=NEW, instances={}, dropped_clock_rows=0)
    for q in QS:
        n = f'sucore_{q}'; i = I[n]
        if i['master'] not in ('ot_hbm_su_static_qcore', 'ot_hbm_su_static_qcore_r5') or (i.get('params') or {}).get('PRETREE') != 1:
            raise ValueError(f'{n}: expected l23 PRETREE=1 qcore, got {i["master"]} {i.get("params")}')
        for p in DROP:
            if p not in i['ports']:
                raise ValueError(f'{n}: port {p} absent')
        for e in c['edges']:
            for end in ('source', 'sink'):
                if e[end][0] == n and e[end][1] in DROP:
                    raise ValueError(f'{n}.{e[end][1]} is a data edge ({e["name"]}): not a clock-only port')
        rows = [r for r in c['clock_resets'] if r.get('instance') == n and r.get('port') in DROP]
        if len(rows) != 2 or any(r.get('kind') != 'clock' or r.get('source') != ['hb_ckgen', 'pll_serial'] for r in rows):
            raise ValueError(f'{n}: clk_rf/clk_red clock rows not the expected pll_serial pair: {rows}')
        ctl = [r for r in c['clock_resets'] if r.get('instance') == n and r.get('port') == 'clk_ctl']
        if len(ctl) != 1 or ctl[0].get('source') != ['hb_ckgen', 'pll_serial']:
            raise ValueError(f'{n}: clk_ctl not on pll_serial')
        c['clock_resets'] = [r for r in c['clock_resets'] if not (r.get('instance') == n and r.get('port') in DROP)]
        rep['dropped_clock_rows'] += len(rows)
        old = i['master']
        for p in DROP:
            del i['ports'][p]
        got = {k: (v['direction'], v['bits']) for k, v in i['ports'].items()}
        if got != PORTS:
            raise ValueError(f'{n}: port set differs from r13: {set(got.items()) ^ set(PORTS.items())}')
        i['master'] = NEW; i['source'] = SRC
        i['params'] = dict(MUT=0, COLLPORT=1, RF_LOCAL=1, PRETREE=1) | {k: v for k, v in (i.get('params') or {}).items() if k == 'MUT'}
        i['rtl_deps'] = sorted(set(DEPS))
        i['note'] = (i.get('note') or '') + (f' | l23q: master {old} -> {NEW} (qcore r13c, PRETREE=1, clk_ctl only; '
                                             'clk_rf/clk_red dropped = same pll_serial source)')
        rep['instances'][n] = dict(old=old, params=i['params'])
    m = c.get('masters')
    if isinstance(m, dict):
        for k in ('ot_hbm_su_static_qcore', 'ot_hbm_su_static_qcore_r5'):
            if k in m and not any(x['master'] == k for x in I.values()):
                del m[k]
        m[NEW] = sum(1 for x in I.values() if x['master'] == NEW)
    return c, rep


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('inp'); p.add_argument('out'); p.add_argument('--report', required=True)
    a = p.parse_args()
    c, r = apply(json.load(open(a.inp)))
    Path(a.out).write_text(json.dumps(c, separators=(',', ':')) + '\n'); Path(a.report).write_text(json.dumps(r, indent=1) + '\n')
    print('L23Q_QCORE_R13 4 sucore -> %s, clock rows dropped %d' % (NEW, r['dropped_clock_rows']))


if __name__ == '__main__':
    main()
