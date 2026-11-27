"""FACE-SITE-KEEP-1127 / C-RST-WAVEFRONT-UNPINNED (HEAD-TILE-R3): partition_types[T].reset.face_sites_um
{"<face><j>": [x, y]} pins a soft type's reset face site j at a published xy, so a local re-form of T keeps the die reset
wavefront (every part's parent, release and every other type's reset tree).  Opt-in: absent = unchanged.
Synthetic fixture only (examples/tiny_plan.json as a wavefront die); the k2 HEAD repro lives outside the repo.
    python3 -I -m pytest -q tools/die_plan/test_reset_wavefront_pin.py"""
import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reset_tree as RT  # noqa: E402
import schema  # noqa: E402

TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def wf_raw(**type_reset):
    raw = copy.deepcopy(TINY)
    raw.setdefault("reset", {}).update(release="wavefront")
    for tn, rs in type_reset.items():
        raw["partition_types"][tn].setdefault("reset", {}).update(rs)
    return raw


def snap(raw):
    P = schema.Plan(copy.deepcopy(raw))
    s = RT.wf_solve(P)
    soft = sorted(t for t in P.types if not P.types[t].get("hard"))
    return dict(sites={t: [(f["face"], f["j"], tuple(f["xy"]), f["mid"]) for f in RT.face_sites(P, t)] for t in soft},
                parent=s["parent"], rel=s["est_rel"], unr=s["unreachable"], choice=s["choice"], outs=s["outs"],
                trees={t: [(r["q"], tuple(r["xy"]), r.get("depth")) for r in RT.for_type(P, t)["relays"]] for t in soft})


def test_absent_and_empty_field_are_the_default():
    raw = wf_raw()
    assert schema.validate(copy.deepcopy(raw)) == []
    base = snap(raw)
    assert snap(wf_raw(mid={"face_sites_um": {}})) == base


def test_pinning_every_site_at_its_own_xy_is_a_fixed_point():
    base = snap(wf_raw())
    keep = {t: {"face_sites_um": {f"{f}{j}": list(xy) for f, j, xy, _m in base["sites"][t]}} for t in base["sites"]}
    raw = wf_raw(**keep)
    assert schema.validate(copy.deepcopy(raw)) == []
    assert snap(raw) == base


def test_kept_site_moves_only_that_site():
    base = snap(wf_raw())
    f, j, (x, y), _m = next(s for s in base["sites"]["mid"] if s[0] == "E")
    P0 = schema.Plan(wf_raw())
    new = RT._snap(P0, x, y + 30.0)
    got = snap(wf_raw(mid={"face_sites_um": {f"{f}{j}": list(new)}}))["sites"]["mid"]
    for a, b in zip(base["sites"]["mid"], got):
        assert b[2] == (tuple(new) if (b[0], b[1]) == (f, j) else a[2])


@pytest.mark.parametrize("key,dxy,why", [("E99", (0, 0), "names no face site"),
                                         ("E0", (0.0011, 0), "off the tap grid"),
                                         ("E0", (-200.0, 0), "not within")])
def test_bad_kept_site_fails_closed(key, dxy, why):
    base = snap(wf_raw())
    x, y = next(s[2] for s in base["sites"]["mid"] if s[0] == "E" and s[1] == 0)
    P0 = schema.Plan(wf_raw())
    xy = (x + dxy[0], y + dxy[1]) if why != "not within" else RT._snap(P0, x + dxy[0], y)
    P = schema.Plan(wf_raw(mid={"face_sites_um": {key: list(xy)}}))
    with pytest.raises(RT.ResetError, match=why):
        RT.face_sites(P, "mid")


def test_kept_site_inside_a_hard_core_fails_closed(monkeypatch):
    base = snap(wf_raw())
    x, y = next(s[2] for s in base["sites"]["mid"] if s[0] == "E" and s[1] == 0)
    real = RT.blockages
    monkeypatch.setattr(RT, "blockages", lambda t, clear=RT.CLEAR_UM: (list(real(t, clear)) +
                        ([(x - 5.0, y - 5.0, x + 5.0, y + 5.0)] if clear == 0.0 else [])))
    P = schema.Plan(wf_raw(mid={"face_sites_um": {"E0": [x, y]}}))
    with pytest.raises(RT.ResetError, match="inside hard core"):
        RT.face_sites(P, "mid")


def test_schema_checks_the_xy_shape():
    assert schema.validate(wf_raw(mid={"face_sites_um": {"E0": [1.0]}})) != []
