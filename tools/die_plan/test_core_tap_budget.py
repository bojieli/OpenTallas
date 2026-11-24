"""CORE-TAP-BUDGET 11-24 (FABLE-RC-ALL 701c4a59): early core taps without a SIGNED/parent_budget owner (legacy kit path).

HEAD hd_lep0N / hd_lep0N_w: no budget_owner -> core_latency.txt aimed the pair-core pin at the liberty ETM max 612.07 while
the tap (SDC source latency) carried 553.42 (signed contract 558.17 / 451.18): 58.65 ps early pair-core clock."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "precheck"))
import core_clock_contract as CC  # noqa: E402
import core_tap_retarget as RT  # noqa: E402
import gen_phys as G  # noqa: E402
import precheck as PC  # noqa: E402


def core(tmp_path):
    lib = tmp_path / "node_tt.lib"
    lib.write_text('''library(node) { time_unit : "1ps"; cell(node) { pin(clk) {
      direction : input;
      clock : true;
      timing() { timing_type : max_clock_tree_path;
        cell_rise(scalar) { values("267.63"); } cell_fall(scalar) { values("280"); }
      }
    } } }''')
    return dict(inst="u_node", module="node", lib=str(lib))


def signed(tmp_path):
    (tmp_path / "signoff.json").write_text(json.dumps(dict(verdict="SIGNED", corners={
        c: dict(done=True, design="node", parasitics="spef", clock_ports=["clk"],
                insertion_pinflops=dict(n=2058, mean=m, min=m - 15, max=m + 17))
        for c, m in [("tt", 245.9), ("ff", 199.6)]})))


def plan(c, **tap):
    tp = dict(name="u_node.clk", kind="core", xy=[1, 1], insertion_ps=245.9, insertion_ff_ps=199.6, **tap)
    return SimpleNamespace(types={"tile": dict(hard_cores=[c], clock=dict(core_taps="early", taps=[tp]))},
                           clock=dict(insertion_ps=250.))


def rows_of(p, tmp_path, monkeypatch):
    monkeypatch.setattr(G, "core_tap_rows", lambda *_a, **_k: [("clk_c0", "u_node", "clk", 0., 245.9)])
    out = tmp_path / "kit"
    out.mkdir(exist_ok=True)
    G.core_latency_files(p, "tile", out, **G.core_mean_contract_options(p, "tile"))
    return (out / "core_latency.txt").read_text().splitlines(), json.loads((out / "core_latency.json").read_text())["rows"]


def test_legacy_tapped_pin_takes_tap_insertion_not_etm_max(tmp_path, monkeypatch):
    p = plan(core(tmp_path))                     # no budget_owner: the HEAD hd_lep0N form
    assert G.core_mean_contract_options(p, "tile") == dict(mean_contract=False, require_signed=True)
    txt, rows = rows_of(p, tmp_path, monkeypatch)
    assert "u_node clk 245.9 clk_c0" in txt      # was 267.63 (ETM max): 21.73 ps pin-vs-tap error
    assert rows[0]["etm_max_bound_ps"] == 267.63 and rows[0]["basis"] == "plan_core_tap_insertion"
    assert rows[0]["signed"] is False and rows[0]["release_qualified"] is False


def test_legacy_untapped_pin_keeps_etm_bound():
    rows = [dict(inst="u_a", pin="clk", rise_ps=612.07, fall_ps=600., tap="clk_c0"),
            dict(inst="u_b", pin="clk", rise_ps=300., fall_ps=300., tap="grid")]
    ch = G.legacy_core_tap_targets("T", rows, [("clk_c0", "u_a", "*", 0., 553.42)])
    assert [r["inst"] for r in ch] == ["u_a"] and rows[0]["rise_ps"] == 553.42 and rows[0]["etm_max_bound_ps"] == 612.07
    assert rows[1] == dict(inst="u_b", pin="clk", rise_ps=300., fall_ps=300., tap="grid")


def test_signed_owner_takes_mean_path(tmp_path, monkeypatch):
    c = core(tmp_path)
    signed(tmp_path)
    p = plan(c, budget_owner="SIGNED: node signoff.json")
    assert G.core_mean_contract_options(p, "tile") == dict(mean_contract=True, require_signed=True)
    txt, rows = rows_of(p, tmp_path, monkeypatch)
    assert txt[0].startswith("# inst pin mean_pin_register_insertion_ps") and "u_node clk 245.9 clk_c0" in txt
    assert rows[0]["signed"] is True


def test_precheck_flags_unowned_core_tap_only(tmp_path, monkeypatch):
    c = core(tmp_path)
    signed(tmp_path)
    monkeypatch.setattr(G, "core_tap_rows", lambda *_a, **_k: [("clk_c0", "u_node", "clk", 0., 245.9)])
    f = PC.core_tap_owner_findings(plan(c), "tile")
    assert len(f) == 1 and f[0][0] == 1
    assert "owners: NONE" in f[0][1] and "ETM-tap +21.73" in f[0][1] and "plan-signed +0.00" in f[0][1]
    assert PC.core_tap_owner_findings(plan(c, budget_owner="SIGNED: x"), "tile") == []
    assert PC.core_tap_owner_findings(plan(c, budget_owner="parent_budget pin mean"), "tile") == []
    other = PC.core_tap_owner_findings(plan(c, budget_owner="physical/x/views/node_tt.lib"), "tile")
    assert other and "physical/x/views/node_tt.lib" in other[0][1]
    assert "CORE-TAP-OWNER" in PC.CHECKS and "CORE-TAP-OWNER" not in PC.OPT_IN


def test_retarget_apply_stamps_owner_on_keep_rows():
    raw = dict(partition_types={"tile": dict(clock=dict(taps=[
        dict(name="u_a.clk", kind="core", insertion_ps=558.0, insertion_ff_ps=451.0),
        dict(name="u_b.clk", kind="core", insertion_ps=558.17, insertion_ff_ps=451.18, budget_owner="SIGNED:old")]))})
    row = dict(type="tile", status="KEEP", basis="mean", signed_mean_TT=558.17, new_ins_TT=558.17, new_ins_FF=451.18,
               old_early_TT=0, new_early_TT=0, source="vE28s clock_contract.json")
    n = RT.apply_rows(raw, [dict(row, tap="u_a.clk"), dict(row, tap="u_b.clk"),
                            dict(row, tap="u_a.clk", status="UNSIGNED", signed_mean_TT=None)])
    a, b = raw["partition_types"]["tile"]["clock"]["taps"]
    assert n == 1 and a["budget_owner"] == "SIGNED:vE28s clock_contract.json" and a["insertion_ps"] == 558.17
    assert b["budget_owner"] == "SIGNED:old"


def test_native_sram_head_new_shape_spec_from_sheet(tmp_path):
    d = tmp_path / "ot_sram_1r1w_32x128_m1_r0c0"
    d.mkdir()
    sheet = dict(generator="tools/mem_compiler/sram_gen.py v1.0+aligned-v2",
                 spec=dict(name="ot_sram_1r1w_32x128_m1_r0c0", words=32, bits=128),
                 alignment_v2=dict(kind="sram", head_new_shape=True, verification={"pass": True}))
    (d / "ot_sram_1r1w_32x128_m1_r0c0.json").write_text(json.dumps(sheet))
    c = dict(inst="u_m", module="ot_sram_1r1w_32x128_m1_r0c0", lib=str(d / "ot_sram_1r1w_32x128_m1_r0c0_tt.lib"))
    with pytest.raises(CC.ContractError, match="selected corner absent"):    # past the identity check, into the views
        CC.native_memory_clock_model(c)
    sheet["spec"]["name"] = "other"
    (d / "ot_sram_1r1w_32x128_m1_r0c0.json").write_text(json.dumps(sheet))
    with pytest.raises(CC.ContractError, match="identity/verification missing"):
        CC.native_memory_clock_model(c)


def test_legacy_tapped_pin_prefers_signed_view_mean(tmp_path, monkeypatch):
    c = core(tmp_path)
    signed(tmp_path)                             # view SIGNED mean 245.9; the plan tap is stale (240) and unowned
    p = plan(c)
    p.types["tile"]["clock"]["taps"][0]["insertion_ps"] = 240.0
    monkeypatch.setattr(G, "core_tap_rows", lambda *_a, **_k: [("clk_c0", "u_node", "clk", 0., 240.0)])
    out = tmp_path / "kit2"
    out.mkdir()
    G.core_latency_files(p, "tile", out, **G.core_mean_contract_options(p, "tile"))
    assert "u_node clk 245.9 clk_c0" in (out / "core_latency.txt").read_text()
    row = json.loads((out / "core_latency.json").read_text())["rows"][0]
    assert row["basis"] == "signed_view_mean" and row["etm_max_bound_ps"] == 267.63 and row["signed"] is False
