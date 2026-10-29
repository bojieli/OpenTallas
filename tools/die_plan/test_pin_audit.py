"""pin_audit.py: interior island clock pin face (QC-SU-F4A-SIGN KeyError island) + scalar keys + face pins."""
from tools.die_plan import pin_audit as PA

W, H = 250.56, 216.0


def test_island_face_interior_pin_exact_xy():
    p = dict(bus="ck", bit=None, layer="M5", x=125.292, y=108.0, face="island")
    assert PA.pin_key(p) == "ck"
    assert PA.box_ok(p, (125.276, 107.904, 125.308, 108.096), W, H)          # centred on the plan entry
    assert not PA.box_ok(p, (125.324, 107.904, 125.356, 108.096), W, H)      # moved one M5 track in x
    assert not PA.box_ok(p, (125.276, 107.952, 125.308, 108.144), W, H)      # moved in y
    assert not PA.box_ok(dict(p, x=0.016), (-0.032, 107.904, 0.064, 108.096), W, H)   # outside the die


def test_face_pins_unchanged():
    w = dict(bus="addr", bit=0, layer="M4", x=0.042, y=207.516, face="W")
    assert PA.pin_key(w) == "addr[0]"
    assert PA.box_ok(w, (0.0, 207.504, 0.084, 207.528), W, H)
    assert not PA.box_ok(w, (0.1, 207.504, 0.184, 207.528), W, H)             # off the face
    s = dict(bus="d", bit=3, layer="M5", x=50.004, y=0.0, face="S")
    assert PA.box_ok(s, (49.988, 0.0, 50.020, 0.192), W, H)
    assert not PA.box_ok(s, (49.988, 1.0, 50.020, 1.192), W, H)


def test_interior_ports_not_extra():
    for n in ("clk", "clk_t3", "arst_n", "ft_ck_i", "ft_ck_o", "ft_rst_i", "ft_rst_o", "mp_isl0_ck"):
        assert PA.INTERIOR.match(n), n
    for n in ("ck", "fault", "w16_we", "ft_data_i"):
        assert not PA.INTERIOR.match(n), n


def test_face_edge_exact_one_nm_decimal_boundary():
    # Actual CFG7 N-face geometry: 60.481 - 60.48 rounds above 0.001.
    p = dict(bus="cfg", bit=32, layer="M3", x=20.493, y=60.4615, face="N")
    assert PA.box_ok(p, (20.484, 60.443, 20.502, 60.481), 30.24, 60.48)
    assert not PA.box_ok(p, (20.484, 60.443, 20.502, 60.481001), 30.24, 60.48)
