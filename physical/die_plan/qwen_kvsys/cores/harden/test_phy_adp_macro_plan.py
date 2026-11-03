"""DIE-KV-60/adp 11-01: qkd_hr_phy_adp macro-fit plan (native SRAM 174.12 x 29.736, R270 on the core E edge)."""
import json
import re
from pathlib import Path

H = Path(__file__).resolve().parent
QV = H.parents[1]


def test_phy_adp_macro_plan_fits_core_and_plan_slot():
    p = json.load(open(H / "qkd_hr_phy_adp_macro_plan.json"))
    w, h = p["outline_um"]
    assert p["module"] == "qkd_hr_phy_adp" and p["added_cycles"] == 0 and p["pg_pin_layer"] == "M4"
    (b,) = p["blocks"]
    assert b["inst"] == "u_slice.u_body.g_grp[0].u_rb.g_sram.g_t[0].u_m" and b["orient"] == "R270"
    lef = (QV.parents[2] / p["children"][b["master"]] / f"{b['master']}.lef").read_text()
    size = re.search(r"\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)", lef)
    assert (float(size[1]), float(size[2])) == (174.12, 29.736)
    mw, mh = 29.736, 174.12                                   # rotated footprint
    halo = p["halo_um"]
    assert halo <= b["x"] - 4.32 and b["x"] + mw + halo <= w + 1e-6      # E edge, inside the die area with halo
    assert 4.32 + halo <= b["y"] and b["y"] + mh + halo <= h - 4.32      # N / S logic gutters for the pin ends
    assert abs((b["x"] - 0.012) / 0.048 - round((b["x"] - 0.012) / 0.048)) < 1e-6   # M5 pin phase
    import importlib.util
    spec = importlib.util.spec_from_file_location("mpt_adp", H / "macro_pin_tracks.py")
    T = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(T)
    assert T.check(p["blocks"], lambda m: lef)                # DIE-KV-62/hr: every SRAM pin on a preferred track
    rec = json.load(open(H / "recipes_kv.json"))["qkd_hr_phy_adp"]
    assert rec["hard_children"].endswith("qkd_hr_phy_adp_macro_plan.json")
    plan = json.load(open(QV / "plan_of_record/plan_c.json"))
    cores = [c for c in plan["partition_types"]["kv3_hub_Wi"]["hard_cores"] if c["module"] == "qkd_hr_phy_adp"]
    assert len(cores) == 8 and all(c["outline_um"] == [w, h] for c in cores)


def _gk():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gk_adp", H / "gen_core_kit_kv.py")
    G = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(G)
    return G


def test_gen_core_kit_rotated_m4_macro_pdn_form():
    G = _gk()
    assert "add_pdn_connect -grid {macro} -layers {M4 M6}" in G.PDN_MACRO_M4_ROT
    assert "-layer {M6}" in G.PDN_MACRO_M4_ROT and "R270" in G.ROT90 and "R0" not in G.ROT90


def test_ifp_standin_for_rotated_only_fit_children():
    # IFP-0002 checks the unrotated master; the R90 stand-in (same pins, swapped size) is used for that call only
    G = _gk()
    lef = ("MACRO m\n  FOREIGN m 0 0 ;\n  SIZE 174.120 BY 29.736 ;\n  CLASS BLOCK ;\n  PIN clk\n    PORT\n"
           "      LAYER M4 ;\n      RECT 0.000 0.768 0.024 0.792 ;\n    END\n  END clk\nEND m\nEND LIBRARY\n")
    out = G.ifp_standin_lef(lef, "m", "m__ifp_r90")
    assert "MACRO m__ifp_r90" in out and "END m__ifp_r90" in out and "FOREIGN m__ifp_r90 0 0" in out
    assert "SIZE 29.736 BY 174.120" in out and "RECT 28.9440 0.0000 28.9680 0.0240 ;" in out and "PIN clk" in out
    size = {"m": (174.12, 29.736)}.get
    blk = [dict(inst="u", master="m", orient="R270")]
    assert G.ifp_standin_children(blk, size, (43.2, 198.72)) == ["m"]
    assert G.ifp_standin_children([dict(blk[0], orient="R0")], size, (190.0, 198.72)) == []
    assert G.ifp_standin_children(blk, size, (190.0, 198.72)) == []        # fits unrotated: no stand-in
    assert "rename initialize_floorplan ot_ifp_orig_initialize_floorplan" in G.IFP_STANDIN_TCL
    assert "read_liberty -corner $c $sl" in G.IFP_STANDIN_TCL     # swapMaster under STA needs the stand-in liberty
    assert "rename ::rtl_macro_placer ::ot_ifp_rtl_macro_placer" in G.IFP_STANDIN_MPL_TCL   # MPL-0006: fixed-site check


def test_macro_pin_tracks_rotated_phase():
    # DIE-KV-62/hr 11-02: R270 swaps the pin phase axis; y 17.28 put the M4 pins 0.012 um off the M4 tracks
    import importlib.util
    import pytest
    spec = importlib.util.spec_from_file_location("mpt_t", H / "macro_pin_tracks.py")
    T = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(T)
    lef = ("MACRO m\n  SIZE 174.120 BY 29.736 ;\n  CLASS BLOCK ;\n  PIN clk\n    USE CLOCK ;\n    PORT\n"
           "      LAYER M4 ;\n      RECT 0.000 0.768 0.024 0.792 ;\n    END\n  END clk\n  PIN VDD\n    USE POWER ;\n"
           "    PORT\n      LAYER M4 ;\n      RECT 1.000 1.000 1.111 1.111 ;\n    END\n  END VDD\nEND m\n")
    w, h, pins = T.lef_master(lef, "m")
    assert (w, h) == (174.12, 29.736) and list(pins) == ["clk"]
    assert T.place(0.012, 0.78, w, h, "R270", 17.772, 17.28) == pytest.approx((18.552, 191.388))
    assert T.place(0.012, 0.78, w, h, "R0", 1.0, 2.0) == pytest.approx((1.012, 2.78))
    bad = dict(inst="u", master="m", orient="R270", x=17.772, y=17.28)
    with pytest.raises(SystemExit, match=r"shift the site by \(\+0.000, \+0.012\)"):
        T.check([bad], lambda m: lef)
    assert T.check([dict(bad, y=17.292)], lambda m: lef)
    assert T.check([dict(bad, orient="R0", x=0.0, y=0.012)], lambda m: lef)     # R0: M4 y phase only
