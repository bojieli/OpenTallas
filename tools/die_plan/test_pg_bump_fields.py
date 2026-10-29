"""QC-PG-5 (OWNER 10-28 option c): opt-in fine-pitch power-bump fields in die.pg.bumps (die_trial._field_bumps)."""
from types import SimpleNamespace
import subprocess
import pytest
import die_trial as D
import schema
from test_pg_bump_contract import MOCK


def plan(**cfg):
    return SimpleNamespace(W=3000., H=2000., die={"pg": {"bumps": cfg}})


FIELD = dict(name="a0_p75", pitch_um=75., pad_um=37.5, keep_um=75., rects_um=[[600., 500., 1500., 1400.]])


def test_no_fields_is_unchanged():
    base = D.bump_grid(plan(pitch_um=150., pad_um=70.), [])
    assert base == D.bump_grid(plan(pitch_um=150., pad_um=70., fields=[]), [])
    assert all(len(b) == 3 for b in base)
    assert D.bump_grid(plan(pitch_um=150., pad_um=70.), [], pads=True) == [b + (70.,) for b in base]


def test_field_replaces_base_and_keeps_distance():
    b = D.bump_grid(plan(pitch_um=150., pad_um=70., fields=[FIELD]), [], pads=True)
    fine = [x for x in b if x[3] == 37.5]
    coarse = [x for x in b if x[3] == 70.]
    r = FIELD["rects_um"][0]
    assert fine and all(r[0] <= x <= r[2] and r[1] <= y <= r[3] for _, x, y, _ in fine)
    xs = sorted({x for _, x, _, _ in fine})
    assert all(abs(q - p - 75.) < 1e-6 for p, q in zip(xs, xs[1:]))
    assert all(max(abs(x - a), abs(y - c)) >= 75. for _, x, y, _ in coarse for _, a, c, _ in fine)
    # half the field bumps are VDD (parity checkerboard), and the base far away is untouched
    assert abs(sum(1 for f in fine if f[0] == "VDD") - len(fine) / 2) <= 1
    far = [x[:3] for x in coarse if x[1] > 1700]
    assert far == [q for q in D.bump_grid(plan(pitch_um=150., pad_um=70.), []) if q[1] > 1700]
    assert [x[:3] for x in b] == D.bump_grid(plan(pitch_um=150., pad_um=70., fields=[FIELD]), [])


def test_field_lattice_shares_the_base_lattice():
    b = D.bump_grid(plan(pitch_um=150., pad_um=70., fields=[FIELD]), [], pads=True)
    base_x = {x for _, x, _ in D.bump_grid(plan(pitch_um=150., pad_um=70.), [])}
    fx = {x for _, x, _, p in b if p == 37.5}
    assert base_x & fx                 # 75 = 150/2, both die-centred -> every other field column is a base column


def test_field_respects_io_windows():
    io = [{"rect_um": [900., 900., 1000., 1000.]}]
    b = D.bump_grid(plan(pitch_um=150., pad_um=70., fields=[FIELD]), io, pads=True)
    assert not [x for x in b if x[1] + x[3] / 2 > 900 and x[1] - x[3] / 2 < 1000 and x[2] + x[3] / 2 > 900 and x[2] - x[3] / 2 < 1000]


@pytest.mark.parametrize("bad", [dict(pitch_um=0.), dict(pad_um=80.), dict(keep_um=10.), dict(rects_um=[]),
                                 dict(rects_um=[[5, 5, 1, 1]]), dict(pad_um=True)])
def test_field_validation(bad):
    with pytest.raises(ValueError):
        D.bump_contract(plan(pitch_um=150., pad_um=70., fields=[dict(FIELD, **bad)]))


def test_schema_accepts_fields():
    props = schema.SCHEMA["properties"]["die"]["properties"]["pg"]["properties"]["bumps"]["properties"]
    assert set(props["fields"]["items"]["required"]) == {"name", "pitch_um", "pad_um", "keep_um", "rects_um"}


def test_mixed_pad_tcl_contacts_with_own_pad():
    p = plan(pitch_um=150., pad_um=70.)
    t = D.bumps_tcl(p, [("VDD", 75, 75, 70.), ("VDD", 100, 75, 6.)])
    assert "ot_pad VDD 0 75 75 70" in t and "ot_pad VDD 1 100 75 6" in t and "OT_BUMPS mixed pads 6:1 70:1" in t
    r = subprocess.run(["tclsh"], input=MOCK + "\n" + t + '\nputs "BOXES $boxes"\n', text=True, capture_output=True)
    # 70-um pad at x 75 hits both VDD stripes (50-55, 100-105); 6-um pad at x 100 hits only the 100-105 stripe
    assert "BOXES {50 40 55 110} {100 40 105 110} {100 72 103 78}" in r.stdout, r.stdout + r.stderr
    assert D.bumps_tcl(p, [("VDD", 75, 75)]) == D.bumps_tcl(p, [("VDD", 75, 75)])
    assert "ot_pad VDD 0 75 75\n" in D.bumps_tcl(p, [("VDD", 75, 75)])
