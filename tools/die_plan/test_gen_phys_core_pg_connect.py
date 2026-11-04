"""PG-CORECONN-1 (opt-in partition_types.<t>.core_pg_connect): hard-core VDD/VSS pins land on the tile PG grid.
python3 -m pytest -q tools/die_plan/test_gen_phys_core_pg_connect.py"""
import copy
import filecmp
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import schema  # noqa: E402
from test_g2 import PAIR  # noqa: E402


def _lef(d, name="core", vdd="M5", vss="M5"):
    def pin(p, use, lay):
        geo = f"    PORT\n      LAYER {lay} ;\n        RECT 3.0 1.0 3.2 9.0 ;\n    END\n" if lay else ""
        return f"  PIN {p}\n    USE {use} ;\n{geo}  END {p}\n"
    p = Path(d) / f"{name}.lef"
    p.write_text(f"MACRO {name}\n  SIZE 20 BY 10 ;\n{pin('VDD', 'POWER', vdd)}{pin('VSS', 'GROUND', vss)}END {name}\n")
    return str(p)


def _P(d, **lays):
    cores = [dict(inst="u_b.g_cv[0].u_eA", module="core", lef=_lef(d, **lays), origin_um=[10.0, 20.0]),
             dict(inst="u_b.u_eB", module="core4", lef=_lef(d, "core4", "M4", "M4"), origin_um=[50.0, 20.0])]
    return SimpleNamespace(types={"hd": dict(outline_um=[100.0, 100.0], hard_cores=cores, core_pg_connect=True)})


def test_connect_layer_from_lef():
    with tempfile.TemporaryDirectory() as d:
        assert gen_phys.core_pg_connect_layer(_lef(d)) == ("M5", "M6")
        assert gen_phys.core_pg_connect_layer(_lef(d, "a", "M4", "M4")) == ("M4", "M5")
        assert gen_phys.core_pg_connect_layer(_lef(d, "b", "M6", "M6")) == ("M6", "M7")
        for bad in (dict(vss=None), dict(vdd="M7", vss="M7"), dict(vdd="M5", vss="M4")):
            with pytest.raises(ValueError):
                gen_phys.core_pg_connect_layer(_lef(d, "x", **{**dict(vdd="M5", vss="M5"), **bad}))


def test_grids_per_layer_and_opt_in():
    with tempfile.TemporaryDirectory() as d:
        P = _P(d)
        mac = gen_phys.type_macros(P, "hd")
        t = gen_phys.core_pg_grids(P, "hd", mac)
        txt = "\n".join(t)
        assert "add_pdn_connect -grid {core_pg_M5} -layers {M5 M6}" in txt
        assert "add_pdn_connect -grid {core_pg_M4} -layers {M4 M5}" in txt
        assert r"{^u_b\.g_cv\\\[0\\\]\.u_eA$}" in txt        # escaped ODB bracket name as a pdngen regex
        assert gen_phys.core_pg_unconnected(txt, mac) == []
        P.types["hd"]["core_pg_connect"] = False
        assert gen_phys.core_pg_grids(P, "hd", mac) == []


def test_mutant_unconnected_core_pg_pin_fails():
    """Mutants: a core missing from its grid, a grid without the connect, the connect on the wrong layer pair, and
    the default kit PDN (no macro grid at all) each leave a core PG pin unconnected and must be reported."""
    with tempfile.TemporaryDirectory() as d:
        P = _P(d)
        mac = gen_phys.type_macros(P, "hd")
        good = "\n".join(gen_phys.core_pg_grids(P, "hd", mac))
        drop_inst = good.replace(r"{^u_b\.u_eB$}", "{^nobody$}")
        no_conn = "\n".join(l for l in good.splitlines() if "core_pg_M5} -layers" not in l)
        wrong = good.replace("-grid {core_pg_M5} -layers {M5 M6}", "-grid {core_pg_M5} -layers {M4 M5}")
        assert [b[0] for b in gen_phys.core_pg_unconnected(drop_inst, mac)] == ["u_b.u_eB"]
        assert [b[0] for b in gen_phys.core_pg_unconnected(no_conn, mac)] == ["u_b.g_cv[0].u_eA"]
        assert [b[0] for b in gen_phys.core_pg_unconnected(wrong, mac)] == ["u_b.g_cv[0].u_eA"]
        assert len(gen_phys.core_pg_unconnected(gen_phys.PDN, mac)) == 2
        # generation refuses an opted-in type whose macro has no connectable PG pin
        P2 = _P(d, vdd="M5", vss=None)
        with pytest.raises(ValueError):
            gen_phys.core_pg_grids(P2, "hd", gen_phys.type_macros(P2, "hd"))


