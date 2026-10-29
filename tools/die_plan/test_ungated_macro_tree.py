import collections
import pytest
import core_family_slice as F


def geo_file(tmp_path, gated=False):
    lines = ['DIE 0 0 120 120', 'CORE 0 0 120 120', 'PIN ck 60 60']
    if gated:
        lines.append('GATE g ICGx1_ASAP7_75t_R 60 60')
    for i, (x, y) in enumerate(( (x, y) for x in range(6, 115, 9) for y in range(6, 115, 9) )):
        lines.append('SINK %d %d DFFHQNx1_ASAP7_75t_R r%d CLK%s' % (x, y, i, ' gate=g' if gated else ''))
    lines.append('MACRO mem ot_sram_1r1w_128x256_m1_r2c2 40 40 52 50 clk 53 45')
    p = tmp_path / 'g.txt'
    p.write_text('\n'.join(lines) + '\n')
    return p


def test_macro_is_separate_leaf_with_actual_pin_cap_and_equal_depth(tmp_path, monkeypatch):
    monkeypatch.setattr(F, 'macro_clk_cap', lambda m, p: {'TT': 9.3458, 'FF': 8.124})
    geo = geo_file(tmp_path)
    P = F.ungated_macro_htree(geo, [2, 2], 70, [], 8)
    macro = [(u, s) for u, ss in P['leafsinks'].items() for s in ss if s[4].startswith('MACRO:')]
    assert len(macro) == 1
    u, s = macro[0]
    assert len(P['leafsinks'][u]) == 1 and s[:4] == (53., 45., 'mem', 'clk')
    assert P['sinkcap'] == {'TT': {'mem/clk': 9.3458}, 'FF': {'mem/clk': 8.124}}
    assert not any(n[4] in ('icg', 'gbuf') for n in P['nodes'])
    par = {n[0]: n[1] for n in P['nodes']}
    depths = set()
    for leaf in P['leafsinks']:
        d = 0
        while leaf is not None:
            d += 1
            leaf = par[leaf]
        depths.add(d)
    assert len(depths) == 1
    counts = collections.Counter('%s/%s' % (s[2], s[3]) for ss in P['leafsinks'].values() for s in ss)
    assert all(n == 1 for n in counts.values()) and counts['mem/clk'] == 1


def test_ungated_form_refuses_gated_vehicle(tmp_path):
    with pytest.raises(SystemExit, match='use icg_copies'):
        F.ungated_macro_htree(geo_file(tmp_path, gated=True), [2, 2], 70, [])


def test_macro_missing_cap_fails_closed(tmp_path, monkeypatch):
    def missing(*args):
        raise SystemExit('macro_clk_cap: no liberty')
    monkeypatch.setattr(F, 'macro_clk_cap', missing)
    with pytest.raises(SystemExit, match='no liberty'):
        F.ungated_macro_htree(geo_file(tmp_path), [2, 2], 70, [], 8)


def test_macro_guard_catches_omitted_pin_and_wrong_corner_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(F, 'macro_clk_cap', lambda m, p: {'TT': 9.3458, 'FF': 8.124})
    geo = geo_file(tmp_path)
    rec = dict(leaf_sinks={'m': ['mem/clk']}, macro_leaves=['m'], sinkcap={'TT': {'mem/clk': 9.3458}, 'FF': {'mem/clk': 8.124}})
    assert not F.macro_leaf_errors(rec, geo)
    rec['sinkcap']['FF']['mem/clk'] = .65
    assert F.macro_leaf_errors(rec, geo) == ['macro leaf cap mismatch FF mem/clk']
    rec['leaf_sinks']['m'] = []
    assert 'macro leaf coverage/classification: mem/clk' in F.macro_leaf_errors(rec, geo)
