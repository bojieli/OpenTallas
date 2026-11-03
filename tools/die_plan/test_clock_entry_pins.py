"""clock_entry_pins.py: clock pins of a pin table move to the plan clock entry exactly as gen_core_kit_hbm places them;
--keep tables and tables without an entry are unchanged; bus/bit rows are handled (DIE-HBM-60 11-03)."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clock_entry_pins as C  # noqa: E402


def _plan(d):
    hc = lambda m, pf: dict(inst=f"u_{m}", module=m, origin_um=[0, 0], outline_um=[100.0, 50.0], pins_file=pf)
    P = dict(schema="opentallas.die_plan.v1", die=dict(name="t", period_ps=833, outline_um=[200.0, 100.0]),
             partition_types={"T": dict(hard_cores=[hc("ma", "cores/ma.json"), hc("mb", "cores/mb.json"),
                                                    hc("mc", "cores/mc.json"), hc("md", "cores/md.json")])},
             partitions=[dict(name="p0", type="T")])
    (d / "cores").mkdir()
    face = [dict(name="clk", layer="M5", x=10.008, y=0.24), dict(name="d[0]", layer="M4", x=0.0, y=20.0)]
    for m in ("ma", "mb", "mc"):
        (d / "cores" / f"{m}.json").write_text(json.dumps(face))
    (d / "cores" / "md.json").write_text(json.dumps([dict(bus="clk", bit=None, face="S", layer="M5", x=10.008, y=0.0)]))
    ent = {"p0": {"a": dict(module="ma", xy_um=[50.0, 25.0], port="clk"),
                  "c": dict(module="mc", xy_um=[50.0, 25.0], port="clk"),
                  "d": dict(module="md", xy_um=[40.0, 20.0], port="clk")}}
    (d / "clock_entries.json").write_text(json.dumps(ent))
    (d / "die_plan.json").write_text(json.dumps(P))


def test_moves_keeps_and_matches_generator():
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        _plan(d)
        ev, Q, files = C.run(d, keep=["mc"], write=d / "out")
        T = {r["module"]: r for r in ev["tables"].values()}
        assert T["ma"]["status"] == "MOVED" and T["md"]["status"] == "MOVED"
        assert T["mb"]["status"].startswith("UNCHANGED")          # no entry for mb
        assert T["mc"]["status"].startswith("KEPT")               # signed record
        P = json.loads((d / "die_plan.json").read_text())
        m5 = C.m5_of(P)
        mv, _ = C.G.plan_clock_entries(d / "clock_entries.json", "ma", ["clk"], 100.0, 50.0, m5)
        assert T["ma"]["moved"]["clk"] == list(mv["clk"])         # generator's own number
        new = json.loads((d / "out" / "cores" / "ma__centry.json").read_text())
        assert [p for p in new if p["name"] == "d[0]"][0] == dict(name="d[0]", layer="M4", x=0.0, y=20.0)
        hcs = {h["module"]: h["pins_file"] for h in Q["partition_types"]["T"]["hard_cores"]}
        assert hcs == {"ma": "cores/ma__centry.json", "mb": "cores/mb.json", "mc": "cores/mc.json",
                       "md": "cores/md__centry.json"}
        newd = json.loads((d / "out" / "cores" / "md__centry.json").read_text())
        assert newd[0]["bus"] == "clk" and (newd[0]["x"], newd[0]["y"]) == tuple(T["md"]["moved"]["clk"])


def test_check_kit_flags_difference():
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        _plan(d)
        ev, _, _ = C.run(d)
        x, y = ev["tables"]["ma|cores/ma.json"]["moved"]["clk"]
        good, bad = d / "good.json", d / "bad.json"
        good.write_text(json.dumps(dict(view="ma@1", source="cores/ma.json", pins=[dict(name="clk", layer="M5", x=x, y=y)])))
        bad.write_text(json.dumps(dict(view="ma@1", source="cores/ma.json", pins=[dict(name="clk", layer="M5", x=10.008, y=0.24)])))
        assert C.check_kits(ev, [good])[1:] == (1, [])
        used, ok, mis = C.check_kits(ev, [bad])
        assert used == 1 and ok == 0 and len(mis) == 1


if __name__ == "__main__":
    test_moves_keeps_and_matches_generator()
    test_check_kit_flags_difference()
    print("PASS 2")