def test_schema_accepts_flag():
    raw = copy.deepcopy(PAIR)
    raw["partition_types"]["fa"]["core_pg_connect"] = True
    schema.Plan(raw)


def _same_tree(a, b):
    c = filecmp.dircmp(a, b)
    assert not c.left_only and not c.right_only and not c.diff_files, (c.left_only, c.right_only, c.diff_files)
    for sub in c.common_dirs:
        _same_tree(Path(a) / sub, Path(b) / sub)


def test_kit_byte_identical_off_and_grid_on(monkeypatch):
    P0 = schema.Plan(copy.deepcopy(PAIR))
    raw = copy.deepcopy(PAIR)
    raw["partition_types"]["fa"]["core_pg_connect"] = True                  # opted in, no macro: nothing to add
    P1 = schema.Plan(raw)
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        gen_phys.write_type_kit(P0, "fa", a, [])
        gen_phys.write_type_kit(P1, "fa", b, [])
        _same_tree(Path(a) / "fa", Path(b) / "fa")
        assert (Path(a) / "fa" / "pdn.tcl").read_text() == gen_phys.PDN
    # with a placed macro the kit pdn.tcl carries its macro grid after the tile grid, and is checked
    monkeypatch.setattr(gen_phys, "core_pg_grids", lambda P, tn, m, root=None, exclude=(): [
        "define_pdn_grid -macro -name {core_pg_M5} -instances {{^u$}} -voltage_domains {CORE} -halo {0}",
        "add_pdn_connect -grid {core_pg_M5} -layers {M5 M6}"])
    monkeypatch.setattr(gen_phys, "core_pg_unconnected", lambda *a, **k: [])
    with tempfile.TemporaryDirectory() as d:
        gen_phys.write_type_kit(P1, "fa", d, [])
        pdn = (Path(d) / "fa" / "pdn.tcl").read_text()
        assert pdn.startswith(gen_phys.PDN) and pdn.endswith("add_pdn_connect -grid {core_pg_M5} -layers {M5 M6}\n")
    monkeypatch.setattr(gen_phys, "core_pg_unconnected", lambda *a, **k: [("u", "M5", "M6")])
    with tempfile.TemporaryDirectory() as d, pytest.raises(ValueError, match="unconnected"):
        gen_phys.write_type_kit(P1, "fa", d, [])


def test_phy_path_uses_layer_grids_when_opted_in():
    with tempfile.TemporaryDirectory() as d:
        P = _P(d)
        phy = ("u_phy", "phy", _lef(d, "phy", "M6", "M6"), None, 0.0, 0.0, "R0")
        mac = gen_phys.type_macros(P, "hd") + [phy]
        doms = [("phy_pg", "VDDPHY", "VSS", (0.0, 0.0, 20.0, 10.0), ["u_phy"])]
        off = gen_phys.phy_pg_pdn(P, "hd", doms, mac, root=d)
        on = gen_phys.phy_pg_pdn(P, "hd", doms, mac, root=d, core_grids=True)
        assert "-grid {core_macros} -layers {M4 M5}" in off and "core_pg_" not in off      # default unchanged
        assert "core_macros" not in on and "-grid {core_pg_M5} -layers {M5 M6}" in on
        assert "u_phy" not in "\n".join(l for l in on.splitlines() if "core_pg_" in l)     # PHY macro keeps its grid
        assert gen_phys.core_pg_unconnected(on, mac, exclude={"u_phy"}) == []
        assert len(gen_phys.core_pg_unconnected(off, mac, exclude={"u_phy"})) == 1          # the M5 core: M4 M5 only


def test_phy_domain_content_without_macro_view_fails_closed():
    # S81-KITS-G 10-30: a PG domain powering content with no lef/lib (u_phy 'rework') was a raw KeyError 'u_phy'
    with tempfile.TemporaryDirectory() as d:
        P = _P(d)
        mac = gen_phys.type_macros(P, "hd")
        doms = [("phy_pg", "VDDPHY", "VSS", (0.0, 0.0, 20.0, 10.0), ["u_phy"])]
        with pytest.raises(ValueError, match=r"PG domain phy_pg \(hd\): powered content \['u_phy'\] has no macro view"):
            gen_phys.phy_pg_pdn(P, "hd", doms, mac, root=d)


