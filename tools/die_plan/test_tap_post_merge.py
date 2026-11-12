"""QC-EVENT-S26 11-11: clock_taps.tcl POST_MIN (clock.tap_post_merge_min_sinks): after the affinity
passes a near-empty tap merges WHOLE into its nearest tap with >= min sinks within the radius; default off."""
import test_clock_taps_groups as G
import gen_phys
from pathlib import Path

FILL = ''.join(f'mkflop f{i} 0\n' for i in range(60))


def test_post_merge_moves_small_tap_whole(tmp_path):
    # two flops nearest clk_t1 (x 1000): a 2-sink tap after the nearest-tap split
    body = FILL + 'mkflop lone 900\nmkflop lone2 910\n'
    p = G.run(tmp_path, body, env='set ::env(OT_TAP_POST_MIN_SINKS) 16\nset ::env(OT_TAP_POST_MIN_UM) 1000')
    assert p.returncode == 0, p.stderr
    out = p.stdout
    assert 'POST_MIN 16 sinks/tap' in out and 'clk_t1(2)->clk' in out, out
    assert 'NET ck_lone nclk' in out and 'NET ck_lone2 nclk' in out
    assert '"dropped": ["clk_t1"]' in (tmp_path / 'ot_clock_taps.json').read_text()


def test_post_merge_respects_radius(tmp_path):
    body = FILL + 'mkflop lone 900\n'
    p = G.run(tmp_path, body, env='set ::env(OT_TAP_POST_MIN_SINKS) 16\nset ::env(OT_TAP_POST_MIN_UM) 200')
    assert p.returncode == 0, p.stderr
    assert 'NET ck_lone nt1' in p.stdout
    assert '0 small taps merged' in p.stdout and 'kept 1 clk_t1(1)' in p.stdout


def test_post_merge_default_off(tmp_path):
    body = FILL + 'mkflop lone 900\n'
    p = G.run(tmp_path, body)
    assert p.returncode == 0, p.stderr
    assert 'POST_MIN' not in p.stdout and 'NET ck_lone nt1' in p.stdout


def test_gen_phys_export_opt_in():
    import pytest
    assert gen_phys.tap_post_merge_exports({"clock": {"tap_radius_um": 200.0}}) == []
    ex = gen_phys.tap_post_merge_exports({"clock": {"tap_radius_um": 200.0, "tap_post_merge_min_sinks": 16}})
    assert ex == ["export OT_TAP_POST_MIN_SINKS = 16", "export OT_TAP_POST_MIN_UM = 200"]
    assert gen_phys.tap_post_merge_exports({"clock": {"tap_post_merge_min_sinks": 16}})[1] == "export OT_TAP_POST_MIN_UM = 200"
    for bad in (0, True, 1.5, 2000):
        with pytest.raises(ValueError):
            gen_phys.tap_post_merge_exports({"clock": {"tap_post_merge_min_sinks": bad}})


def test_schema_key():
    import schema
    ck = {"tap_post_merge_min_sinks": 16}
    js = (Path(schema.__file__).with_name("die_plan.schema.json")).read_text()
    assert '"tap_post_merge_min_sinks"' in js


def test_post_merge_never_empties_root(tmp_path):
    # clk (x 0) keeps 2 sinks, clk_t1 (x 1000) has 60: the root is not merged away
    body = 'mkflop a 0\nmkflop b 10\n' + ''.join(f'mkflop f{i} 1000\n' for i in range(60))
    p = G.run(tmp_path, body, env='set ::env(OT_TAP_POST_MIN_SINKS) 16\nset ::env(OT_TAP_POST_MIN_UM) 2000')
    assert p.returncode == 0, p.stderr
    assert 'NET ck_a nclk' in p.stdout and 'kept 1 clk(2):root' in p.stdout, p.stdout
