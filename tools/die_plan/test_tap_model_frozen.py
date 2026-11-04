"""clock.tap_model "frozen_anchor": opt-in reproduction of the taps a frozen plan was solved with."""
import pytest
import pin_frozen_tap_model as PIN
import schema as S
import taps
from test_density_taps import _no_pins, _plan

SITES = [[100, 350, 10], [350, 100, 10], [350, 500, 10]]


def _taps(monkeypatch, **ck):
    _no_pins(monkeypatch)
    P = _plan(SITES, cores=[], tap_min_sinks=1, tap_radius_um=600, **ck)
    return P, taps.density_taps(P, "hd")


def test_default_and_consumed_are_the_same_model(monkeypatch):
    assert _taps(monkeypatch)[1] == _taps(monkeypatch, tap_model="consumed")[1]


def test_frozen_anchor_is_not_snapped_to_consumed_tracks(monkeypatch):
    import gen_phys
    P, frozen = _taps(monkeypatch, tap_model="frozen_anchor")
    default = _taps(monkeypatch)[1]
    snap = lambda x, y: gen_phys._snap_tap(P, x, y, pg_legal=True)
    assert all(snap(x, y) == (x, y) for _, x, y, _, _ in default)
    assert any(snap(x, y) != (x, y) for _, x, y, _, _ in frozen)
    assert sum(r[3] for r in frozen) == sum(r[3] for r in default) == 30


def test_frozen_anchor_uses_placed_macros_only_in_tap_clear():
    reuse = dict(inst="reuse", origin_um=[40., 40.], outline_um=[100., 100.])
    t = dict(outline_um=[250., 250.], contents=[reuse], clock=dict(tap_model="frozen_anchor"))
    assert S.tap_clear(t, 80., 80.) == (80., 80.)
    t["clock"] = {}
    assert S.tap_clear(t, 80., 80.) != (80., 80.)


@pytest.mark.parametrize("model, bit_sites", [("frozen_anchor", False), ("consumed", True), (None, True)])
def test_sink_census_follows_the_model(monkeypatch, model, bit_sites):
    seen = []
    monkeypatch.setattr(taps, "planned_sinks", lambda P, tn, bit_sites=False: seen.append(bit_sites) or [(1., 1., "f")])
    ck = {} if model is None else dict(tap_model=model)
    P = _plan([], cores=[], **ck)
    del P.types["hd"]["clock"]["sink_sites_um"]
    assert taps.sink_sites(P, "hd") == [(1., 1., 1.)]
    assert seen == [bit_sites]


def test_schema_accepts_only_the_two_models():
    ck = S.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]
    assert ck["tap_model"]["enum"] == ["consumed", "frozen_anchor"]


def test_pin_sets_both_models_on_every_type_and_nothing_else():
    raw = dict(note="n", partition_types=dict(a=dict(hard=False, clock=dict(tap_mode="density")), b=dict(reset=dict(k=1))))
    PIN.pin(raw)
    assert raw == dict(note="n", partition_types=dict(
        a=dict(hard=False, clock=dict(tap_mode="density", tap_model="frozen_anchor"),
               reset=dict(obstacle_model="lef_origin")),
        b=dict(reset=dict(k=1, obstacle_model="lef_origin"), clock=dict(tap_model="frozen_anchor"))))


def test_pin_refuses_in_place(tmp_path):
    f = tmp_path / "p.json"
    f.write_text("{}")
    with pytest.raises(SystemExit):
        PIN.main(["x", str(f), str(f)])
