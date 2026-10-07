#!/usr/bin/env python3
"""SS / FF liberty views for the S81 die link black boxes ot_pdie_serdes and ot_pdie_ucie (S81-RERUN, 2026-10-06).

Their v2 abstracts (physical/asap7_v41x_pdie_macros_v2/<name>/) carry only a TT liberty (tools/chip_assembly/macros.py
FakeRAM boundary: clock-to-Q 218 ps, setup 50 ps, hold 50 ps, output slew 20 ps), while the HBM3E PHY abstract has
SS/FF/TT from tools/mem_compiler/hbm_phy_gen.py (registered boundary = ASAP7 flop clock-to-Q / setup + 3 FO4, hold
+ 1 FO4, output slew 1.5 FO4, per calibrated corner).  Same method, applied as a derating: every boundary number of the
TT view is scaled by the HBM PHY's corner / TT ratio of the same quantity (the HBM PHY json records the per-corner
values), and the operating conditions are the HBM PHY's.  The TT view is unchanged; the json gains a "corner_libs"
provenance record.

  python3 tools/s81_pdie_corner_libs.py [--check]
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDIE = ROOT / 'physical/asap7_v41x_pdie_macros_v2'
HBM = ROOT / 'physical/asap7_memory_macros_v2/ot_hbm3e_phy_v41x_aw30_e8p5/ot_hbm3e_phy_v41x_aw30_e8p5.json'
NAMES = ('ot_pdie_serdes', 'ot_pdie_ucie')
QTY = {'clk2q': 'clk_to_q_ps', 'setup': 'setup_ps', 'hold': 'hold_ps', 'slew': 'out_slew_intrinsic_ps'}


def ratios():
    t = json.loads(HBM.read_text())['timing']
    out = {}
    for c in ('ss', 'ff'):
        out[c] = dict(voltage=t[c]['voltage'], temperature=t[c]['temperature'],
                      **{q: t[c][k] / t['tt'][k] for q, k in QTY.items()})
    return out


def derate(text, c, r):
    lines = text.split('\n')
    kind = None
    out = []
    for ln in lines:
        m = re.search(r'timing_type : (\w+);', ln)
        if m:
            kind = {'setup_rising': 'setup', 'hold_rising': 'hold', 'rising_edge': 'clk2q'}[m.group(1)]
        if 'cell_rise' in ln or 'cell_fall' in ln:
            q = 'clk2q'
        elif 'rise_transition' in ln or 'fall_transition' in ln:
            q = 'slew'
        elif 'constraint' in ln:
            q = kind
        else:
            q = None
        if q:
            cur = q
        if 'values (' in ln:
            ln = re.sub(r'([0-9]+\.[0-9]+)', lambda m_: f'{float(m_.group(1)) * r[cur]:.4f}', ln)
        out.append(ln)
    s = '\n'.join(out)
    v, tmp = r['voltage'], r['temperature']
    oc = f'{c}_{str(v).replace(".", "p")}_{int(tmp)}'
    s = re.sub(r'nom_temperature : [0-9.]+;', f'nom_temperature : {tmp:.3f};', s)
    s = re.sub(r'nom_voltage : [0-9.]+;', f'nom_voltage : {v};', s)
    s = re.sub(r'operating_conditions\(tt_0p7_25\) \{[^}]*\}',
               f'operating_conditions({oc}) {{ process : 1; temperature : {tmp:.3f}; voltage : {v}; tree_type : balanced_tree; }}', s)
    s = s.replace('default_operating_conditions : tt_0p7_25;', f'default_operating_conditions : {oc};')
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    r = ratios()
    bad = 0
    for n in NAMES:
        d = PDIE / n
        tt = (d / f'{n}_tt.lib').read_text()
        js = json.loads((d / f'{n}.json').read_text())
        rec = dict(method='HBM3E PHY abstract corner method (tools/mem_compiler/hbm_phy_gen.py: flop clock-to-Q / setup '
                          '+ 3 FO4, hold + FO4, slew 1.5 FO4 per calibrated corner) applied as corner / TT ratios to '
                          'this TT view', source=str(HBM.relative_to(ROOT)), tool='tools/s81_pdie_corner_libs.py',
                   ratios={c: {k: round(v, 6) for k, v in rr.items()} for c, rr in r.items()}, views={})
        for c in ('ss', 'ff'):
            txt = derate(tt, c, r[c])
            p = d / f'{n}_{c}.lib'
            if a.check:
                bad += (not p.is_file()) or p.read_text() != txt
            else:
                p.write_text(txt)
            rec['views'][p.name] = hashlib.sha256(txt.encode()).hexdigest()
        if not a.check:
            js['corner_libs'] = rec
            (d / f'{n}.json').write_text(json.dumps(js, indent=2, sort_keys=True) + '\n')
        print(n, {c: {k: round(v, 3) for k, v in rr.items()} for c, rr in r.items()})
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
