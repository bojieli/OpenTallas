"""pytest: ADV-BANK-SPAN (HEAD W4b hd_lep0N_w u_rg2 g_bank[3] 480 um write leg, -151 ps)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_bank_span as A  # noqa: E402


def bank(p, k, x, y):
    return {"inst": f"{p}.g_bank[{k}].u_m", "origin_um": [x, y], "outline_um": [169.368, 29.16], "orient": "R0"}


def plan(xs):
    return {"partition_types": {"t": {"hard_cores": [bank("u_m", k, x, y) for k, (x, y) in enumerate(xs)]}}}


def test_column_is_clean_and_outlier_flags():
    col = [(100.0, 500.0 + 43.2 * k) for k in range(5)]
    assert A.findings(plan(col), "p") == []
    far = col[:4] + [(600.0, 500.0)]
    lines = A.findings(plan(far), "p")
    assert len(lines) == 1 and "FAIL-SPAN" in lines[0] and "g_bank[4]" in lines[0]
    mid = col[:4] + [(370.0, 500.0)]
    assert "WIDE" in A.findings(plan(mid), "p")[0]


def test_escaped_names_and_single_bank_ignored():
    p = plan([(0.0, 0.0), (500.0, 0.0)])
    p["partition_types"]["t"]["hard_cores"][1]["inst"] = "u_m.g_bank\\[1\\].u_m"
    assert "FAIL-SPAN" in A.findings(p, "p")[0]
    assert A.findings(plan([(0.0, 0.0)]), "p") == []
