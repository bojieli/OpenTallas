"""kit_contract._plan_contents: a contents entry with a kit-only physical specialization (physical_inst +
physical_master, DIE-KV-47 SD PHY re-site 10-30) is keyed by its physical instance with its physical master;
every other entry keeps its logical inst; an entry with only one of the two fields stays logical."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_contract as KC  # noqa: E402


def _write(tmp_path, contents):
    kd = tmp_path / "kit"
    pd = tmp_path / "plan"
    kd.mkdir()
    pd.mkdir()
    (kd / "budget.json").write_text(json.dumps({"type": "t_sd"}))
    (pd / "die_plan.json").write_text(json.dumps({"partition_types": {"t_sd": {"contents": contents}}}))
    return kd, pd


def test_physical_inst_keys_entry_with_physical_master(tmp_path):
    phy = dict(inst="u_phy_logical", module="ot_pdie_serdes", outline_um=[10.0, 20.0], origin_um=[1.0, 2.0],
               physical_inst="u_bound.u_core.u_phy.g_native.u_macro", physical_master="fixed_w522")
    sram = dict(inst="u_sram", module="sram", outline_um=[5.0, 5.0], origin_um=[0.0, 0.0])
    kd, pd = _write(tmp_path, [phy, sram, dict(inst="u_no_outline", module="x"), "junk"])
    got = KC._plan_contents(kd, pd)
    assert set(got) == {"u_bound.u_core.u_phy.g_native.u_macro", "u_sram"}
    p = got["u_bound.u_core.u_phy.g_native.u_macro"]
    assert p["inst"] == "u_bound.u_core.u_phy.g_native.u_macro" and p["module"] == "fixed_w522"
    assert p["outline_um"] == [10.0, 20.0] and p["origin_um"] == [1.0, 2.0]
    assert got["u_sram"] is not None and got["u_sram"]["module"] == "sram"
    assert phy["inst"] == "u_phy_logical"  # plan entry itself is not mutated


def test_partial_physical_identity_stays_logical(tmp_path):
    a = dict(inst="u_a", module="m_a", outline_um=[1.0, 1.0], physical_inst="u_bound.u_a")
    b = dict(inst="u_b", module="m_b", outline_um=[1.0, 1.0], physical_master="fixed_b")
    kd, pd = _write(tmp_path, [a, b])
    got = KC._plan_contents(kd, pd)
    assert set(got) == {"u_a", "u_b"}
    assert got["u_a"]["module"] == "m_a" and got["u_b"]["module"] == "m_b"


def test_missing_plan_or_type_returns_none(tmp_path):
    kd, pd = _write(tmp_path, [])
    assert KC._plan_contents(kd, None) is None
    assert KC._plan_contents(kd, tmp_path / "nowhere") is None
    (kd / "budget.json").write_text(json.dumps({"type": "other"}))
    assert KC._plan_contents(kd, pd) is None
