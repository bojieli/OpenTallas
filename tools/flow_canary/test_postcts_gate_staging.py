"""FLOW-21 CCBAND 11-01: postcts_gate.tcl imports core_clock_band (25552a564); every kit generator that stages the gate
stages the module, and a crashed gate is a flow (tcl_errors) failure in the canary, not a design stop."""
import importlib.util
import json
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("canary_ccband", ROOT / "tools/flow_canary/canary.py")
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)
GENERATORS = ("tools/die_plan/gen_phys.py", "physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py",
              "physical/die_plan/hbm_arch_cores/kit_tkm_noid.py", "physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py")


def test_gate_imports_core_clock_band():
    assert "import core_clock_band" in (ROOT / "tools/die_plan/postcts_gate.tcl").read_text()


def test_every_generator_stages_core_clock_band_with_the_gate():
    for g in GENERATORS:
        text = (ROOT / g).read_text()
        lists = [m.group(0) for m in re.finditer(r"[\(\[][^\(\)\[\]]*postcts_gate\.tcl[^\(\)\[\]]*[\)\]]", text)
                 if "copyfile" in text[m.end():m.end() + 300] or ":shutil" in text[m.end():m.end() + 8]
                 or "for f in" in text[max(0, m.start() - 40):m.start()]]
        assert lists, g
        assert all("core_clock_band.py" in l for l in lists), (g, lists)


def test_crashed_postcts_gate_is_a_tcl_error(tmp_path):
    kit = tmp_path / "kit"
    logs = kit / "run/logs/asap7/d/base"
    logs.mkdir(parents=True)
    (kit / "config.mk").write_text("export LAYER_PARASITICS_FILE = /work/setRC_rcx.tcl\n")
    (kit / "postcts_gate_TT.log").write_text(
        "Error: postcts_gate.tcl, 34 Traceback (most recent call last):\n"
        "ModuleNotFoundError: No module named 'core_clock_band'\nOT_POSTCTS_GATE TT no result FAIL\n")
    (tmp_path / "canary_meta.json").write_text(json.dumps(dict(kit=str(kit), spec=dict(die="s81_head", item="hd_turn_a"))))
    r = C.check_run(tmp_path)
    assert r["stages"]["tcl_errors"]["verdict"] == "FAIL" and "postcts_gate_TT.log" in r["stages"]["tcl_errors"]["why"]
