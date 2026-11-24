"""pytest: ADV-CTLM-AGES on the QC C1g tt_ctlm positive (program 19/19/17/17 vs delivered 14/10; core XPF 21 vs 1 + R_HR = 20)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_ctlm_ages as A  # noqa: E402


def test_c1g_positive():
    r = A.judge({"R_CMD": 19, "R_HR": 19, "R_SS": 17, "R_AG": 17}, 20, {"core_1": 21}, {"R_CMD": 14, "R_HR": 10})
    kinds = [k for k, _ in r]
    assert kinds.count("AGE") == 2 and "XPF-CORE" in kinds and "XPF-PROG" not in kinds
    assert any("21 != 1 + program R_HR 19 = 20" in t for _, t in r)


def test_consistent_program_passes():
    assert A.judge({"R_CMD": 14, "R_HR": 10, "R_ST": 10}, 11, {"core_1": 11}, {"R_CMD": 14, "R_HR": 10, "R_ST": 10}) == []


def test_xpf_rule_on_program_value():
    assert [k for k, _ in A.judge({"R_HR": 19}, 21, {}, {})] == ["XPF-PROG"]


def test_never_raises():
    assert A.findings({}, "p", None)[0].startswith("WARN ADV-CTLM-AGES not checked")
