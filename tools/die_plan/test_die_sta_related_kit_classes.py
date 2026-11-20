"""DIE-CORETAP-1119: kit-contract hold split per pair class (kind core/reg, part family)."""
import die_sta_related as R


def _taps():
    return {"t_pv_S_0__clk_c14": {"part": "pv_S_0"}, "t_pv_S_0__clk_t111": {"part": "pv_S_0"},
            "t_pv_S_0__clk_t2": {"part": "pv_S_0"}, "t_hg_EN_0__clk_t1": {"part": "hg_EN_0"},
            "t_hg_EN_0__clk_c0": {"part": "hg_EN_0"}}


def test_part_family_and_kind():
    assert R.part_family("pv_S_0") == "pv" and R.part_family("phy_EN_3") == "phy" and R.part_family("s_2N_C") == "s"
    T = _taps()
    assert R.pair_tap_kind("t_pv_S_0__clk_c14", T["t_pv_S_0__clk_c14"]) == "core"
    assert R.pair_tap_kind("t_pv_S_0__clk_t111", T["t_pv_S_0__clk_t111"]) == "reg"


def test_classes_worst_and_counts():
    T = _taps()
    hd = [(175.0, "t_pv_S_0__clk_c14", "t_pv_S_0__clk_t111", "pv_S_0"),
          (40.0, "t_pv_S_0__clk_t2", "t_pv_S_0__clk_t111", "pv_S_0"),
          (5.0, "t_hg_EN_0__clk_t1", "t_hg_EN_0__clk_c0", "hg_EN_0")]
    c = R.kit_contract_classes(hd, T, lambda r: 10.0)
    k = c["kind"]
    assert k["core->reg"]["worst_hold_bound_ps"] == -165.0 and k["core->reg"]["neg_pairs"] == 1
    assert k["reg->reg"]["worst_hold_bound_ps"] == -30.0
    assert k["reg->core"]["worst_hold_bound_ps"] == 5.0 and k["reg->core"]["neg_pairs"] == 0
    assert list(c["family"])[0] == "pv:core->reg"          # worst class first
    assert c["family"]["hg:reg->core"]["pairs"] == 1
    # the overall bound is the min of the class bounds
    assert min(v["worst_hold_bound_ps"] for v in k.values()) == 10.0 - 175.0


def test_per_region_window():
    T = _taps()
    hd = [(30.0, "t_pv_S_0__clk_t2", "t_pv_S_0__clk_t111", "pv_S_0"), (30.0, "t_hg_EN_0__clk_t1", "t_hg_EN_0__clk_c0", "hg_EN_0")]
    c = R.kit_contract_classes(hd, T, lambda r: {"pv_S_0": 40.0}.get(r[3], 10.0))
    assert c["family"]["pv:reg->reg"]["worst_hold_bound_ps"] == 10.0
    assert c["family"]["hg:reg->core"]["worst_hold_bound_ps"] == -20.0
