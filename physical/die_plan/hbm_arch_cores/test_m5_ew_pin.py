import gen_core_kit_hbm as G

M5 = (0.072, 0.096)


def test_m5_e_pin_on_track_and_touches_face():
    p = dict(name="rst_n", layer="M5", x=270.0, y=313.181)
    txt, rows = G.io_tcl([p], 270.0, 403.92, "t", clock_entry=dict(names=[], m5=M5))
    assert "-layer M5 -location {269.9280 313.1810}" in txt
    assert rows[0]["face"] == "E" and rows[0]["entry"] == [269.928, 313.181]
    assert rows[0]["w"] >= 0.048 and rows[0]["h"] == 0.48


def test_other_pins_unchanged():
    ps = [dict(name="a", layer="M4", x=270.0, y=10.0), dict(name="b", layer="M5", x=50.0, y=0.0)]
    with_ce = G.io_tcl(ps, 270.0, 403.92, "t", clock_entry=dict(names=[], m5=M5))
    assert with_ce == G.io_tcl(ps, 270.0, 403.92, "t")


def test_no_clock_entry_mode_keeps_old_form():
    p = dict(name="rst_n", layer="M5", x=270.0, y=313.181)
    assert "-pin_size {0.1920 0.0240}" in G.io_tcl([p], 270.0, 403.92, "t")[0]


def test_resume_fix_matches_generator(tmp_path):
    import m5_ew_pin_fix as F

    p = dict(name="rst_n", layer="M5", x=270.0, y=313.181)
    good = G.io_tcl([p], 270.0, 403.92, "t", clock_entry=dict(names=[], m5=M5))[0]
    (tmp_path / "io.tcl").write_text("place_pin -pin_name {rst_n} -layer M5 -location {269.9040 313.1810} -pin_size {0.1920 0.0240}\n")
    (tmp_path / "config.mk").write_text("export DIE_AREA = 0 0 270 403.92\n")
    (tmp_path / "core_grt_pre.tcl").write_text("source /work/max_fanout.tcl\n")
    moved = F.fix(tmp_path)
    assert len(moved) == 1 and moved[0] in good
    assert (tmp_path / "core_grt_pre.tcl").read_text().startswith("source /work/m5_ew_pin_fix.tcl")
    assert F.fix(tmp_path) == []
