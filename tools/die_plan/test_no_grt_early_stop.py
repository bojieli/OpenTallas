"""WF-1 11-14 (OWNER 11-14: delete the GRT early congestion stop, do not loosen it): no overflow-based GRT stop remains in the tree;
the only GRT stop is the post-route time cap OT_GRT_POST_MAX_S."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEN = ["physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py", "physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py",
       "physical/die_plan/hbm_arch_cores/run_kit_hbm.sh", "physical/die_plan/qwen_kvsys/cores/harden/run_kit_kv.sh",
       "tools/die_plan/gen_phys.py", "tools/die_plan/core_flow.py",
       "physical/common_flow/grt183_make.sh", "physical/common_flow/grt_stall_resume.tcl"]
ACTIVE_BAD = re.compile(r"early congestion stop|OT_GRT_EARLY(?!_SETTLE)|OT_GRT_CONGESTED_FAIL\s*[=:]|GRT_NO_PROGRESS|grt_early_stop")


def code_lines(text):
    for ln in text.splitlines():
        s = ln.strip()
        if s and not s.startswith("#"):
            yield ln


def test_no_active_early_stop_guard_in_the_generators_and_wrappers():
    bad = []
    for rel in GEN:
        p = ROOT / rel
        if not p.is_file():
            continue
        for ln in code_lines(p.read_text(errors="replace")):
            if ACTIVE_BAD.search(ln) and "REMOVED" not in ln:
                bad.append(f"{rel}: {ln.strip()[:120]}")
    assert not bad, bad


def test_early_stop_module_is_gone():
    assert not (ROOT / "tools/autopilot/grt_early_stop.py").exists()


def test_grt183_make_has_only_the_time_cap_stop():
    t = (ROOT / "physical/common_flow/grt183_make.sh").read_text()
    stops = re.findall(r"gstop=(\w+)", "\n".join(code_lines(t)))
    # gstop also carries the DRT / hold-structural stops of other stages; the only GRT stop is the post-route time cap
    assert "timecap" in stops and not [s for s in stops if "grt" in s.lower() or "overflow" in s.lower() or "congest" in s.lower()], stops
    assert "OT_GRT_TIMECAP" in t and "OT_GRT_POST_MAX_S" in t


def test_failfast_grt_rule_is_deleted_not_disabled():
    import importlib.util
    spec = importlib.util.spec_from_file_location("ff_rules", ROOT / "physical/common_flow/failfast_rules.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert not hasattr(mod, "grt_decide") and not hasattr(mod, "grt_line")
    assert not [k for k in mod.DEFAULTS if k.startswith("OT_FF_GRT")]
    src = (ROOT / "physical/common_flow/failfast_rules.py").read_text()
    assert "GRT_NO_PROGRESS" not in "\n".join(code_lines(src)) and "OT_FF_GRT" not in "\n".join(code_lines(src))
