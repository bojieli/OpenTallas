import landing_place as LP


def _t(extra):
    c = {"depth": 1, "branches": {"a_o": {"stages": [{"xy_um": [10.0, 20.0], "raw_reset": "rst_n_t0"}]}}}
    c.update(extra)
    return {"outline_um": [100.0, 100.0], "clock": {"landing_writer_start": c}}


def test_absent_origin_rect_unchanged():
    g = LP._writer_start_groups(_t({}))
    assert [x[0] for x in g] == ["u_cland_writer_start_a_o_0"]


def test_origin_rect_adds_origin_group_first():
    g = LP._writer_start_groups(_t({"origin_rect_um": [1, 2, 3, 4]}))
    assert g[0] == ("u_cland_origin", [1, 2, 3, 4], "writer-start-origin")
    assert g[1][0] == "u_cland_writer_start_a_o_0"


def test_relay_copy_origin_name():
    t = _t({"origin_rect_um": [1, 2, 3, 4]}); t["landing_relay_start_copy"] = True
    assert LP._writer_start_groups(t)[0][0] == "u_cland_rstart_rx"
