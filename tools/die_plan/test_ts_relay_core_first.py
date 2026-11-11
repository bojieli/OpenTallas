"""STATION-FIX-HBM 11-11 (COORD S7): ts_relay_event writes native-OUT relay entries core -> face.  The 13 HBM relay
entries of plan 29333b2b, regenerated in the new form from their own window / core ends and sites, run core -> face in
kit order (no INVERTED chain), equal the stationfix_1111 plan event output and keep identical native_istations source
entries (bind digest unchanged)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import native_istations as NI  # noqa: E402
import ts_relay_event as TE  # noqa: E402

ROWS = json.loads((HERE / "test_ts_relay_core_first_hbm.json").read_text())["rows"]


def _edge(p, o, tol=2.0):
    return min(p[0], p[1], o[0] - p[0], o[1] - p[1]) <= tol


def _inverted(e, o):
    """kit order = regs_um as written (core-launched OUT entry); stage 0 must be the stage farthest from the face end
    (station_lint S7: INVERTED when stage 0 sits nearer the face than the last stage by a quarter of the length)"""
    face = e["to_um"] if _edge(e["to_um"], o) else e["from_um"]
    d = [abs(r[0] - face[0]) + abs(r[1] - face[1]) for r in e["regs_um"]]
    L = abs(e["from_um"][0] - e["to_um"][0]) + abs(e["from_um"][1] - e["to_um"][1])
    return d[0] - d[-1] < -max(10.0, 0.25 * L)


def test_old_form_is_inverted_new_form_is_not():
    assert len(ROWS) == 13
    for r in ROWS:
        old, o = r["entry"], r["outline_um"]
        assert _edge(old["from_um"], o) and not _edge(old["to_um"], o) and _inverted(old, o), (r["type"], r["bus"])
        new = dict(old, **TE.out_core_first(old["from_um"], old["to_um"], old["regs_um"]))
        assert _edge(new["to_um"], o) and not _edge(new["from_um"], o), (r["type"], r["bus"])
        assert not _inverted(new, o), (r["type"], r["bus"])
        assert sorted(map(tuple, new["regs_um"])) == sorted(map(tuple, old["regs_um"]))   # same sites, same count


def test_new_form_equals_plan_event_and_native_entries():
    ev = HERE.parents[1] / "physical/die_plan/hbm/plan_of_record/stationfix_1111/event.py"
    import importlib.util
    spec = importlib.util.spec_from_file_location("stationfix_event", ev)
    E = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(E)
    for r in ROWS:
        old = r["entry"]
        new = dict(old, **TE.out_core_first(old["from_um"], old["to_um"], old["regs_um"]))
        t = dict(outline_um=r["outline_um"], buses=[r["bus"]], internal_stations=[old])
        flipped, _ = E.apply(dict(partition_types={r["type"]: t}), ((r["type"], r["bus"]["name"], 0, old["launch"]),))
        assert flipped["partition_types"][r["type"]]["internal_stations"][0] == new
        a = NI.source_entries(t, {r["bus"]["name"]})
        b = NI.source_entries(dict(t, internal_stations=[new]), {r["bus"]["name"]})
        assert a == b and len(a) == 1
