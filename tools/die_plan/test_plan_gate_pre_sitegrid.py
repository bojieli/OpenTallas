"""SITEGRID-1123 (ADV-SITEGRID-1123): exact bank sites on the kit site/row lattice, integer DBU (site_grid.py)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_gate_pre as G  # noqa: E402
import site_grid as SG  # noqa: E402

T = dict(dbu=1000, site_w=54, row_h=270, mfg=1, src="test")
X0 = Y0 = 4.32


def on(c, r):
    """the c-th site column / r-th row origin, as a row generator writes it (float, 6 decimals)"""
    return [round(X0 + c * 0.054, 6), round(Y0 + r * 0.27, 6)]


def plan(types):
    return {"die": "kv", "partition_types": types}


def hg_type(bits):
    """HGFORM-like kv3_hg: one o_ectl_Q_N_tN bus, 2 stages of exact bank sites"""
    return {"outline_um": [1278.72, 1520.64],
            "internal_stations": [{"conn": "bus:o_ectl_Q_N_tN", "regs_um": [[965, 1240], [965, 1250]],
                                   "bit_sites_um": bits, "bit_site_cell_um": [0.378, 0.27]}]}


def fails(lines):
    return [x for x in lines if x.startswith("FAIL ")]


def test_hgform_off_grid_bank_seats_fail_with_nearest_origin():
    bits = [[[965, round(1240 + 0.27 * b, 6)] for b in range(3)], [[965, round(1250 + 0.27 * b, 6)] for b in range(3)]]
    out = SG.findings(plan({"kv3_hg": hg_type(bits)}), T=T)
    f = fails(out)
    assert len(f) == 1 and f[0].startswith("FAIL SITEGRID kv3_hg: 6 exact bank site(s)")
    assert "internal_stations[0] bus:o_ectl_Q_N_tN" in f[0]
    assert "stage 0 bit 0 (965, 1240) -> nearest (964.98, 1240.11)" in f[0]
    assert "not on row/site" in f[0]
    assert out[-1].startswith("WARN SITEGRID-SUMMARY 6 exact bank site(s) off grid in 1 type(s)")


def test_on_grid_banks_pass_where_float_modulo_would_not():
    bits = [[on(17790, 4575 + b) for b in range(4)], [on(17800, 4575 + b) for b in range(4)]]
    x = bits[0][0][0]
    assert x == 964.98 and (x - X0) % 0.054 != 0         # naive float modulo calls this off grid
    face = [on(100, 10), on(101, 10)]
    t = hg_type(bits)
    t["internal_stations"][0]["face_bit_sites_um"] = face
    t["clock"] = {"soft_reg_banks": [{"id": "cs0", "cell_glob": "*", "source": "s", "bit_site_cell_um": [0.378, 0.27],
                                       "bit_sites_um": [on(200, 30), on(210, 30)]}]}
    assert SG.findings(plan({"kv3_hg": t}), T=T) == []


def test_soft_cs_and_face_banks_off_grid_fail():
    t = hg_type([[on(1, 1)]])
    t["internal_stations"][0]["face_bit_sites_um"] = [[10.0, on(0, 3)[1]]]        # x off
    t["clock"] = {"soft_reg_banks": [{"id": "cs0", "bit_sites_um": [[on(5, 5)[0], 9.0]]}]}   # y off
    f = fails(SG.findings(plan({"ty": t}), T=T))
    assert len(f) == 1 and "ty: 2 exact bank site(s)" in f[0]
    assert "face bit 0 (10, 5.13) -> nearest (9.99, 5.13)" in f[0]
    assert "clock.soft_reg_banks[0] cs0" in f[0]


def test_shift_vector_core_margins_and_offarea():
    bits = [[[on(c, 7)[0] + 0.027, on(c, 7)[1]] for c in range(3)]]            # half a site east on every bit
    t = hg_type(bits)
    f = fails(SG.findings(plan({"ty": t}), T=T))
    assert "one residual (dx, dy) = (27, 0) DBU on all" in f[0]
    t2 = hg_type([[[0.054 * 3, 0.27 * 2]]])                                       # on grid only with a zero W/S margin
    assert fails(SG.findings(plan({"ty": t2}), T=T)) == []                       # outside the default core: OFFAREA's
    t2["kit_core_margins_um"] = [0, 0, 4.32, 4.32]
    assert fails(SG.findings(plan({"ty": t2}), T=T)) == []
    t2["internal_stations"][0]["bit_sites_um"] = [[[0.054 * 3 + 0.01, 0.27 * 2]]]
    assert "grid x0 0 + k x 0.054, y0 0 + k x 0.27" in fails(SG.findings(plan({"ty": t2}), T=T))[0]


def test_macros_warn_only():
    t = {"outline_um": [400, 400],
         "hard_cores": [{"inst": "u_a", "lef": "a.lef", "origin_um": [100.01, 50.0], "outline_um": [10, 10]},     # off site
                        {"inst": "u_b", "lef": "b.lef", "origin_um": on(30, 30), "outline_um": [10, 10],
                         "track_offset_um": [0.0005, 0]}],                                                   # off mfg
         "contents": [{"inst": "u_c", "module": "m", "lef": "c.lef", "origin_um": on(500, 500)}]}
    out = SG.findings(plan({"ty": t}), T=T)
    assert fails(out) == []
    w = [x for x in out if x.startswith("WARN SITEGRID-MACRO")]
    assert len(w) == 1 and "ty: 1 macro origin(s) off the 0.001 um manufacturing grid" in w[0] and "hard_cores u_b" in w[0]
    assert "2 macro origin(s) off the site column / row in 1 type(s)" in out[-1]


def test_plan_gate_pre_class_and_skip(tmp_path):
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(plan({"kv3_hg": hg_type([[[965, 1240]]])})))
    others = [c for c in G.CLASSES if c != "SITEGRID"] + ["TAPOFF"]
    assert "SITEGRID" in G.CLASSES
    f = G.check(str(tmp_path), str(p), skip=others)
    assert [x.split()[1] for x in f if x.startswith("FAIL ")] == ["SITEGRID"]
    assert fails(G.check(str(tmp_path), str(p), skip=others + ["SITEGRID"])) == []
    argv = ["check", "--tree", str(tmp_path), "--plan", str(p)] + [a for c in G.CLASSES if c != "SITEGRID" for a in ("--skip", c)]
    assert G.main(argv) == 1


def test_dbu_rounding_mirrors_the_kit():
    assert SG.to_dbu(964.98, 1000) == 964980 and SG.to_dbu(0.0005, 1000) == 1 and SG.to_dbu(1240.1100000000001, 1000) == 1240110
    assert SG.tech()["site_w"] in (54, 216) and SG.tech()["row_h"] in (270, 1080)


def test_kit_print_format_is_judged():
    """the kit judges the generator's text: kit_istations %0.9g reads 1111.3740001 as the on-grid 1111.374; soft CS sites
    print %.9g (was %g: 1111.374 -> 1111.37 off grid); a hard core origin + track_offset with float noise
    (406.08000000000004 + 0.108) reaches place_macro as 406.1880 (on the manufacturing grid)."""
    import soft_cs_placement as SCP
    x = on(20501, 10)
    assert x[0] == 1111.374
    assert "{1111.374 7.02}" in SCP.emit([{"id": "cs", "cell_glob": "u*", "bit_sites_um": [x], "bit_site_cell_um": [0.378, 0.27]}])[1]
    t = {"outline_um": [1200, 400], "clock": {"soft_reg_banks": [{"id": "cs", "bit_sites_um": [x]}]},
         "internal_stations": [{"conn": "bus:b", "bit_sites_um": [[[1111.3740001, x[1]]]]}],
         "hard_cores": [{"inst": "u_l", "lef": "l.lef", "origin_um": [406.08000000000004, 509.76], "track_offset_um": [0.108, 0.036],
                         "outline_um": [10, 10]}]}
    assert SG.findings(plan({"ty": t}), T=T)[:-1] == []
    old = SG.SOFT_CS_SPEC
    try:
        SG.SOFT_CS_SPEC = "%g"
        f = fails(SG.findings(plan({"ty": t}), T=T))
        assert len(f) == 1 and "plan (1111.374, 7.02) printed %g" in f[0] and "1 of them are ON grid in the plan" in f[0]
    finally:
        SG.SOFT_CS_SPEC = old