def test_default_on_when_unset_and_skips_unlandable_view():
    """PG-CORECONN-2 11-03 class fix: unset core_pg_connect = ON (S81: 136/158 macro types never set it); explicit
    false keeps the legacy bytes; the implicit default skips a view without PG geometry (comment), explicit true
    still raises."""
    with tempfile.TemporaryDirectory() as d:
        P = _P(d)
        del P.types["hd"]["core_pg_connect"]
        mac = gen_phys.type_macros(P, "hd")
        assert gen_phys.core_pg_on(P, "hd")
        txt = "\n".join(gen_phys.core_pg_grids(P, "hd", mac))
        assert "add_pdn_connect -grid {core_pg_M5} -layers {M5 M6}" in txt
        P.types["hd"]["core_pg_connect"] = False
        assert not gen_phys.core_pg_on(P, "hd") and gen_phys.core_pg_grids(P, "hd", mac) == []
        Q = _P(d, vdd=None, vss=None)
        del Q.types["hd"]["core_pg_connect"]
        mq = gen_phys.type_macros(Q, "hd")
        t = gen_phys.core_pg_grids(Q, "hd", mq)
        assert any(s.startswith("# PG-CORECONN-2 (default-on): macro u_b.g_cv[0].u_eA skipped") for s in t)
        assert "add_pdn_connect -grid {core_pg_M4} -layers {M4 M5}" in "\n".join(t)
        assert gen_phys.core_pg_unconnected("\n".join(t), mq, strict=False) == []
        Q.types["hd"]["core_pg_connect"] = True
        with pytest.raises(ValueError):
            gen_phys.core_pg_grids(Q, "hd", mq)


def test_default_on_skips_buried_pg_view_explicit_keeps_it():
    """PDN-0006 guard for the implicit default: a view whose M5 PG sits under an M6 OBS is skipped (comment) unless
    the type explicitly opts in."""
    with tempfile.TemporaryDirectory() as d:
        P = _P(d)
        del P.types["hd"]["core_pg_connect"]
        lf = Path(d) / "core.lef"
        lf.write_text(lf.read_text().replace("END core\n", "  OBS\n    LAYER M6 ;\n      RECT 0 0 20 10 ;\n  END\nEND core\n"))
        assert gen_phys.macro_obs_layers(lf) == {"M6"}
        mac = gen_phys.type_macros(P, "hd")
        txt = "\n".join(gen_phys.core_pg_grids(P, "hd", mac))
        assert "buried under OBS on M6" in txt
        assert "-layers {M5 M6}" not in txt and "-layers {M4 M5}" in txt
        assert gen_phys.core_pg_unconnected(txt, mac, strict=False) == []
        P.types["hd"]["core_pg_connect"] = True          # explicit opt-in keeps the old (strict) landing
        assert "-layers {M5 M6}" in "\n".join(gen_phys.core_pg_grids(P, "hd", mac))


def _m7_lef(d, name="m7top", m6=False, obs_m7=True):
    """M7-top view like S81 rom_elem_q (M6 PG under its own M7 OBS) / bf_col (M7 PG only): VSS left of VDD."""
    def pin(p, use, x):
        g = f"      LAYER M7 ;\n        RECT {x} 0.5 {x + 0.288} 9.5 ;\n        RECT {x + 10.8} 0.5 {x + 11.088} 9.5 ;\n"
        if m6:
            g += f"      LAYER M6 ;\n        RECT 0 {x} 0.032 {x + 0.288} ;\n"
        return f"  PIN {p}\n    USE {use} ;\n    PORT\n{g}    END\n  END {p}\n"
    obs = "  OBS\n    LAYER M7 ;\n      RECT 0 0 20 10 ;\n  END\n" if obs_m7 else ""
    p = Path(d) / f"{name}.lef"
    p.write_text(f"MACRO {name}\n  SIZE 20 BY 10 ;\n{pin('VDD', 'POWER', 1.24)}{pin('VSS', 'GROUND', 0.856)}{obs}END {name}\n")
    return str(p)


def test_m7_top_views_take_publish_mode():
    """PG-CORECONN-3: M7-only PG and M6-PG-under-M7-OBS views are published (die M8 lands them); an M6 view with an
    open M7 keeps the M6 -> M7 grid; a view with PG nowhere stays unlandable."""
    with tempfile.TemporaryDirectory() as d:
        assert gen_phys.core_pg_mode(_m7_lef(d, "a")) == ("publish", "M7")                  # bf_col / capc5r form
        assert gen_phys.core_pg_mode(_m7_lef(d, "b", m6=True)) == ("publish", "M7")         # rom_elem_q form
        assert gen_phys.core_pg_mode(_m7_lef(d, "b", m6=True), strict=False) == ("publish", "M7")
        assert gen_phys.core_pg_mode(_m7_lef(d, "c", m6=True, obs_m7=False)) == ("grid", "M6", "M7")
        assert gen_phys.core_pg_mode(_lef(d)) == ("grid", "M5", "M6")
        with pytest.raises(ValueError):
            gen_phys.core_pg_mode(_lef(d, "x", None, None))


