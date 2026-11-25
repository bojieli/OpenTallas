"""ADV-MACRO-CHANNEL: pass (wide / abutted / disjoint) plus mutant (narrow channel)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_macro_channel as M  # noqa: E402
import plan_advisory as PA  # noqa: E402


def core(name, x, y, w=100.0, h=100.0, orient="R0"):
    return {"inst": name, "origin_um": [x, y], "outline_um": [w, h], "orient": orient}


def run(*cores):
    return M.findings({"partition_types": {"ty": {"outline_um": [1000.0, 1000.0], "hard_cores": list(cores)}}}, "p")


def test_wide_abutted_and_disjoint_are_silent():
    assert run(core("a", 0, 0), core("b", 0, 100 + 14.88)) == []          # exactly the minimum
    assert run(core("a", 0, 0), core("b", 100, 0)) == []                 # abutted
    assert run(core("a", 0, 0), core("b", 0, 100 + 5), ) != []            # sanity: 5 um is narrow
    assert run(core("a", 0, 0), core("b", 105, 205)) == []               # diagonal, no shared run


def test_mutant_8p16_channel_reported():
    out = run(core("a", 0, 0), core("b", 10, 100 + 8.16))
    assert out[0].startswith("WARN ADV-MACRO-CHANNEL ty: 1 core pair(s) with a channel < 14.88 um (min 8.16)")
    assert "a / b 8.16 um over 90 um (EW)" in out[0] and out[-1].startswith("LIST ADV-MACRO-CHANNEL 1 type(s), 1 narrow")


def test_ns_channel_rotation_and_short_run():
    assert M.channels({"hard_cores": [core("a", 0, 0, 100, 40, "R90"), core("b", 40 + 6, 0, 10, 50)]})[0][4] == "NS"   # R90: a is 40 x 100
    assert M.channels({"hard_cores": [core("a", 0, 0), core("b", 90, 105)]}) == []                                   # run 10 um < 20


def test_registered():
    assert ("MACRO-CHANNEL", "adv_macro_channel") in PA.CHECKS


def test_small_overlap_mutant_and_clean():
    out = run(core("a", 0, 0), core("b", 0, 99.976))        # 0.024 um overlap, the 32x64 SRAM stack case
    assert any(x.startswith("WARN ADV-MACRO-CHANNEL ty: 1 core pair(s) overlap by <= 0.5 um (max 0.024") for x in out)
    assert not any("overlap" in x for x in run(core("a", 0, 0), core("b", 0, 100)))        # abutted
