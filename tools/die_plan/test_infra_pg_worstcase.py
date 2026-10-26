import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import infra_pg as I
import infra_pg_worstcase as WC

LOG = """[INFO PSM-0040] All shapes on net {n} are connected.
########## IR report #################
Net              : {n}
Corner           : default
Total power      : 2.46e+00 W
Supply voltage   : 7.00e-01 V
Worstcase voltage: 6.31e-01 V
Average voltage  : 6.72e-01 V
Average IR drop  : 2.82e-02 V
Worstcase IR drop: {d}e-02 V
Percentage drop  : 9.91 %
######################################
"""


def _run(tmp, name, nets):
    d = Path(tmp) / name; (d / "psm").mkdir(parents=True)
    (d / "psm/psm.log").write_text("".join(LOG.format(n=n, d=v) for n, v in nets) + "OT_DONE\n")
    return d


def test_worst_case_inputs_explicit():
    c, u = WC.WORST_CASE["core"], WC.WORST_CASE["ucie"]
    assert c["w_mm2"] > c["sustained_w_mm2"] > 0 and c["peak_activity"] and c["margin"] and c["per_type"]
    assert abs(u["w"] - I.UCIE_X64_W) < 1e-9 and u["margin"]


def test_verdict_fail_and_pass(tmp_path=None):
    tmp = tempfile.mkdtemp()
    core = _run(tmp, "core", [("VDD", "3.35")])
    bad = _run(tmp, "bad", [("VDD", "3.09"), ("VDDPHY", "6.94")])
    good = _run(tmp, "good", [("VDD", "3.09"), ("VDDPHY", "3.40")])
    for ucie, want in ((bad, "FAIL"), (good, "PASS")):
        out = Path(tmp) / f"pg_{want}.json"
        class A: pass
        a = A(); a.core, a.ucie, a.out, a.pg = str(core), str(ucie), str(out), str(WC.PG)
        WC.verdict(a)
        d = json.loads(out.read_text())
        assert d["ir_verdict"] == want
        assert set(d["psm"]) == {"core_centre", "io_ucie_kv_u_ucie_kv:VDD", "io_ucie_kv_u_ucie_kv:VDDPHY"}
        assert all("verdict" in v for v in d["psm"].values())   # die_infra.pg_ir_state() fallback form
        assert d["worst_case_power"]["core"]["w_mm2"] == d["core_w_mm2"]


if __name__ == "__main__":
    test_worst_case_inputs_explicit(); test_verdict_fail_and_pass(); print("PASS")
