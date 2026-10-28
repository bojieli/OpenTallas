"""FLOW-GEN-2 (d) (COORD 10-28 all-die sweep of HBM-CORES-REBAL-8): every core-kit generator times its reset pins
with the ONE shared rule gen_phys.core_reset_sdc -- a synchronous input from the die reset tree under the normal data
IO budget (the $non_clk_in max/min lines), no reset-specific input delay (the old 0.5 T line)."""
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys  # noqa: E402

PER = 833.0
RSTS = ["rst_n", "u_a__rst_n"]


def _load(rel):
    sp = importlib.util.spec_from_file_location("rstio_" + re.sub(r"\W", "_", rel), ROOT / rel)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def _reset_delays(text, rsts):
    """set_input_delay commands that name a reset port explicitly (the reset-specific override)."""
    return [ln for ln in text.splitlines() if ln.startswith("set_input_delay") and "get_ports" in ln
            and any(r in re.search(r"get_ports \{?([^}\]]*)", ln).group(1).split() for r in rsts)]


def _check(text, rsts=RSTS):
    assert _reset_delays(text, rsts) == [], text
    assert gen_phys.core_reset_sdc(rsts, PER) in text
    assert re.search(r"^set_input_delay (-max )?166\.6000 -clock vclk \$non_clk_in$", text, re.M), text
    assert "416.5" not in text and "recovery at 1 T" not in text


def test_shared_rule():
    assert gen_phys.core_reset_sdc([], PER) == ""
    r = gen_phys.core_reset_sdc(RSTS, PER)
    assert r == "# reset rst_n u_a__rst_n: wavefront relay -> registered synchronous input, data IO budget (166.6000)\n"
    assert not any(ln and not ln.startswith("#") for ln in r.splitlines())   # comment only: the IO lines time it


def test_hbm_harden():
    _check(_load("physical/die_plan/hbm/cores/harden/gen_core_kit.py").sdc(PER, 250.0, ["clk"], RSTS, "t"))


def test_hbm_arch_cores():
    m = _load("physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py")
    text = m.sdc(PER, 250.0, 40.0, ["clk"], ["rst_n", "u_a__rst_n[0]", "u_a__rst_n[1]"], "t")
    _check(text, ["rst_n", "u_a__rst_n"])
    assert text.count("# reset ") == 1
    assert "0.5 * per" not in (ROOT / "physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py").read_text()


def test_kv_harden():
    _check(_load("physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py").sdc(PER, 250.0, 40.0, ["clk"], RSTS, "t"))


def test_s81_eng():
    _check(_load("physical/die_plan/s81/cores/eng/gen_core_kit.py").sdc(["clk"], RSTS, "t"))


def test_s81_legacy():
    _check(_load("physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py").sdc(PER, 250.0, 40.0, ["clk"], RSTS, "t"))


def test_s81_svc():
    _check(_load("physical/die_plan/s81/cores/svc/gen_core_kit_s81.py").sdc(PER, 250.0, ["clk"], RSTS, "t"))


def test_qc_legacy():
    _check(_load("physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py").sdc(PER, 250.0, 40.0, ["clk"], RSTS, "t"))


def test_kv_pvpc_std_sdc():
    out = subprocess.run([sys.executable, str(ROOT / "physical/die_plan/qwen_kvsys/cores/harden/pvpc_1025/std_sdc.py"),
                          "clk", "rst_n", "0"], check=True, capture_output=True, text=True).stdout
    _check(out, ["rst_n"])


def test_s81_head_elemA_rebuild_uses_rule():
    src = (ROOT / "tools/s81_head/hd_elemA_rebuild.py").read_text()
    assert "gen_phys.core_reset_sdc" in src and "416.5000 -clock vclk [get_ports {{rst_n}}]" not in src


def test_no_generator_keeps_a_reset_copy():
    """sweep: no core-kit generator under physical/die_plan still writes the 0.5 T reset input delay."""
    hits = [str(p.relative_to(ROOT)) for p in (ROOT / "physical/die_plan").rglob("*.py")
            if "recovery at 1 T" in p.read_text(errors="replace")]
    assert hits == [], hits
