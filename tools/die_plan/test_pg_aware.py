"""PG-AWARE-1 (FABLE-WAVE-REVIEW fix 6, DRT-0255 class): PG stripes where the plan says (pdn_die_phase) and no standard
cell under an M5 x M6 PG crossing at GRT (pg_cell_keepout.tcl).
python3 -m pytest -q tools/die_plan/test_pg_aware.py"""
import copy
import json
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import schema  # noqa: E402

TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("OT_RFLOW", "OT_PG_DIE_PHASE", "OT_PG_CELL_KEEPOUT", "OT_PG_FACE_CUT", "OT_GEN_M8_GRANT"):
        monkeypatch.delenv(k, raising=False)


def stripes(pdn):
    """{layer: (width, spacing, pitch, offset)} of the partition grid {top} of a pdn text."""
    out = {}
    for m in re.finditer(r"add_pdn_stripe -grid \{top\} -layer \{(M[5-7])\} -width \{([\d.]+)\} -spacing \{([\d.]+)\} "
                         r"-pitch \{([\d.]+)\} -offset \{([\d.]+)\}", pdn):
        out[m.group(1)] = tuple(float(v) for v in m.groups()[1:])
    return out


def pair_centres(layer, core_origin, extent, pdn):
    """type-frame pair centres pdngen draws: first stripe centre = core origin + offset (pdngen measures from the core)."""
    w, s, p, off = stripes(pdn)[layer]
    c, out = core_origin + off + (w + s) / 2, []
    while c < extent:
        out.append(round(c, 4))
        c += p
    return out


def test_phase_fix_puts_every_stripe_pair_in_the_plan_band():
    core = (4.32, 4.32, 617.76, 1334.88)          # QC sle_st_b_v2 (DRT-0255 x_fw_ctl_p2_i[464])
    new = gen_phys.pdn_die_phase(gen_phys.PDN, core)
    for ln in ("M5", "M6", "M7"):
        for c in pair_centres(ln, core[1] if ln == "M6" else core[0], 600.0, new):
            assert schema.pg_blocked(ln, c), (ln, c)
    # today's kit (no fix): the M7 pairs sit half a pitch off the plan band, on the face-pin tracks
    old = pair_centres("M7", core[0], 600.0, gen_phys.PDN)
    assert old[:2] == [8.64, 17.28] and not any(schema.pg_blocked("M7", c) for c in old)
    # the measured stripe of the probe: VDD M7 181.488-181.776 (pair centre 181.44) is on a free plan track
    assert 181.44 in old and not schema.pg_blocked("M7", 181.536)


def test_phase_fix_changes_only_m7_at_the_default_margin():
    core = (4.32, 4.32, 100.0, 100.0)
    new = gen_phys.pdn_die_phase(gen_phys.PDN, core)
    a, b = stripes(gen_phys.PDN), stripes(new)
    assert a["M5"] == b["M5"] and a["M6"] == b["M6"]
    assert a["M7"][3] == 4.128 and b["M7"][3] == pytest.approx(8.448)
    diff = [(x, y) for x, y in zip(gen_phys.PDN.splitlines(), new.splitlines()) if x != y]
    assert len(diff) == 1 and "-layer {M7}" in diff[0][0]
    # zero core margin (KW-FIX-45 hard wrappers): pdngen origin = type origin, nothing changes
    assert gen_phys.pdn_die_phase(gen_phys.PDN, (0.0, 0.0, 100.0, 100.0)) == gen_phys.PDN
    # other stripes (core grids with their own width/pitch) are never touched
    other = "add_pdn_stripe -grid {c1} -layer {M7} -width {0.16} -spacing {2.0} -pitch {4.32} -offset {2.16}"
    assert gen_phys.pdn_die_phase(other, core) == other


def kit(d, monkeypatch, env=()):
    for k, v in env:
        monkeypatch.setenv(k, v)
    raw = copy.deepcopy(TINY)
    raw["die"]["name"] = "s81_head"
    kd = Path(gen_phys.write_type_kit(schema.Plan(raw), "mid", d, [], util=0.5))
    return kd, dict(re.findall(r"^export (\w+) = (.*)$", (kd / "config.mk").read_text(), re.M))


def test_kit_default_off_and_gen_env_switch(tmp_path, monkeypatch):
    kd, c = kit(tmp_path / "a", monkeypatch)
    assert c["OT_PG_CELL_KEEPOUT"] == "0" and (kd / "pg_cell_keepout.tcl").is_file()
    assert stripes((kd / "pdn.tcl").read_text())["M7"][3] == 4.128
    kd, c = kit(tmp_path / "b", monkeypatch, [("OT_PG_CELL_KEEPOUT", "1"), ("OT_PG_DIE_PHASE", "1")])
    assert c["OT_PG_CELL_KEEPOUT"] == "1"
    assert stripes((kd / "pdn.tcl").read_text())["M7"][3] == pytest.approx(8.448)


