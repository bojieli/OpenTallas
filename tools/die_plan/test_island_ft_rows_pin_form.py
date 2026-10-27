"""CLOCK-KV hm_r26q3: core_pin_form + island_ft_rows G0 checks (positive + mutants)."""
import types
import check as C


def _plan(pins, arcs, w=380.16, h=190.08, rects=None):
    doc = {"pins": pins, "island_ft": {"arcs": arcs}} if arcs else {"pins": pins}
    P = types.SimpleNamespace(types={}, clock={"mesh": {"core_islands": {"m": {"rects_um": rects or []}}}})
    return P, {"cores/m.json": ("m", (w, h), doc)}


ARC = dict(source="ft_ck_i_1", sink="ft_ck_o_1", kind="clock", cells=2, master="BUFx24_ASAP7_75t_R",
           rect_um=[107.46, 138.24, 110.7, 138.51])
FT = [dict(name="ft_ck_i_1", layer="M5", x=106.344, y=138.375), dict(name="ft_ck_o_1", layer="M5", x=111.816, y=138.375)]
RECTS = [[107.46, 138.24, 109.08, 138.51], [109.08, 138.24, 110.7, 138.51]]


def run(fn, P, v):
    R = C.Report()
    out = fn(P, R, None, v)
    return out, [i for i in R.items if i["level"] == "ERROR"]


def test_island_ok():
    P, v = _plan(FT, [ARC], rects=RECTS)
    out, e = run(C.check_island_ft_rows, P, v)
    assert out["arcs"] == 1 and not e


def test_island_off_row():
    a = dict(ARC, rect_um=[107.46, 138.30, 110.7, 138.57])
    P, v = _plan(FT, [a], rects=RECTS)
    assert run(C.check_island_ft_rows, P, v)[1]


def test_island_off_site_and_not_plan():
    a = dict(ARC, rect_um=[107.47, 138.24, 110.71, 138.51])
    P, v = _plan(FT, [a], rects=RECTS)
    e = run(C.check_island_ft_rows, P, v)[1]
    assert e and "site grid" in e[0]["msg"] and "core_islands" in e[0]["msg"]


def test_island_image_off_grid():
    # on the R0 grid but the core height breaks the MX image grid (H - 8.64 not a row multiple)
    P, v = _plan(FT, [ARC], h=190.2, rects=RECTS)
    e = run(C.check_island_ft_rows, P, v)[1]
    assert e and "MX image" in e[0]["msg"]


def test_island_port_off_track():
    ft = [dict(FT[0], x=106.35), FT[1]]
    P, v = _plan(ft, [ARC], rects=RECTS)
    assert run(C.check_island_ft_rows, P, v)[1]


def test_pin_form():
    pins = [dict(name=f"d[{i}]", layer="M5", x=10.0 + i, y=215.904) for i in range(4)]
    P, v = _plan(pins, None, w=216.0, h=216.0)
    assert not run(C.check_core_pin_forms, P, v)[1]
    pins += [dict(name="strap_bsel[0]", layer="M5", x=107.976, y=216.0)]
    P, v = _plan(pins, None, w=216.0, h=216.0)
    e = run(C.check_core_pin_forms, P, v)[1]
    assert e and "strap_bsel[0]" in e[0]["msg"]
    # COORD 10-27 hm_r26q4: a face with only edge-form pins fails too (plan = kit centre form)
    cen = [dict(name=f"d[{i}]", layer="M5", x=10.0 + i, y=215.904) for i in range(4)]
    P, v = _plan(cen + [dict(name="strap_bsel[0]", layer="M4", x=0.0, y=108.0)], None, w=216.0, h=216.0)
    e = run(C.check_core_pin_forms, P, v)[1]
    assert e and "no centre-form" in e[0]["msg"]
    # a data-pin edge face in a centre-form view (qkd_hr_* style) is a warning only
    P, v = _plan(cen + [dict(name="s", layer="M4", x=0.0, y=108.0)], None, w=216.0, h=216.0)
    assert not run(C.check_core_pin_forms, P, v)[1]
    P, v = _plan(cen + [dict(name="strap_bsel[0]", layer="M4", x=0.096, y=108.0)], None, w=216.0, h=216.0)
    assert not run(C.check_core_pin_forms, P, v)[1]
    # an all-edge-form view (qkd_hr_* style) is one form and legal
    P, v = _plan([dict(name="s", layer="M4", x=0.0, y=108.0), dict(name="t", layer="M5", x=10.0, y=216.0)], None,
                 w=216.0, h=216.0)
    assert not run(C.check_core_pin_forms, P, v)[1]
