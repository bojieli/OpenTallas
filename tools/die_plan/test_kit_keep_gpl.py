"""KV-KITS-5 10-27: every generated kit carries the shared keep-register canonicalize hook (SYNTH_CANONICALIZE_TCL =
physical/common_flow/ot_keep_regs.tcl, COORD sys_c LEC ruling); --gpl-plain TYPES puts pure-FT corridor kits on
plain-wirelength GPL (GPL_ROUTABILITY_DRIVEN=0 / GPL_TIMING_DRIVEN=0) and refuses a type without ft slots.
    python3 -m pytest -q tools/die_plan/test_kit_keep_gpl.py"""
import json
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen  # noqa: E402
import gen_phys  # noqa: E402
import schema  # noqa: E402

TINY = HERE / "examples" / "tiny_plan.json"


def _P():
    return schema.Plan(json.loads(TINY.read_text()))


def test_kit_has_keep_regs_hook_and_its_helpers():
    with tempfile.TemporaryDirectory() as d:
        kd = gen_phys.write_type_kit(_P(), "mid", d, [])
        cfg = (kd / "config.mk").read_text()
        assert "export SYNTH_CANONICALIZE_TCL = /work/ot_keep_regs.tcl" in cfg
        src = HERE.parents[1] / "physical" / "common_flow"
        for f in gen_phys.KEEP_REGS_HOOK:
            assert (kd / f).read_bytes() == (src / f).read_bytes(), f
        # AUTOBUILD-PIPE-5 10-31 (OWNER 12.27): plain GPL is DEFAULT-ON for an ft_slots type (mid has ft slots)
        assert "export GPL_ROUTABILITY_DRIVEN = 0" in cfg and "export GPL_TIMING_DRIVEN = 0" in cfg


def test_gpl_plain_default_skips_types_without_ft_slots_and_opt_out():
    with tempfile.TemporaryDirectory() as d:
        cfg = (gen_phys.write_type_kit(_P(), "src", d, []) / "config.mk").read_text()
        assert "GPL_ROUTABILITY_DRIVEN" not in cfg and "GPL_TIMING_DRIVEN" not in cfg
    P = _P()
    P.budgets["gpl_plain_off_types"] = ["mid"]
    with tempfile.TemporaryDirectory() as d:
        cfg = (gen_phys.write_type_kit(P, "mid", d, []) / "config.mk").read_text()
        assert "GPL_ROUTABILITY_DRIVEN" not in cfg and "GPL_TIMING_DRIVEN" not in cfg


def test_gpl_plain_ft_corridor_kit():
    with tempfile.TemporaryDirectory() as d:
        cfg = (gen_phys.write_type_kit(_P(), "mid", d, [], gpl_plain=True) / "config.mk").read_text()
        assert "export GPL_ROUTABILITY_DRIVEN = 0" in cfg and "export GPL_TIMING_DRIVEN = 0" in cfg


def test_gpl_plain_refuses_type_without_ft_slots():
    with tempfile.TemporaryDirectory() as d:
        with pytest.raises(ValueError, match="pure-FT corridor"):
            gen_phys.write_type_kit(_P(), "src", d, [], gpl_plain=True)


def test_gen_phys_cli_gpl_plain_only_named_types():
    with tempfile.TemporaryDirectory() as d:
        assert gen.main(["phys", str(TINY), "--out", d, "--types", "mid,sink", "--gpl-plain", "mid", "--trial"]) == 0
        mid = (Path(d) / "mid" / "config.mk").read_text()
        sink = (Path(d) / "sink" / "config.mk").read_text()
        assert "GPL_ROUTABILITY_DRIVEN = 0" in mid
        assert ("GPL_ROUTABILITY_DRIVEN = 0" in sink) == bool(_P().types["sink"].get("ft_slots"))
        assert "SYNTH_CANONICALIZE_TCL = /work/ot_keep_regs.tcl" in sink
