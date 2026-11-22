"""FLOW-FLEET-R2 X1: a stored entry without pins is backfilled once its run dir can give them (the 10 prov_1119 cores)."""
import os, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
os.environ.setdefault("OT_COUNT_SOURCE", "hosts")
import signed_store_ingest as SI   # noqa: E402


def E(i, origin, pins=None):
    return {"id": i, "origin": origin, "pins": pins, "scan": {"pins_path": "/srv/x/pins.json", "name": "n"}}


def test_backfill_sets_missing_pins_on_live_hosts_only_and_throttles():
    mf = [E("a" * 64, "epyc8:/srv/x/signoff/signoff.json"), E("b" * 64, "epyc4:/srv/y/signoff/signoff.json"),
          E("c" * 64, "epyc8:/srv/z/signoff/signoff.json", pins={"rows": []}), E("d" * 64, "origin/main:views/x/signoff.json")]
    got, tried = [], {}
    pinf = lambda h, r: {"rows": [1]} if r["path"].startswith("/srv/x") else None
    setter = lambda i, p: got.append((i, p)) or True
    assert SI.pins_backfill(mf, pinf, setter, tried=tried, now=1e9) == ["a" * 64] and got == [("a" * 64, {"rows": [1]})]
    assert set(tried) == {"a" * 64}                       # epyc4 (terminated), an entry with pins, origin/main: never asked
    assert SI.pins_backfill(mf, pinf, setter, tried=tried, now=1e9 + 500) == []          # asked < 6 h ago: not again
    assert SI.pins_backfill(mf, pinf, setter, tried=tried, now=1e9 + 7 * 3600) == ["a" * 64]


def test_limit_and_unreadable_pins():
    mf = [E("%064x" % i, "epyc8:/srv/q%d/signoff/signoff.json" % i) for i in range(5)]
    asked = []
    SI.pins_backfill(mf, lambda h, r: asked.append(r["path"]) or None, lambda i, p: True, limit=3, tried={}, now=1e9)
    assert len(asked) == 3
