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
        a = argparse.Namespace(hold_margin=50.0, skew=50.0, setup_unc=60.0, die_skew=90.0, wire=None, reach=500.0,
                               max_spread=80.0, q_class=180.0, p_class=150.0, q_pin=220.0, p_pin=190.0, ocv=0.05)
        B, avail, w = P.side_budget(a, 'tt')
        assert round(avail, 1) == 683.3 and round(B, 1) == 151.7 and w == 0.76
        r = P.audit_view('v', a, 1)
        b, s = r['buses'], r['summary']
        assert r['clocks']['ck']['ref_ps'] == 100.0, r['clocks']
        # residuals after the reference: o = O - R, s = S + R; per-side bits over B = 151.7
        assert b['ok_i']['in_ps'] == 60.0 and b['ok_i']['in_over_bits'] == 0
        assert b['far_i']['in_ps'] == 250.0 and b['far_i']['in_over_bits'] == 1
        assert b['q']['bits'] == 2 and b['q']['out_ps'] == 300.0 and b['q']['out_over_bits'] == 1 and b['q']['worst_out_pin'] == 'q[1]'
        assert b['thru']['comb_bits'] == 1 and b['thru']['comb_from'] == ['ok_i']
        assert b['fo']['dir'] == 'clock_out' and s['clock_out_bits'] == 1
        # FF: L = min(175 * 0.8) - 80 = 60, H = 60 * 0.8 - 80 = -32 -> 92 < 100
        assert s['L_min_ps'] == 60.0 and s['H_max_ps'] == -32.0 and s['min_delay_margin_ps'] == 92.0
        # die statement: C = o + s = 550, reach = (683.3 - 550) / 0.76; launch / capture beyond the boundary clock
        # (lib tree 90..110 around R 100): q_lb = 300 - 10, p_lb = 250 - 10
        assert s['pair_cost_ps'] == 550.0 and s['reach_self_um'] == round((avail - 550.0) / 0.76, 1)
        assert s['q_lb_ps'] == 290.0 and s['p_lb_ps'] == 240.0 and s['out_unreg_bits'] == 1 and s['in_unreg_bits'] == 1
        dc = r['die_clock']
        assert dc['entry_offset_ps'] == -100.0 and dc['entry_offset_ff_ps'] == -80.0 and dc['boundary_spread_ps'] == 20.0
        assert dc['balanced_entry_offset_ps'] == -125.0 and dc['signoff_allow_ps'] == 516.7
        assert r['flags'] == ['comb', 'out_unreg', 'in_unreg', 'min_delay'], r['flags']
        assert r['notes'] == ['reach_limited', 'ref_estimated'] and len(r['fix']) == 4, (r['notes'], r['fix'])
        # insertion.json: the boundary mean is the reference (SDC clock "ck" matches the Liberty pin or its bus bit) and
        # its measured spread is judged; O + S (the pair cost) does not move with the reference
        (v / 'insertion.json').write_text('{"clock": "ck", "tt": {"boundary": {"n": 4, "mean": 104.0, "min": 20.0, "max": 110.0}, '
                                          '"all": {"n": 9, "mean": 100.0, "min": 20.0, "max": 110.0}}, '
                                          '"ff": {"boundary": {"n": 4, "mean": 83.0, "min": 16.0, "max": 88.0}}}')
        r2 = P.audit_view('v', a, 1)
        assert r2['die_clock']['reference_ps'] == 104.0 and r2['die_clock']['reference_src'].startswith('insertion.json')
        assert r2['buses']['q']['out_ps'] == 296.0 and r2['buses']['far_i']['in_ps'] == 254.0 and r2['summary']['pair_cost_ps'] == 550.0
        assert r2['die_clock']['boundary_spread_ps'] == 90.0 and 'spread' in r2['flags'] and 'ref_estimated' not in r2['notes']
        # Independent clock records must not borrow the other domain's mean or
        # spread; an SDC clock name can differ from its physical Liberty pin.
        ll = P.parse_lib(v / 't_tt.lib')
        ll['pins']['hk'] = ll['pins']['ck']
        refs = P.clock_refs(ll, {'clock_measurements': {
            'ck': {'clock': 'core_clk', 'lib_clock_pin': 'ck', 'tt': {'boundary': {'n': 4, 'mean': 103, 'min': 98, 'max': 110}}},
            'hk': {'clock': 'hclk', 'lib_clock_pin': 'hk', 'tt': {'boundary': {'n': 8, 'mean': 207, 'min': 199, 'max': 216}}},
        }}, 'tt')
        assert refs['ck']['rise'] == 103 and refs['ck']['bmin'] == 98 and refs['ck']['n'] == 4
        assert refs['hk']['rise'] == 207 and refs['hk']['bmin'] == 199 and refs['hk']['n'] == 8
        assert all(r['src'] == 'insertion.json boundary mean' for r in refs.values())
        # NATIVE-REF 2026-10-18: a parent with hard-child clock pins at its boundary (ck_insertion child_flop record)
        # is referenced at the child flops, not the raw child pins (kp4_dec: launch 388 raw-pin vs 174 child-flop basis)
        cf = P.clock_refs(P.parse_lib(v / 't_tt.lib'), {'clock': 'ck', 'tt': {
            'boundary': {'n': 4, 'mean': 104.0, 'min': 20.0, 'max': 110.0},
            'child_flop': {'boundary': {'n': 4, 'mean': 380.0, 'min': 360.0, 'max': 400.0}}}}, 'tt')
        assert cf['ck']['rise'] == 380.0 and cf['ck']['bmin'] == 360.0 and cf['ck']['bmax'] == 400.0, cf
        assert cf['ck']['src'] == 'insertion.json child_flop boundary mean'
        (v / 'insertion.json').unlink()
        # a tile over the reach against its own kind but with pin registers is NOT a tile defect; C > available is 'abut'
        a.q_pin = a.p_pin = 1000.0
        r3 = P.audit_view('v', a, 1)
        assert 'out_unreg' not in r3['flags'] and 'abut' not in r3['flags'] and 'reach_limited' in r3['notes']
        a.die_skew = 250.0
        assert 'abut' in P.audit_view('v', a, 1)['flags']
        a.q_pin, a.p_pin, a.die_skew = 220.0, 190.0, 90.0
        a.skew = 0.0
        assert 'min_delay' not in P.audit_view('v', a, 1)['flags']
        # export-SDC marking: corrected only by the view's own record, never by commit time
        assert r['export_sdc_corrected'] is None and r['exported_before_export_sdc_fix'] is True
        (v / 'abstract.json').write_text('{"name": "t", "verdict": {"json": "x"}}')
        assert P.audit_view('v', a, 1)['exported_before_export_sdc_fix'] is True
        (v / 'abstract.json').write_text('{"name": "t", "verdict": {"check": {"tt": {"ok": true}}}}')
        r = P.audit_view('v', a, 1)
        assert r['export_sdc_corrected'] == 'verdict' and r['exported_before_export_sdc_fix'] is False
        (v / 'abstract.json').write_text('{"name": "t", "reexport_1013": {"why": "replayed"}}')
        assert P.audit_view('v', a, 1)['export_sdc_corrected'] == 'reexport_1013'
    print('test_pinreg_audit PASS')


if __name__ == '__main__':
    main()
