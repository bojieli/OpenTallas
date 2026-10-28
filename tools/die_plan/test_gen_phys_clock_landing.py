"""DIE-HEAD-4b gen phys --clock-landing (opt-in): kits take the landed wrapper + exactly the ring RTL it instantiates."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import gen_rtl  # noqa: E402

ROOT = HERE.parent.parent


def test_landing_rtl_picks_only_instantiated_ring_files():
    assert gen_phys.landing_rtl(ROOT, "module w;\n    ot_dp_st #(.W(1)) u (.d(a));\nendmodule\n") == []
    got = gen_phys.landing_rtl(ROOT, "module w;\n    ot_dp_clk_landing #(.W(5)) u_cland_y (\n    );\nendmodule\n")
    assert [p.name for p in got] == ["ot_dp_clk_landing.sv", "ot_meso_fifo.sv"]
    got = gen_phys.landing_rtl(ROOT, "    ot_dp_clk_landing_ca #(.W(5), .K(2)) u_cland_y (\n")
    # the CA ring also uses ot_dp_landing_fault_port (defined in ot_dp_clk_landing.sv)
    assert [p.name for p in got] == (["ot_dp_clk_landing.sv", "ot_dp_clk_landing_ca.sv", "ot_meso_fifo.sv"]
                                     if (ROOT / "rtl/common/ot_dp_clk_landing_ca.sv").is_file() else [])


def test_landing_refuses_kit_rtl(tmp_path):
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    with pytest.raises(gen_rtl.GenError, match="kit-rtl"):
        gen_phys.write_phys(raw, tmp_path, trial=True, kit_rtl={"mid": str(tmp_path / "x.f")}, landing={})


def test_landing_needs_a_composed_plan(tmp_path):
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    with pytest.raises(gen_rtl.GenError, match="landing_network"):
        gen_phys.write_phys(raw, tmp_path, trial=True, landing={"ports": []})
