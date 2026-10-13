#!/usr/bin/env python3
"""pinreg_audit.py: Liberty ETM reading and the per-pin flags on a synthetic view (run: python3 test_pinreg_audit.py)."""
import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pinreg_audit as P  # noqa: E402


def lib(scale_ff=1.0):
    def arc(typ, rel, **t):
        body = ''.join(f'        {k}(scalar) {{\n          values("{v * scale_ff}");\n        }}\n' for k, v in t.items())
        return f'      timing() {{\n        related_pin : "{rel}";\n        timing_type : {typ};\n{body}      }}\n'

    def pin(name, d, arcs, clock=False):
        return f'    pin("{name}") {{\n      direction : {d};\n' + ('      clock : true;\n' if clock else '') + arcs + '    }\n'
    return ('library (t) {\n  time_unit : "1ps";\n  cell ("t") {\n'
            + pin('ck', 'input', arc('min_clock_tree_path', 'ck', cell_rise=90) + arc('max_clock_tree_path', 'ck', cell_rise=110), True)
            + pin('ok_i', 'input', arc('setup_rising', 'ck', rise_constraint=-40) + arc('hold_rising', 'ck', rise_constraint=60))
            + pin('far_i', 'input', arc('setup_rising', 'ck', rise_constraint=150) + arc('hold_rising', 'ck', rise_constraint=-80))
            + '    bus("q") {\n      direction : output;\n'
            + pin('q[0]', 'output', arc('rising_edge', 'ck', cell_rise=180, cell_fall=175))
            + pin('q[1]', 'output', arc('rising_edge', 'ck', cell_rise=400, cell_fall=390)) + '    }\n'
            + pin('thru', 'output', arc('combinational', 'ok_i', cell_rise=50))
            + pin('fo', 'output', arc('rising_edge', 'ck', cell_rise=120) + arc('falling_edge', 'ck', cell_fall=120))
            + '  }\n}\n')


def main():
    with tempfile.TemporaryDirectory() as td:
        v = Path(td) / 'v'
        v.mkdir()
        (v / 't_tt.lib').write_text(lib())
        (v / 't_ff.lib').write_text(lib(0.8))
        P.ROOT = Path(td)
        P.last_commit_time = lambda d: 0
        a = argparse.Namespace(budget_frac=0.2, hold_margin=50.0, skew=50.0)
        r = P.audit_view('v', a, 1)
        b, s = r['buses'], r['summary']
        assert r['clocks']['ck']['ref_ps'] == 100.0, r['clocks']
        assert b['ok_i']['in_ps'] == 60.0 and b['ok_i']['in_over_bits'] == 0
        assert b['far_i']['in_ps'] == 250.0 and b['far_i']['in_over_bits'] == 1
        assert b['q']['bits'] == 2 and b['q']['out_ps'] == 300.0 and b['q']['out_over_bits'] == 1 and b['q']['worst_out_pin'] == 'q[1]'
        assert b['thru']['comb_bits'] == 1 and b['thru']['comb_from'] == ['ok_i']
        assert b['fo']['dir'] == 'clock_out' and s['clock_out_bits'] == 1
        # FF: L = min(175 * 0.8) - 80 = 60, H = 60 * 0.8 - 80 = -32 -> 92 < 100
        assert s['L_min_ps'] == 60.0 and s['H_max_ps'] == -32.0 and s['min_delay_margin_ps'] == 92.0
        assert r['flags'] == ['comb', 'out_over', 'in_over', 'min_delay'], r['flags']
        a.skew = 0.0
        assert 'min_delay' not in P.audit_view('v', a, 1)['flags']
    print('test_pinreg_audit PASS')


if __name__ == '__main__':
    main()
