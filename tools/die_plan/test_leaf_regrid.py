"""S81-LEAF-REGRID: lane slots (columns beside the vn face, landing-band keep-outs), apply and check on a synthetic leaf."""
import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import leaf_regrid as R  # noqa: E402
import s81_hi_corridor as H  # noqa: E402

L = R.LW
TN = "ot_s81sl_leaf__t97"


def plan(band=None):
    cores = [dict(inst="u_lf.u_vn.u_a", module="ot_s81sl_vn_a", origin_um=[600.0, 500.0], orient="R0", outline_um=[356.4, 164.16])]
    st = []
    for k in range(16):                              # 4 x 4 block, 6 um gaps: the measured bad form
        x0, y0 = 100.0 + (k % 4) * (L + 6.0), 340.0 + (k // 4) * (L + 6.0)
        cores.append(dict(inst=f"u_lf.u_vp.g_ln[{k}].u_l", module="ot_dsrom_su_hcpost_lane_pr", origin_um=[x0, y0], orient="R0", outline_um=[L, L]))
        st.append(dict(bits=256, launch="core:u_lf.u_vn.u_a.hw_d", capture=f"u_lf.u_vp.g_ln[{k}].u_l",
                       conn=f"core:u_lf.u_vn.u_a.hw_d|core:u_lf.u_vp.g_ln[{k}].u_l", from_um=[600.0, 520.0 + 6 * k],
                       regs_um=[[590.0, 520.0 + 6 * k], [x0 + L + 3.0, y0 + 60.0]], to_um=[x0 + L, y0 + 60.0], note=""))
    t = dict(outline_um=[1000.0, 1300.0], hard_cores=cores, internal_stations=st)
    if band:
        t["clock"] = dict(band_fixed_um=dict(ft3_i=dict(rect_um=list(band))))
    return {"partition_types": {TN: t}}


def _hit(slot, band, gap):
    x, y = slot
    a, b, c, d = band
    return x < c + gap and a < x + L + gap and y < d + gap and b < y + L + gap


def test_slots_are_columns_beside_the_vn_face_with_the_gaps():
    S, err = R.find_slots(plan()["partition_types"][TN])
    assert err is None and S["side"] == -1 and len(S["slots"]) >= 16 and S["strip"] >= R.STRIP - 1e-6
    cols = sorted(S["cols"])
    assert all(b - a >= L + R.COL_GAP - 1e-6 for a, b in zip(cols, cols[1:]))
    for x in cols:
        ys = sorted(y for sx, y in S["slots"] if sx == x)
        assert all(b - a >= L + R.ROW_GAP - 1e-6 for a, b in zip(ys, ys[1:]))


def test_no_slot_on_or_beside_a_landing_band():
    """t44 kit A 11-21: two moved lanes stood on the ft3_i / up_s landing bands and global_place stopped (OT_CLAND BAND FAIL)"""
    S0, _ = R.find_slots(plan()["partition_types"][TN])
    x, y = S0["slots"][len(S0["slots"]) // 2]
    band = (x + 10.0, y + 20.0, x + 100.0, y + 60.0)                     # a band under one free-form slot
    assert any(_hit(s, band, 0.0) for s in S0["slots"])
    S1, _ = R.find_slots(plan(band)["partition_types"][TN])
    assert S1["slots"] and not any(_hit(s, band, R.BAND_GAP - 1e-6) for s in S1["slots"])


def test_apply_moves_the_lanes_off_the_band_and_check_gates_it():
    S0, _ = R.find_slots(plan()["partition_types"][TN])
    x, y = sorted(S0["slots"], key=lambda s: abs(s[0] + L / 2 - S0["face_x"]) + abs(s[1] + L / 2 - 560.0))[0]
    band = (x + 10.0, y + 20.0, x + 100.0, y + 60.0)                     # under the slot the free form would use first
    P = plan(band)
    t = P["partition_types"][TN]
    r = R.regrid_type(TN, t, P, R.COL_GAP, R.ROW_GAP, R.STRIP)
    assert r["result"] == "moved", r
    lanes = [b for b in H.boxes(t) if H.LN.search(b[0])]
    assert len(lanes) == 16 and not any(b[1] < band[2] + R.BAND_GAP - 1e-6 and band[0] - R.BAND_GAP + 1e-6 < b[3]
                                        and b[2] < band[3] + R.BAND_GAP - 1e-6 and band[1] - R.BAND_GAP + 1e-6 < b[4] for b in lanes)
    R.seat(t)                                                             # as apply does: registers 8.64 um off every core
    c = R.check_type(TN, t, 0)
    assert c["lanes_on_band"] == [] and c["lane_gaps_under"] == 0 and c["sites_in_core"] == 0
    bad = copy.deepcopy(t)                                                # a band drawn over a placed lane fails the check
    b0 = lanes[0]
    bad["clock"]["band_fixed_um"]["ft3_i"]["rect_um"] = [b0[1] + 5.0, b0[2] + 5.0, b0[3] - 5.0, b0[2] + 40.0]
    cb = R.check_type(TN, bad, 0)
    assert cb["lanes_on_band"] == [b0[0]] and not cb["pass"]


def test_refused_type_keeps_its_rows_through_the_cli(tmp_path):
    import json, subprocess
    P = plan()
    t = P["partition_types"][TN]
    t["outline_um"] = [1000.0, 480.0]                                     # 3 rows a column: 12 slots for 16 lanes
    src = tmp_path / "p.json"; out = tmp_path / "o.json"
    src.write_text(json.dumps(P))
    r = subprocess.run([sys.executable, "-I", str(HERE / "leaf_regrid.py"), "apply", str(src), "--types", "t97", "--out", str(out),
                        "--report", str(tmp_path / "r.json")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    rep = json.loads((tmp_path / "r.json").read_text())
    assert rep and rep[0]["result"].startswith("REFUSED")
    assert json.loads(out.read_text())["partition_types"][TN] == json.loads(src.read_text())["partition_types"][TN]
