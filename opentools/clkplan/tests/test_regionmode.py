"""region-mode predictor + shared-OCV parity tests (light)."""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from common import plan as PL  # noqa: E402
from clkplan import model as MD, ocv, regionmode as RM  # noqa: E402

M = MD.load()
EX = ROOT / "examples" / "regions_toy.json"


def run(P):
    return RM.analyse(P, M, PL.clock_sinks(P))


def test_forwarded_hop_fails_on_nominal_d():
    """neighbour-forwarded 3-mm hop: nominal |d| ~ one hop (~640 ps TT) > P/2 -> FAIL (QC-SLICECLK-2 finding)."""
    res = run(PL.load(EX))
    assert res["verdict"] == "FAIL"
    x = {r["name"]: r for r in res["crossings"]["rows"]}
    assert 600 < abs(x["x01"]["TT"]["d_ps"]) < 700 and x["x01"]["TT"]["margin_ps"] < 0
    assert x["x11"]["pass"] and x["x11"]["same_region"]


def test_balanced_spine_feed_passes():
    """same regions fed from a shared spine with equal taps: d = 0, unshared = feed + local -> PASS."""
    P = PL.load(EX)
    P["feeds"] = [dict(name=f"s{i}", src="root", dst=f"r{i}", len_um=1500.0, kind="spine") for i in range(3)]
    res = run(P)
    assert res["verdict"] == "PASS", res["crossings"]["summary"]
    r = res["crossings"]["rows"][0]
    assert abs(r["TT"]["d_ps"]) < 30 and r["TT"]["margin_ps"] > 100      # d = local-tree length difference only


def test_feed_graph_rejects_two_parents():
    P = json.loads(EX.read_text())
    P["feeds"].append(dict(name="dup", src="root", dst="r0", len_um=10))
    assert any("more than one incoming feed" in e for e in PL.validate(PL.fill_defaults(P)))


def _pess_qc(L1_mm, L2_mm, d_mm, corner):
    """QC-SLICECLK-2 predict.py branch form: 199.4 ps/mm TT, 405-um A stages, no B part, droop not shared."""
    T = M.T
    ps_mm = 199.4 if corner == "TT" else 199.4 * T["classes"]["A"]["FF"]["mu_stage_ps"] / T["classes"]["A"]["TT"]["mu_stage_ps"]

    def br(L):
        u = L * ps_mm
        fc = T["classes"]["A"][corner]["cell_share"]
        return dict(cell_ps=fc * u, net_ps=(1 - fc) * u, stages={"A": max(1, round(L / 0.405))})
    a, b = br(L1_mm), br(L2_mm)
    return max(ocv.branch_pessimism(T, corner, a, b, d_mm * 1000, False), ocv.branch_pessimism(T, corner, b, a, d_mm * 1000, False))


def test_parity_with_qc_sliceclk2_prediction():
    """reproduces claude/qc-sliceclk2-1027@d2a6b2d12b predict_out.txt: K=1 slice<->slice damage 235 TT / 194 FF,
    K=3 forwarded 133 TT / 109 FF (same math as main tools/die_plan/clk_aocv.branch_pessimism)."""
    W = 2.471
    d = math.hypot(2 * W, 1.0)
    assert round(_pess_qc(14.37, 14.37, d, "TT")) == 235
    assert round(_pess_qc(14.37, 14.37, d, "FF")) == 194
    h = 26.266 / 3
    L = h / 2 + W / 2
    d3 = math.hypot(2 * W, h / 2)
    assert round(_pess_qc(L + W, L, d3, "TT")) == 133 and round(_pess_qc(L + W, L, d3, "FF")) == 109


def test_parity_with_main_clk_aocv():
    """opentools ocv == main tools/die_plan/clk_aocv.py on the same branches (skipped outside the repo)."""
    p = REPO / "tools" / "die_plan" / "clk_aocv.py"
    if not p.exists():
        return
    sys.path.insert(0, str(p.parent))
    import clk_aocv as CA
    T = M.T
    for c in ("TT", "FF"):
        a = ocv.branch(T, c, 1800.0, 18, 250.0)
        b = ocv.branch(T, c, 900.0, 9, 202.5)
        for same in (True, False):
            ours = ocv.branch_pessimism(T, c, a, b, 3200.0, same)
            ref = CA.branch_pessimism(T, c, a, b, 3200.0, same, "setup")
            assert abs(ours - ref) < 1e-9