def _P7(d, explicit):
    cores = [dict(inst="u_b.u_e0", module="m7top", lef=_m7_lef(d, "m7top", m6=True), origin_um=[10.0, 20.0]),
             dict(inst="u_b.g[1].u_v", module="m7only", lef=_m7_lef(d, "m7only"), origin_um=[40.0, 20.0],
                  orient="MY"),
             dict(inst="u_b.u_eB", module="core4", lef=_lef(d, "core4", "M4", "M4"), origin_um=[70.0, 20.0])]
    t = dict(outline_um=[100.0, 100.0], hard_cores=cores)
    if explicit:
        t["core_pg_connect"] = True
    return SimpleNamespace(types={"hd": t})


@pytest.mark.parametrize("explicit", [False, True])
def test_publish_instead_of_skip_and_counted_landed(explicit):
    with tempfile.TemporaryDirectory() as d:
        P = _P7(d, explicit)
        mac = gen_phys.type_macros(P, "hd")
        t = gen_phys.core_pg_grids(P, "hd", mac)                 # explicit true no longer raises on M7-top views
        txt = "\n".join(t)
        assert "skipped" not in txt and "-layers {M6 M7}" not in txt
        assert "# PG-CORECONN-3: macro u_b.u_e0 M7 PG straps published" in txt
        assert "add_pdn_connect -grid {core_pg_M4} -layers {M4 M5}" in txt
        pub = gen_phys.core_pg_published(P, "hd", mac)
        assert pub == ["u_b.u_e0", "u_b.g[1].u_v"]
        assert gen_phys.core_pg_unconnected(txt, mac, strict=explicit, published=set(pub)) == []
        # mutant: a publish-mode macro left out of pg_publish.tcl is reported unconnected
        bad = gen_phys.core_pg_unconnected(txt, mac, strict=explicit, published={"u_b.u_e0"})
        assert bad == [("u_b.g[1].u_v", "M7", "die M8 (not published)")]
        P.types["hd"]["core_pg_connect"] = False
        assert gen_phys.core_pg_published(P, "hd", mac) == []


def test_publish_tcl_net_from_master_use_and_overlap_guard():
    tcl = gen_phys.core_pg_publish_tcl(["u_b.u_e0", "u_b.g[1].u_v"])
    assert tcl.startswith("# GENERATED") and "uplevel #0 {" in tcl and tcl.rstrip().endswith("}")
    assert r"pgp_publish {^u_b\.g\\\[1\\\]\.u_v$}" in tcl                          # same regex form as pdngen
    assert "set use [$mt getSigType]" in tcl and "[$n getSigType] ne $use" in tcl     # VDD<-POWER, VSS<-GROUND
    assert "findBTerm [$n getName]" in tcl                                            # bpin on the ITerm's own net
    assert "proc pgp_check" in tcl and "overlaps" in tcl                              # other-net M7 overlap = error
    assert 'error "OT_PG_PUBLISH: published $pgp_insts of 2 macros"' in tcl
    assert tcl.count("{") == tcl.count("}")


def test_kit_post_pdn_publish_and_composition(monkeypatch):
    P1 = schema.Plan(copy.deepcopy(PAIR))
    monkeypatch.setattr(gen_phys, "core_pg_published", lambda *a, **k: ["u_x"])
    monkeypatch.setattr(gen_phys, "core_pg_unconnected", lambda *a, **k: [])
    with tempfile.TemporaryDirectory() as d:
        gen_phys.write_type_kit(P1, "fa", d, [])
        k = Path(d) / "fa"
        assert "pgp_publish {^u_x$}" in (k / "pg_publish.tcl").read_text()
        assert "export POST_PDN_TCL = /work/pg_publish.tcl" in (k / "config.mk").read_text()
        assert not (k / "post_pdn.tcl").exists()
    monkeypatch.setattr(gen_phys, "pg_island_cuts", lambda *a, **k: [("u_x", "rst_n", (1.0, 2.0, 3.0, 4.0))])
    with tempfile.TemporaryDirectory() as d:
        gen_phys.write_type_kit(P1, "fa", d, [])
        k = Path(d) / "fa"
        assert "export POST_PDN_TCL = /work/post_pdn.tcl" in (k / "config.mk").read_text()
        assert (k / "post_pdn.tcl").read_text().splitlines()[1:] == ["source /work/pg_island_cut.tcl",
                                                                     "source /work/pg_publish.tcl"]
