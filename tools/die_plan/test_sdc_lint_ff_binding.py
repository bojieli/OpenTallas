"""HBM-CORES-R6 10-27: a kit whose flow repairs FF hold against config.mk OT_VCLK_FF must carry the same per-corner FF
binding (insertion_ff_ps) in sdc_lint.json, the file signoff.py reads; otherwise sign-off silently times FF hold against
the single TT vclk (collar_idx256r R5 attempt 3: ff_ref_missing after a full route).  sdc_lint fails closed pre-synth.
    python3 -m pytest -q tools/die_plan/test_sdc_lint_ff_binding.py"""
import json
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import schema  # noqa: E402
import sdc_lint  # noqa: E402

TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())
HBM_GEN = HERE.parents[1] / "physical" / "die_plan" / "hbm_arch_cores" / "gen_core_kit_hbm.py"


def _kit(d):
    kd = gen_phys.write_type_kit(schema.Plan(TINY), "src", d, [])
    assert sdc_lint.kit_vclk_ff(kd) is not None          # gen_phys kits carry the per-corner binding
    return kd


def _ctx(kd, **edit):
    ctx = json.loads((kd / "sdc_lint.json").read_text())
    for k, v in edit.items():
        if v is None:
            ctx.pop(k, None)
        else:
            ctx[k] = v
    (kd / "sdc_lint.json").write_text(json.dumps(ctx))


def test_consistent_kit_passes():
    with tempfile.TemporaryDirectory() as d:
        assert sdc_lint.lint_kit_files(_kit(d)) == []


def test_missing_ff_binding_fails_closed():
    with tempfile.TemporaryDirectory() as d:
        kd = _kit(d)
        _ctx(kd, insertion_ff_ps=None)
        err = sdc_lint.lint_kit_files(kd)
        assert any("no insertion_ff_ps" in e and "ff_ref_missing" in e for e in err), err


def test_mismatched_ff_binding_fails():
    with tempfile.TemporaryDirectory() as d:
        kd = _kit(d)
        ctx = json.loads((kd / "sdc_lint.json").read_text())
        _ctx(kd, insertion_ff_ps=float(ctx["insertion_ff_ps"]) - 5.0)
        assert any("!= config.mk OT_VCLK_FF" in e for e in sdc_lint.lint_kit_files(kd))


def test_no_vclk_ff_no_obligation():
    with tempfile.TemporaryDirectory() as d:
        kd = _kit(d)
        cm = kd / "config.mk"
        cm.write_text(re.sub(r"(?m)^export OT_VCLK_FF.*\n", "", cm.read_text()))
        _ctx(kd, insertion_ff_ps=None)
        assert sdc_lint.kit_vclk_ff(kd) is None
        assert not any("OT_VCLK_FF" in e for e in sdc_lint.lint_kit_files(kd))


def test_override_and_last_assignment(tmp_path):
    (tmp_path / "config.mk").write_text("export OT_VCLK_FF = 190\noverride export OT_VCLK_FF = 202.5\n")
    assert sdc_lint.kit_vclk_ff(tmp_path) == 202.5
    assert sdc_lint.ff_binding_errors(tmp_path, dict(insertion_ff_ps=202.5, time_unit_ps=1.0)) == []
    assert sdc_lint.ff_binding_errors(tmp_path, dict(insertion_ff_ps=250.0, time_unit_ps=1.0))


def test_hbm_generator_keeps_ff_binding_in_lint_ctx():
    """the HBM core generator used to strip insertion_ff_ps from sdc_lint.json (collar R5 root cause)."""
    src = HBM_GEN.read_text()
    w = re.search(r'\(kd / "sdc_lint\.json"\)\.write_text\(json\.dumps\((\w+)', src)
    assert w and w.group(1) == "lint_ctx", "sdc_lint.json must be written from lint_ctx"
    m = re.search(r"lint_ctx = \{k: v for k, v in lctx\.items\(\) if (.+)\}", src)
    assert m and "insertion_ff_ps" not in m.group(1), m and m.group(1)
    assert "insertion_ff_ps=ff_ins" in src