def test_keepout_hooks_are_grt_only():
    pre = (HERE / "grt_pre.tcl").read_text()
    post = (HERE / "grt_post.tcl").read_text()
    tcl = (HERE / "pg_cell_keepout.tcl").read_text()
    # before PG-TRACK-TRUTH (which stays last), gated on the kit variable; removed in POST before 5_1_grt.odb
    assert pre.index("ot_pgcko_add") < pre.index("ot_pgtt_add")
    assert '$::env(OT_PG_CELL_KEEPOUT) eq "1"' in pre and 'OT_PG_CELL_KEEPOUT) ne "1"' in tcl
    assert post.index("ot_pgcko_remove") < post.index("if {[info exists ::env(OT_TAP_GRT_MODE)]")
    assert "dbBlockage_create" in tcl and "dbBlockage_destroy" in tcl and "detailed_placement" in tcl
    import importlib.util
    spec = importlib.util.spec_from_file_location("kit_resume", HERE.parent / "autopilot" / "kit_resume.py")
    kr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kr)
    assert kr.VAR_STAGE["OT_PG_CELL_KEEPOUT"] == "grt"


# ---- PG-AWARE-1 pin rule (FABLE-HARD-QCHEAD section 2, the 630-kit scan rule) and macro-face PG cut (section 3)
import landing_contract as LC  # noqa: E402
import pg_access as PA  # noqa: E402
from types import SimpleNamespace  # noqa: E402

_LAYERS = {"M7": {"dir": "V", "pitch_um": 0.064, "offset_um": 0.032}, "M6": {"dir": "H", "pitch_um": 0.064, "offset_um": 0.032}}


def _lc_plan(pins, hard=False):
    t = {"outline_um": [319.68, 349.92], "clock": {"landing_contract": {"pins": pins}, "edge_clocks": []}}
    if hard:
        t["hard"] = True
    return SimpleNamespace(types={"t": t}, layers=_LAYERS, layer_budget={"partition_signal_max": "M7"})


def _lc_pin(name, x, y):
    return dict(name=name, dir="in", kind="ctl", layer="M7", xy_um=[x, y], epoch=False)


@pytest.mark.parametrize("x,y,ok", [(158.176, 174.9516, False),   # QC su_l0 cland_tstart_in (Rect Only DRC 3)
                                    (158.176, 167.392, True),     # QC S3R2 sites
                                    (158.176, 228.949, True),
                                    (100.032, 896.424, False),    # HEAD hd_spn_end rst_start_raw_5 after the 8.64 move
                                    (100.032, 887.784, False),    # ... and before it
                                    (100.032, 889.944, True),     # the 2.16 move
                                    (170.528, 554.880, False),    # HEAD hd_host_e rst_start_raw_0
                                    (289.952, 19.200, False)])    # HEAD hd_host_e rst_start_raw_2
def test_fable_scan_rule_flags_exactly_the_measured_pins(x, y, ok):
    assert PA.pin_ok("M7", x, y, 0.432) is ok


def test_landing_pin_over_m6_pair_moves_half_a_pair_pitch_in_y():
    P = _lc_plan([_lc_pin("cland_tstart_in", 158.176, 174.9516), _lc_pin("ok", 158.176, 167.392)])
    assert LC.pg_bad_pins(P, P.types["t"]) == ["cland_tstart_in"]
    t = LC.separate_pins(P, "t")
    xy = {p["name"]: p["xy_um"] for p in t["clock"]["landing_contract"]["pins"]}
    assert xy["ok"] == [158.176, 167.392]
    nx, ny = xy["cland_tstart_in"]
    assert nx == 158.176 and abs(ny - 174.9516) < 4.32 and abs(abs(ny - 174.9516) % 4.32) > 1.0
    assert LC.pg_pin_ok(P, t, "M7", (nx, ny)) and not LC.pg_bad_pins(P, t)


def test_pin_rule_keeps_hard_types_and_face_pins():
    assert LC.pg_bad_pins(_lc_plan([_lc_pin("a", 158.176, 174.9516)], hard=True), _lc_plan([], hard=True).types["t"]) == []
    P = _lc_plan([_lc_pin("face", 158.176, 0.216)])          # in the core margin: no partition M5/M6 stripe there
    assert LC.pg_bad_pins(P, P.types["t"]) == [] and LC.separate_pins(P, "t") is None


