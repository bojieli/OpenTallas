"""S81-TAPROWS 11-15: the half / idx tap-row delta (tools/die_plan/s81_taprows.py)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import core_clock_contract as CC  # noqa: E402
import s81_taprows as TR  # noqa: E402

LIB = 'library (x) { cell (c) { pin (clk) { clock : true; timing () { timing_type : max_clock_tree_path; } } } }\n'
REFS = {"he": dict(tt=465.39, ff=361.26, source="core_latency.contract.io_reference_ps"),
        "hw": dict(tt=465.39, ff=361.26, source="core_latency.contract.io_reference_ps"),
        "idx": dict(tt=722.72, ff=592.8, source="insertion_band.corners.bound_ps")}


def plan(tmp_path):
    lib = tmp_path / "half_tt.lib"
    lib.write_text(LIB)
    core = lambda i, m: dict(inst=i, module=m, lib=str(lib))
    half_taps = lambda i: [dict(name=i + ".ck", kind="core", xy=[1, 1], insertion_ps=437.413, insertion_ff_ps=348.735, budget_owner="old"),
                           dict(name=i + ".clk", kind="core", xy=[2, 2], insertion_ps=532.99335, budget_owner="lib")]
    return {"note": "", "partition_types": {
        "col_a": dict(hard_cores=[core("u_w", "ot_v41_rom_elem_q_qxpq_w10_gb_hw"), core("u_e", "ot_v41_rom_elem_q_qxpq_w10_gb_he")],
                      clock=dict(core_taps="early", taps=half_taps("u_w") + [dict(name="u_e.ck", kind="core", xy=[3, 3], insertion_ps=476.052, insertion_ff_ps=382.22),
                                                                          dict(name="u_e.clk", kind="core", xy=[4, 4], insertion_ps=553.17902)])),
        "bk_sel__t2": dict(hard_cores=[core("u_bk_sel.u_tx", "dsdv_idx_tx_n32"), core("u_bk_sel.u_c", "dsdv_bksel_c")],
                           clock=dict(core_taps="early", taps=[dict(name="u_bk_sel.u_tx.ck", kind="core", xy=[5, 5], insertion_ps=829.1, insertion_ff_ps=665.2),
                                                                dict(name="u_bk_sel.u_c.ck", kind="core", xy=[6, 6], insertion_ps=442.81, insertion_ff_ps=353.98)]))}}


def test_halves_get_one_row_at_the_signed_reference(tmp_path):
    p = plan(tmp_path)
    rep = TR.apply(p, REFS, root=str(tmp_path))
    taps = p["partition_types"]["col_a"]["clock"]["taps"]
    assert sorted(t["name"] for t in taps) == ["u_e.clk", "u_w.clk"]          # the twin (.ck) rows are gone, the view's pin name stays
    assert all(t["insertion_ps"] == 465.39 and t["insertion_ff_ps"] == 361.26 for t in taps)
    assert {t["name"]: t["xy"] for t in taps} == {"u_e.clk": [4, 4], "u_w.clk": [2, 2]}
    assert rep["halves"] == {"he": 1, "hw": 1} and rep["rows_deleted"] == 2


def test_bksel_budget_450_and_idx_tap_at_its_reference(tmp_path):
    p = plan(tmp_path)
    TR.apply(p, REFS, root=str(tmp_path))
    ck = p["partition_types"]["bk_sel__t2"]["clock"]
    assert ck["insertion_ps"] == 450 and ck["insertion_target_override"]["reason"].strip()
    by = {t["name"]: t for t in ck["taps"]}
    assert (by["u_bk_sel.u_tx.ck"]["insertion_ps"], by["u_bk_sel.u_tx.ck"]["insertion_ff_ps"]) == (722.72, 592.8)
    assert by["u_bk_sel.u_c.ck"]["insertion_ps"] == 442.81                     # other cores untouched


def test_refuses_a_delta_with_nothing_to_edit(tmp_path):
    import pytest
    p = plan(tmp_path)
    p["partition_types"]["col_a"]["hard_cores"] = []
    with pytest.raises(SystemExit):
        TR.apply(p, REFS, root=str(tmp_path))


def test_reference_comes_from_the_signed_record(tmp_path):
    f = tmp_path / "signoff.json"
    f.write_text(json.dumps(dict(verdict="SIGNED", core_latency=dict(contract=dict(io_reference_ps=dict(tt=465.39, ff=361.26))))))
    assert TR._ref(f)["tt"] == 465.39


def test_bksel_q_rows_take_the_b1c_reference(tmp_path):
    p = plan(tmp_path)
    ck = p["partition_types"]["bk_sel__t2"]
    ck["hard_cores"].append(dict(inst="u_bk_sel.u_sel.g_q[0].u_q", module="dsdv_bksel_q", lib=str(tmp_path / "half_tt.lib")))
    ck["clock"]["taps"].append(dict(name="u_bk_sel.u_sel.g_q[0].u_q.ck", kind="core", xy=[7, 7], insertion_ps=651.6, insertion_ff_ps=527.5))
    rep = TR.apply(p, REFS, root=str(tmp_path), bksel=dict(tt=790.1, ff=640.0, basis="x"))
    by = {t["name"]: t for t in ck["clock"]["taps"]}
    q = by["u_bk_sel.u_sel.g_q[0].u_q.ck"]
    assert (q["insertion_ps"], q["insertion_ff_ps"]) == (790.1, 640.0) and ck["clock"]["insertion_ps"] == 450 and len(rep["bksel_q"]) == 1
