"""FLOW-HEALTH-1 11-16 (COORD, OWNER 11-14 "delete, not loosen, the GRT early stop"): a generated kit has no GRT iteration cap and no early / congested stop;
the skew check covers the kit scripts so a die tree that predates the deletion is seen."""
import re
from pathlib import Path

import flow_guard as FG

ROOT = Path(__file__).resolve().parents[2]
KIT_FILES = [ROOT / rel for rel in FG.KIT_SCRIPTS] + [ROOT / "tools/die_plan/core_flow.py", ROOT / "tools/die_plan/gen_phys.py",
                                                      ROOT / "physical/die_plan/hbm_arch_cores/run_kit_hbm.sh",
                                                      ROOT / "physical/die_plan/qwen_kvsys/cores/harden/run_kit_kv.sh"]
STOP_ENV = re.compile(r"OT_GRT_EARLY_STOP|OT_GRT_CONGESTED_FAIL|GRT_EARLY_RULE|grt_early_stop|early_off\b|cong_off\b|GRT_NO_PROGRESS")
ITER_CAP = re.compile(r"congestion_iterations\s+\d+|-grt_iterations\s+\d+|OT_GRT_MAX_ITER\w*\s*[:=]\s*\d+")


def code(p):
    return [ln for ln in p.read_text(errors="replace").splitlines() if ln.strip() and not ln.strip().startswith("#")]


def test_no_grt_stop_env_or_function_in_the_kit_scripts():
    bad = [f"{p.name}: {ln.strip()[:110]}" for p in KIT_FILES if p.is_file() for ln in code(p) if STOP_ENV.search(ln) and "REMOVED" not in ln]
    assert not bad, bad


def test_no_numeric_grt_iteration_cap_in_the_kit_scripts():
    bad = [f"{p.name}: {ln.strip()[:110]}" for p in KIT_FILES if p.is_file() for ln in code(p) if ITER_CAP.search(ln)]
    assert not bad, bad


def test_failfast_defaults_have_no_grt_rule():
    assert not [k for k in re.findall(r"\"(OT_FF_[A-Z_]+)\"", (ROOT / "physical/common_flow/failfast_rules.py").read_text().split("DEFAULTS = {")[1].split("}")[0])
                if "GRT" in k]


def test_the_judge_never_stops_grt_on_overflow(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("ff", str(ROOT / "physical/common_flow/failfast_rules.py"))
    ff = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ff)
    lg = tmp_path / "run/logs/asap7/x/base"
    lg.mkdir(parents=True)
    (lg / "5_1_grt.log").write_text("[INFO GRT-0101] Running extra iterations to remove congestion.\n" + "".join(
        "[INFO GRT-0102] Start extra iteration %d/30\n" % i for i in range(1, 16)) + "Total 100 90 10.00% 90000 / 1 / 1\n")
    (tmp_path / "config.mk").write_text("export DESIGN_NAME = x\n")
    assert ff.judge(str(tmp_path), 0, None, env={}, settle_s=0) == []


def test_skew_covers_the_kit_scripts():
    seen = []

    def rpy(h, code, args, timeout=0):
        seen.append(args["files"])
        return {f: "x" for f in args["files"]}
    rows = FG.skew_report([("s81", "/t")], lambda rel: "m", lambda rel: "import os\n" if rel.endswith("gen.py") else None, rpy, {"s81": ["h"]})
    assert all(f in seen[0] for f in FG.KIT_SCRIPTS)
    assert rows and set(FG.KIT_SCRIPTS) <= set(rows[0][3])             # a tree whose kit scripts differ from main is listed
