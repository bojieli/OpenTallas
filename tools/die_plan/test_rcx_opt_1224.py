"""OWNER RULE 12.24 (10-31): ONE shared optimistic width-aware RCX set (size-effect R credit, M1..M9) is the default of
the clock_routed RCX recipe (CLOCK-128-R6), rcx_kv and the ot-clk region mesh RCX (tools/clk/mesh_form.py)."""
import inspect
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "clk"))
import clock_routed as CR  # noqa: E402
import rcx_width_rules as RW  # noqa: E402

MIXED = (HERE / CR.OPT_RULES).read_text()


def test_credit_m1_m9_monotone_and_unity_at_table_width():
    for n in range(1, 10):
        w0 = RW.ASAP7_W0_UM[n]
        assert RW.size_effect_credit(n, w0) == 1.0
        assert RW.size_effect_credit(f"M{n}", w0 / 2) == 1.0          # never a penalty below the table width
        c = [RW.size_effect_credit(n, w0 * k) for k in (2, 4, 8, 32)]
        assert all(1.0 > a > b > 0.45 for a, b in zip(c, c[1:])), (n, c)


def test_rpersq_opt_credits_only_named_layers():
    base = RW.rpersq(MIXED)
    assert sorted(base) == [f"M{n}" for n in range(1, 10)]
    rs, cred = RW.rpersq_opt(MIXED, {"M8": 0.16, 9: 0.16})
    for lay in base:
        if lay in ("M8", "M9"):
            assert abs(rs[lay] - base[lay] * RW.size_effect_credit(lay, 0.16)) < 1e-9
            assert cred[lay] < 0.8
        else:
            assert rs[lay] == base[lay] and cred[lay] == 1.0


def test_clock_routed_default_is_opt():
    assert inspect.signature(CR.write_route).parameters["rcx_rules"].default == "opt"
    assert CR.opt_rules_path().exists()
    t = CR.rcx_tcl("opt", MIXED, CR.opt_credit_widths("16w"))
    assert "-ext_model_file /out/rcx_ndr.rules -lef_res" in t
    rs, _ = RW.rpersq_opt(MIXED, {"M8": 0.64, "M9": 0.64})
    assert f"[$ot_tech findLayer M8] setResistance {rs['M8']:.6g}" in t
    assert f"setResistance {RW.rpersq(MIXED)['M8']:.6g}" not in t      # no R_sq/w upper bound on the NDR layer
    assert "OWNER 12.24" in t
    # stock and explicit files stay selectable (A/B), unchanged
    assert CR.rcx_tcl() == f"extract_parasitics -ext_model_file {CR.STOCK_RULES}"
    assert f"setResistance {RW.rpersq(MIXED)['M8']:.6g}" in CR.rcx_tcl("ndr", MIXED)


def test_mixed_table_exact_width_check():
    for ndr in ("4w", "8w", "16w", "2x16w"):
        c = CR.rules_width_check(MIXED, ndr)
        assert c["ok"] and c["selection"] == "exact", c
    assert CR.rules_width_check(MIXED, None)["ok"]
    old = CR.rules_width_check((HERE / "rcx/asap7_rcx_ndr016.rules").read_text(), "16w")
    assert not old["ok"]                                                  # 2-entry R18 rule unchanged


def test_mesh_form_region_rcx_uses_opt_credit():
    import mesh_form
    t = mesh_form.rcx_opt_tcl(dict(name="CK2W2S", layers=["M8", "M9"], width=0.08, spacing=0.32))
    assert "extract_parasitics -ext_model_file $P/rcx_patterns.rules -lef_res" in t
    rs, _ = RW.rpersq_opt(MIXED, {"M8": 0.08, "M9": 0.08})
    assert f"[$ot_tech findLayer M9] setResistance {rs['M9']:.6g}" in t
    assert "@" not in t
