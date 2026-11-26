import pytest
import retap as R

OLD = [("clk", 0.0, 0.0), ("clk_t1", 100.0, 0.0), ("clk_t134", 500.0, 500.0)]
NEW = [("clk", 0.0, 0.0), ("clk_t1", 100.0, 0.0), ("clk_t2", 480.0, 510.0)]


def test_rename_map_only_for_names_gone_from_the_new_grid():
    assert R.tap_rename_map(OLD, NEW) == {"clk_t134": "clk_t2"}


def test_apply_renames_and_keeps_live_names():
    live = {n for n, _, _ in NEW}
    assert R.apply_rename(["clk_t134", "clk_t1", "other"], {"clk_t134": "clk_t2"}, live) == ["clk_t2", "clk_t1", "other"]


def test_unmapped_clk_t134_style_name_is_a_hard_error_naming_the_pin():
    live = {n for n, _, _ in NEW}
    with pytest.raises(R.RetapError) as e:
        R.apply_rename(["clk_t999"], {"clk_t134": "clk_t2"}, live, where="kv3_pv pins/22 source_clock_port")
    assert "kv3_pv pins/22" in str(e.value) and "clk_t999" in str(e.value)
