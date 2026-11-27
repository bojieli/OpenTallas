"""view_pg_port: LEF PG PORT vs signed DEF (C-VIEW-PG-PORT-STALE)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pytest
import view_pg_port as v

DEF = """VERSION 5.8 ;
DESIGN m_x ;
UNITS DISTANCE MICRONS 1000 ;
PINS 2 ;
  - VDD + NET VDD + DIRECTION INOUT + USE POWER
    + PORT
      + LAYER M5 ( 0 0 ) ( 120 20000 )
      + PLACED ( 6000 4000 ) N
    + PORT
      + LAYER M5 ( 0 0 ) ( 120 20000 )
      + PLACED ( 10320 4000 ) N
 ;
  - VSS + NET VSS + DIRECTION INOUT + USE GROUND
    + PORT
      + LAYER M5 ( 0 0 ) ( 120 20000 )
      + PLACED ( 8000 4000 ) N
 ;
END PINS
END DESIGN
"""


def lef(vdd, vss):
    def pin(n, use, rects):
        body = "".join(f"      RECT  {r} ;\n" for r in rects)
        return (f"  PIN {n}\n    DIRECTION INOUT ;\n    USE {use} ;\n    PORT\n      LAYER M5 ;\n{body}    END\n  END {n}\n")
    return ("VERSION 5.8 ;\nMACRO m_x\n  SIZE 43.2 BY 77.76 ;\n" + pin("VDD", "POWER", vdd) + pin("VSS", "GROUND", vss)
            + "  PIN a\n    DIRECTION INPUT ;\n    PORT\n      LAYER M3 ;\n      RECT  1 1 2 2 ;\n    END\n  END a\n"
            + "  OBS\n    LAYER M1 ;\n      RECT  0 0 1 1 ;\n  END\nEND m_x\n")


GOOD = lef(["6.000 4.000 6.120 24.000", "10.320 4.000 10.440 24.000"], ["8.000 4.000 8.120 24.000"])
STALE = lef(["6.000 4.000 6.120 24.000", "8.700 4.000 8.820 24.000", "10.320 4.000 10.440 24.000"], ["8.000 4.000 8.120 24.000"])


@pytest.fixture
def contract(tmp_path):
    d = tmp_path / "6_final.def"
    d.write_text(DEF)
    m, c = v.signed_ports(d)
    assert m == "m_x"
    return c


def test_signed_ports_origin_applied(contract):
    assert contract["ports"]["VDD"][0] == ["M5", 6000, 4000, 6120, 24000] or tuple(contract["ports"]["VDD"][0]) == ("M5", 6000, 4000, 6120, 24000)
    assert len(contract["ports"]["VSS"]) == 1


def test_compare_ok_and_stale(contract):
    assert v.compare(GOOD, contract)[0]
    ok, rep = v.compare(STALE, contract)
    assert not ok and rep["VDD"]["count"] == [2, 3] and rep["VDD"]["extra"] == 1 and rep["VSS"]["equal"]


def test_regen_port_only(contract):
    out = v.regenerate(STALE, contract, "m_x")
    assert v.compare(out, contract)[0]

    def strip(t):
        for p in v.PG:
            m = v.lef_pin(t, p)
            t = t[:m.start()] + t[m.end():]
        return t
    assert strip(out) == strip(STALE)


def test_regen_layer_change_refused(contract):
    bad = STALE.replace("LAYER M5 ;\n      RECT  6.000", "LAYER M4 ;\n      RECT  6.000")
    with pytest.raises(ValueError):
        v.regenerate(bad, contract, "m_x")


def test_plan_check_report_only(tmp_path, contract):
    (tmp_path / "views").mkdir()
    (tmp_path / "views" / "good.lef").write_text(GOOD)
    (tmp_path / "views" / "stale.lef").write_text(STALE)
    (tmp_path / "views" / "other.lef").write_text(GOOD.replace("MACRO m_x", "MACRO m_y").replace("END m_x", "END m_y"))
    cpath = tmp_path / "c.json"
    cpath.write_text(json.dumps(dict(schema=v.SCHEMA, masters={"m_x": contract})))
    plan = {"partition_types": {"t1": {"hard_cores": [{"lef": "views/stale.lef"}, {"lef": "views/good.lef"}, {"lef": "views/other.lef"}, {"lef": "views/gone.lef"}]},
                                "t2": {"hard_cores": [{"lef": "views/stale.lef"}]}}}
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))
    lines, recs = v.plan_check(plan, v.load_contract(cpath), plan_path)
    assert len(lines) == 1 and "2 pointers" in lines[0] and "VIEW-PG-PORT m_x" in lines[0]
    st = {r["lef"]: r["status"] for r in recs}
    assert st == {"views/stale.lef": "DIFF", "views/good.lef": "ok", "views/other.lef": "nocontract", "views/gone.lef": "unresolved"}
    assert v.main(["check", str(plan_path), "--contract", str(cpath)]) == 0          # report-only
    assert v.main(["check", str(plan_path), "--contract", str(cpath), "--strict"]) == 1
