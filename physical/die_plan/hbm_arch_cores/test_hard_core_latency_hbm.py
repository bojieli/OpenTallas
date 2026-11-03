"""DIE-HBM-60/CORES 11-03 (class CLK-BAND): opt-in typed hard_core_latency clock contract for HBM core kits.

Default kits keep the old declaration (no clock_contract -> insertion band gates, vclk_ref rebind).  With
--hard-core-latency (or --retrofit-boundary KIT --hard-core-latency) core.json carries the COORD 10-24 contract the
KV/S81 generators write, so the existing readers pick the existing approved policy: core_clock_band info,
vclk_ref bound-ff.  No reader or gate is changed."""
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
spec = importlib.util.spec_from_file_location("coregen_hcl", HERE / "gen_core_kit_hbm.py")
coregen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coregen)
sys.path.insert(0, str(REPO / "tools/die_plan"))
import vclk_ref  # noqa: E402


def _kit(tmp, contract):
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "sdc_lint.json").write_text(json.dumps(dict(time_unit_ps=1.0, insertion_ff_ps=202.5, insertion_tol_ps=40)))
    coregen.write_boundary_context(tmp, ["clk", "clk_q[0]", "clk_q[1]"], ["rst_n"], contract)
    return tmp


def test_default_unchanged(tmp_path):
    kd = _kit(tmp_path / "a", False)
    cj = json.loads((kd / "core.json").read_text())
    assert "clock_contract" not in cj and cj["boundary_role"] == {"clk": "clk", "clk_q": "clk", "rst_n": "reset"}
    assert vclk_ref.hard_core_latency_contract(kd) is None
    assert vclk_ref.ff_reference(kd)["ref"] == "rebind"


def test_contract_opt_in(tmp_path):
    kd = _kit(tmp_path / "b", True)
    cc = json.loads((kd / "core.json").read_text())["clock_contract"]
    assert cc["kind"] == "hard_core_latency" and cc["ruling"] == "COORD 10-24"
    assert vclk_ref.ff_reference(kd)["ref"] == "bound-ff"
    import core_clock_band
    assert core_clock_band.band_policy(kd) == "info"


def test_retrofit_ledger(tmp_path):
    kd = tmp_path / "c"
    kd.mkdir()
    (kd / "freeze.json").write_text(json.dumps(dict(schema="opentallas.hbm_arch.core_freeze.v1", clocks=["clk"],
                                                     resets=["rst_n"])))
    coregen.retrofit_boundary_context(kd, True)
    led = json.loads((kd / "contract_retrofit.json").read_text())
    assert led["clock_contract"]["kind"] == "hard_core_latency" and led["clock_ports"] == ["clk"]
    assert json.loads((kd / "core.json").read_text())["clock_contract"] == led["clock_contract"]
