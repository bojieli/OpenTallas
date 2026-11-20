"""S81-HI-CORRIDOR: shared hi-quad bank sites (check / sites / seed) on a synthetic leaf type."""
import copy
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s81_hi_corridor as H  # noqa: E402

L = 114.48


def plan():
    cores = [dict(inst="u_lf.u_vn.u_a", module="ot_s81sl_vn_a", origin_um=[500.0, 300.0], orient="R0", outline_um=[356.4, 164.16])]
    for k in range(16):
        col, row = k % 2, k // 2
        cores.append(dict(inst=f"u_lf.u_vp.g_ln[{k}].u_l", module="ot_dsrom_su_hcpost_lane_pr",
                          origin_um=[200.0 + col * (L + 11.0), 20.0 + row * (L + 15.0)], orient="MX", outline_um=[L, L]))
    st = []
    for k in range(16):
        x0, y0 = cores[1 + k]["origin_um"]
        # stage 0 at the vn face, stage 1 alternately west gap / vn face (centroid lands inside a lane), stage 2 at the lane
        s1 = [x0 + L + 5.5, y0 + 40] if k % 2 == 0 else [490.0, y0 + 40]
        st.append(dict(bits=523, launch="core:u_lf.u_vn.u_a.hw_d", capture=f"u_lf.u_vp.g_ln[{k}].u_l",
                       conn="x", from_um=[500.0, 380.0], regs_um=[[490.0, 380.0], s1, [x0 + L + 2, y0 + 60]],
                       to_um=[x0 + L, y0 + 60], note=""))
    t = dict(outline_um=[1000.0, 1200.0], hard_cores=cores, internal_stations=st)
    return {"partition_types": {"ot_s81sl_leaf__t99": t}}


def test_check_flags_bank_inside_lane():
    r = H.check(plan(), r"t99", 2)["ot_s81sl_leaf__t99"]
    assert r["banks_inside_core"] >= 1 and r["verdict"] == "OVER"


def test_sites_moves_every_shared_bank_out_of_cores_and_keeps_counts():
    P = plan()
    before = copy.deepcopy(P)
    rows = H.sites(P, r"t99", 2, 4.32)
    assert rows and all(r["result"] == "sited" for r in rows)
    t, t0 = P["partition_types"]["ot_s81sl_leaf__t99"], before["partition_types"]["ot_s81sl_leaf__t99"]
    assert [len(e["regs_um"]) for e in t["internal_stations"]] == [len(e["regs_um"]) for e in t0["internal_stations"]]
    assert [e["regs_um"][2] for e in t["internal_stations"]] == [e["regs_um"][2] for e in t0["internal_stations"]]
    r = H.check(P, r"t99", 2)["ot_s81sl_leaf__t99"]
    assert r["banks_inside_core"] == 0
    for g in range(4):     # one site per quad stage
        es = [e for e in t["internal_stations"] if int(e["capture"].split("[")[1].split("]")[0]) // 4 == g]
        for j in range(2):
            assert len({tuple(e["regs_um"][j]) for e in es}) == 1


def test_seed_B_puts_quads_in_columns():
    sd, rep = H.seed(plan(), r"t99", "B", 30.24)
    assert rep["ot_s81sl_leaf__t99"]["quads_in_one_column"] == 4
    pos = sd["ot_s81sl_leaf__t99"]
    assert sorted(tuple(v["origin_um"]) for v in pos.values()) == sorted(
        tuple(c["origin_um"]) for c in plan()["partition_types"]["ot_s81sl_leaf__t99"]["hard_cores"][1:])


def test_cli_check(tmp_path):
    p = tmp_path / "p.json"; p.write_text(json.dumps(plan()))
    out = subprocess.run([sys.executable, "-I", str(HERE / "s81_hi_corridor.py"), "check", str(p), "--types", "t99"],
                         capture_output=True, text=True, check=True).stdout
    assert "HI_CORRIDOR_CHECK" in out and "OVER" in out
