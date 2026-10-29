"""HBM-CORES-REBAL-10: gen_core_kit_hbm.macro_reg_guide_spec (opt-in --macro-reg-guide): one guide box per static macro,
grown, clipped to the core, pairwise disjoint, members = the sibling scope of the macro instance."""
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_core_kit_hbm as G  # noqa: E402

W, H = 94824, 41064   # ot_sram_1r1w_128x256_m1_r2c2 LEF SIZE, nm


def _pl(k, x, y, o="R0"):
    return dict(inst=f"u_fcore.u_core.u_bank0.u_data.g_read\\[{k}\\].u_m", macro="sram", xy_um=[x, y], orient=o)


def test_spec_disjoint_and_scoped():
    # lanes__canon-like stack: two columns 10.8 um apart, rows 49.68 um pitch, one macro at the core edge
    pls = [_pl(0, 34.722, 99.372, "MX"), _pl(1, 34.722, 149.052, "MX"), _pl(2, 140.346, 95.052, "MX"),
           _pl(3, 140.346, 144.732, "MY"), _pl(4, 5.0, 600.0)]
    core = (4.32, 4.32, 756.0, 721.44)
    g = G.macro_reg_guide_spec(pls, lambda m: (W, H), "g_wcopy", 15.0, core)
    assert [x["prefix"] for x in g][:2] == ["u_fcore.u_core.u_bank0.u_data.g_read[0].g_wcopy.",
                                            "u_fcore.u_core.u_bank0.u_data.g_read[1].g_wcopy."]
    for x in g:
        b, m = x["box_um"], x["macro_um"]
        assert core[0] <= b[0] and core[1] <= b[1] and b[2] <= core[2] and b[3] <= core[3]
        # the box still holds its own macro (cuts sit in the gaps between macros)
        assert b[0] <= m[0] and b[1] <= m[1] and m[2] <= b[2] and m[3] <= b[3]
    assert g[4]["box_um"][0] == 4.32                                   # clipped at the core edge
    assert g[0]["box_um"][0] == round(34.722 - 15.0, 3)                # free side keeps the full growth
    for a, b in itertools.combinations(g, 2):
        A, B = a["box_um"], b["box_um"]
        assert not (A[0] < B[2] and B[0] < A[2] and A[1] < B[3] and B[1] < A[3]), (a["name"], b["name"])
    # column gap 140.346 - (34.722 + 94.824) = 10.8 -> cut at its middle
    assert abs(g[0]["box_um"][2] - (34.722 + 94.824 + 5.4)) < 1e-3


def test_spec_refuses_rotation():
    try:
        G.macro_reg_guide_spec([_pl(0, 10, 10, "R90")], lambda m: (W, H), "g_wcopy", 15.0, (0, 0, 500, 500))
    except SystemExit as e:
        assert "orientation" in str(e)
    else:
        raise AssertionError("R90 accepted")


def test_relay_minimises_longer_hop_and_stays_disjoint():
    pls = [_pl(0, 34.722, 576.0), _pl(1, 630.0, 99.0)]
    core = (4.32, 4.32, 756.0, 721.44)
    mg = G.macro_reg_guide_spec(pls, lambda m: (W, H), "g_wcopy", 15.0, core)
    pins = [("g_bank_k0_u_bank_write_data[%d]" % i, 380.0 + i, 0.0) for i in range(4)] + [("other", 0.0, 700.0)]
    r = G.relay_reg_guide_spec([dict(name="w0", members=["u_bank0.wd_pin["], pins="^g_bank_k0_u_bank_write_",
                                     sinks="u_fcore.u_core.u_bank0.u_data.", half_um=12.0)], pins, mg, core)[0]
    assert r["pins"] == 4 and r["sink_macros"] == 2
    # direct pin -> far macro is ~894 um; the sinks alone need >= 536 um (L1 minimax); the relay reaches that bound
    assert max(r["hop_pins_um"], r["hop_sinks_um"]) < 545 and r["hop_pins_um"] < r["hop_sinks_um"]
    B = r["box_um"]
    for g in mg:
        A = g["box_um"]
        assert not (A[0] < B[2] and B[0] < A[2] and A[1] < B[3] and B[1] < A[3])