_LEF = """MACRO epc
  SIZE 40.0 BY 30.0 ;
  PIN ft[60]
    DIRECTION INPUT ; USE SIGNAL ;
    PORT
      LAYER M6 ;
        RECT 0.000 12.544 0.300 12.576 ;
    END
  END ft[60]
  PIN ft[61]
    DIRECTION INPUT ; USE SIGNAL ;
    PORT
      LAYER M6 ;
        RECT 0.000 12.904 0.300 12.936 ;
    END
  END ft[61]
  PIN o_n
    DIRECTION OUTPUT ; USE SIGNAL ;
    PORT
      LAYER M7 ;
        RECT 10.000 29.700 10.064 30.000 ;
    END
  END o_n
  PIN mid
    DIRECTION INPUT ; USE SIGNAL ;
    PORT
      LAYER M5 ;
        RECT 20.000 15.000 20.024 15.300 ;
    END
  END mid
  PIN VDD
    DIRECTION INOUT ; USE POWER ;
    PORT
      LAYER M6 ;
        RECT 0.000 1.000 0.300 1.288 ;
    END
  END VDD
END epc
"""


def test_face_cut_windows_stop_parent_stripes_before_pin_faces(tmp_path, monkeypatch):
    lef = tmp_path / "epc.lef"
    lef.write_text(_LEF)
    pins, size = gen_phys.lef_face_pins(lef)
    assert size == (40.0, 30.0) and sorted(ln for ln, _ in pins) == ["M6", "M6", "M7"]   # no PG, no interior pin
    P = SimpleNamespace(types={"hd": {}})
    monkeypatch.setattr(gen_phys, "type_macros", lambda P, tn: [("u_epc", "epc", str(lef), None, 423.36, 313.344, "R0")])
    import cores
    monkeypatch.setattr(cores, "resolve", lambda p, root=None: p)
    assert gen_phys.pg_face_cuts(P, "hd") == []                                       # opt-in
    monkeypatch.setenv("OT_PG_FACE_CUT", "1")
    cuts = gen_phys.pg_face_cuts(P, "hd")
    assert cuts == [("u_epc", "M6", "W", (421.86, 325.816, 423.36, 326.352)),
                    ("u_epc", "M7", "N", (433.288, 343.344, 433.496, 344.844))]
    tcl = gen_phys.pg_face_cut_tcl(cuts)
    assert "pgf_window M6 421.8600 325.8160 423.3600 326.3520" in tcl and "OT_PG_FACE_CUT windows=2" in tcl
    assert tcl.count("{") == tcl.count("}")


def test_pin_rule_skips_signed_types_and_plan_can_force(monkeypatch):
    monkeypatch.setattr(LC, "_SIGNED", ["hd_host_n", "slw_su_l0__cl76fb247e"])
    for tn in ("hd_host_n", "slw_su_l0"):
        t = {"outline_um": [319.68, 349.92], "clock": {"landing_contract": {"pins": [_lc_pin("p", 158.176, 174.9516)]}}}
        P = SimpleNamespace(types={tn: t}, layers=_LAYERS, layer_budget={"partition_signal_max": "M7"})
        assert LC.pg_bad_pins(P, t) == []                        # signed (or a signed variant of it): site kept
        t["pg_pin_rule"] = True
        assert LC.pg_bad_pins(P, t) == ["p"]
    t = {"outline_um": [319.68, 349.92], "clock": {"landing_contract": {"pins": [_lc_pin("p", 158.176, 174.9516)]}}}
    P = SimpleNamespace(types={"hd_host_e": t}, layers=_LAYERS, layer_budget={"partition_signal_max": "M7"})
    assert LC.pg_bad_pins(P, t) == ["p"]                         # unsigned


def test_off_phase_m7_stripe_is_not_a_pin_move():
    # hd_st_turn rst_start_raw_5 (578.88, 535.68): on today's off-phase kit M7 stripe, legal on the plan phase
    P = _lc_plan([_lc_pin("rst_start_raw_5", 578.88, 535.68)])
    P.types["t"]["outline_um"] = [1000.0, 1000.0]
    assert LC.pg_bad_pins(P, P.types["t"]) == []


def test_schema_accepts_pg_pin_rule_key():
    """the plan key landing_contract.pg_rule_applies reads must be a legal type key (gen phys refused it: unknown key)"""
    import schema as S
    props = S.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]
    assert props["pg_pin_rule"] == {"type": "boolean"}
