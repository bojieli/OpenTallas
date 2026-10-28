"""CORES-EARLY-1 10-28: delta_signed_view_pins_1028 -- stale-abstract plan tables follow the SIGNED view, kits cut
from the plan table are left alone, stale kits (pin set differs) are refused."""
import hashlib
import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("dsvp", os.path.join(HERE, "delta_signed_view_pins_1028.py"))
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)

LEF = """MACRO {m}
  SIZE 10.0 BY 5.0 ;
  PIN a
    DIRECTION INPUT ;
    PORT
      LAYER M4 ;
        RECT 0.0 {y0} {x1} {y1} ;
    END
  END a
  PIN z
    DIRECTION OUTPUT ;
    PORT
      LAYER M4 ;
        RECT {zx0} {y0} 10.0 {y1} ;
    END
  END z
END {m}
"""


def mk(tmp, m, x1, zx0, signed_rows, plan_rows, freeze_from_plan=False):
    y0, y1 = 2.148, 2.172                     # M4 centre 2.16 is on track with the 0.012 core offset
    vd = tmp / "views" / m
    vd.mkdir(parents=True)
    (vd / (m + ".lef")).write_text(LEF.format(m=m, x1=x1, zx0=zx0, y0=y0, y1=y1))
    (vd / "signoff.json").write_text(json.dumps(dict(verdict="SIGNED")))
    (vd / "pins.json").write_text(json.dumps(signed_rows))
    pd = tmp / "plan" / "inputs" / "core_pins"
    pd.mkdir(parents=True, exist_ok=True)
    tf = pd / (m + ".json")
    tf.write_text(json.dumps(dict(module=m, lef="old.lef", source="CORE-KS", pins=plan_rows)))
    if freeze_from_plan:
        (vd / "freeze.json").write_text(json.dumps(dict(pins_sha256=hashlib.sha256(tf.read_bytes()).hexdigest())))
    return dict(module=m, inst="u", outline_um=[10.0, 5.0], pins_file="inputs/core_pins/%s.json" % m, lef="old.lef")


def run(tmp, hc, write=True):
    plan = dict(partition_types=dict(t=dict(hard_cores=[hc])))
    rep = D.run(plan, str(tmp / "plan"), write, views=str(tmp / "views"))
    return plan, rep


def test_stale_abstract_table_follows_signed_view(tmp_path):
    # old plan table: deep pin (0..0.2 centre 0.1); signed abstract: shallow pin (0..0.084 centre 0.042)
    signed = [dict(bus="a", bit=None, layer="M4", x=0.042, y=2.16, face="W"),
              dict(bus="z", bit=None, layer="M4", x=9.958, y=2.16, face="E")]
    hc = mk(tmp_path, "c1", 0.084, 9.916, signed,
            [dict(name="a", layer="M4", x=0.1, y=2.16), dict(name="z", layer="M4", x=9.9, y=2.16)])
    plan, rep = run(tmp_path, hc)
    r = list(rep.values())[0]
    assert r["status"] == "PLAN-STALE", r
    t = json.loads((tmp_path / "plan" / hc["pins_file"]).read_text())
    assert [(p["name"], p["x"]) for p in t["pins"]] == [("a", 0.042), ("z", 9.958)]
    assert plan["partition_types"]["t"]["hard_cores"][0]["lef"].endswith("views/c1/c1.lef")


def test_kit_cut_from_plan_table_is_left_alone(tmp_path):
    signed = [dict(bus="a", bit=None, layer="M4", x=0.042, y=2.16, face="W"),
              dict(bus="z", bit=None, layer="M4", x=9.958, y=2.16, face="E")]
    rows = [dict(name="a", layer="M4", x=0.1, y=2.16), dict(name="z", layer="M4", x=9.9, y=2.16)]
    hc = mk(tmp_path, "c2", 0.084, 9.916, signed, rows, freeze_from_plan=True)
    before = (tmp_path / "plan" / hc["pins_file"]).read_bytes()
    plan, rep = run(tmp_path, hc)
    assert list(rep.values())[0]["status"] == "SAME"
    assert (tmp_path / "plan" / hc["pins_file"]).read_bytes() == before
    assert plan["partition_types"]["t"]["hard_cores"][0]["lef"] == "old.lef"


def test_stale_kit_with_other_pin_set_is_refused(tmp_path):
    # mutant: the view was signed on a wider interface (extra pin) -> re-sign, never a plan edit
    signed = [dict(bus="a", bit=None, layer="M4", x=0.042, y=2.16, face="W"),
              dict(bus="z", bit=None, layer="M4", x=9.958, y=2.16, face="E"),
              dict(bus="y", bit=200, layer="M4", x=0.042, y=3.0, face="W")]
    hc = mk(tmp_path, "c3", 0.084, 9.916, signed,
            [dict(name="a", layer="M4", x=0.1, y=2.16), dict(name="z", layer="M4", x=9.9, y=2.16)])
    before = (tmp_path / "plan" / hc["pins_file"]).read_bytes()
    plan, rep = run(tmp_path, hc)
    assert list(rep.values())[0]["status"] == "KIT-STALE"
    assert (tmp_path / "plan" / hc["pins_file"]).read_bytes() == before


def test_rule_diff_is_not_written(tmp_path):
    # signed pin table disagrees with the CORE-KS pick of the signed LEF -> not a stale-abstract case
    signed = [dict(bus="a", bit=None, layer="M4", x=0.5, y=2.16, face="W"),
              dict(bus="z", bit=None, layer="M4", x=9.958, y=2.16, face="E")]
    hc = mk(tmp_path, "c4", 0.084, 9.916, signed,
            [dict(name="a", layer="M4", x=0.1, y=2.16), dict(name="z", layer="M4", x=9.9, y=2.16)])
    plan, rep = run(tmp_path, hc)
    assert list(rep.values())[0]["status"] == "RULE-DIFF"


def test_second_plan_after_tables_moved_is_repointed(tmp_path):
    signed = [dict(bus="a", bit=None, layer="M4", x=0.042, y=2.16, face="W"),
              dict(bus="z", bit=None, layer="M4", x=9.958, y=2.16, face="E")]
    hc = mk(tmp_path, "c5", 0.084, 9.916, signed,
            [dict(name="a", layer="M4", x=0.1, y=2.16), dict(name="z", layer="M4", x=9.9, y=2.16)])
    run(tmp_path, dict(hc))
    plan2, rep = run(tmp_path, dict(hc))          # another plan sharing the (now rewritten) table
    assert list(rep.values())[0]["status"] == "FOLLOWS-VIEW"
    assert plan2["partition_types"]["t"]["hard_cores"][0]["lef"].endswith("views/c5/c5.lef")
