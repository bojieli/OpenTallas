from post_grt_gate import gate


def logs(tmp_path, mutation=None):
    for c in ('TT', 'FF'):
        s = f'RP1_M {c} vclk source latency := 288.9 (OT_VCLK_FF=auto, arrival_max_rise)\n'
        s += f'RP1_M {c} setup_wns 217.22 setup_ep 0 hold_wns 6.55 hold_ep 0\n'
        for mode in ('max', 'min'):
            s += f'RP1_PAIR {c} {mode} n 10365 worst 55.71 bounded 0 signed -55.71 launch q capture d crpr 3 p99_raw 55 searched 1 nopath 0 verify 0.000 rows {{}}\n'
        if c == 'FF' and mutation:
            s = s.replace(*mutation)
        (tmp_path / f'meas_route_{c}.log').write_text(s)


def test_diagnostic_prefix_does_not_poison_numeric_row(tmp_path):
    logs(tmp_path)
    assert gate(tmp_path) == []


def test_hold_pair_and_missing_census_fail_closed(tmp_path):
    for mutation in (('hold_wns 6.55', 'hold_wns -0.01'),
                     ('worst 55.71', 'worst 80.01'),
                     ('n 10365', 'n 0'),
                     ('bounded 0', 'bounded 1'),
                     ('verify 0.000', 'verify 1.0'),
                     ('RP1_M FF setup_wns', 'INCOMPLETE FF setup_wns'),
                     ('worst 55.71', 'worst nan')):
        logs(tmp_path, mutation)
        assert gate(tmp_path), mutation
