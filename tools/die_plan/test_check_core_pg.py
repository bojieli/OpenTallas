"""PG-CORECONN-2: G0 core_pg check (hard-core macros must set core_pg_connect; LEFs must carry landable PG pins).
python3 -m pytest -q tools/die_plan/test_check_core_pg.py"""
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402


def _lef(d, name, vdd="M5", vss="M5"):
    def pin(p, use, lay):
        geo = f"    PORT\n      LAYER {lay} ;\n        RECT 3.0 1.0 3.2 9.0 ;\n    END\n" if lay else ""
        return f"  PIN {p}\n    USE {use} ;\n{geo}  END {p}\n"
    p = Path(d) / f"{name}.lef"
    p.write_text(f"MACRO {name}\n  SIZE 20 BY 10 ;\n{pin('VDD', 'POWER', vdd)}{pin('VSS', 'GROUND', vss)}END {name}\n")
    return str(p)


def _P(d, connect=True, lef_kw=None, n_parts=2):
    cores = [dict(inst="u_b.u_eA", module="core", lef=_lef(d, "core", **(lef_kw or {})), origin_um=[10.0, 20.0])]
    types = {"hd": dict(outline_um=[100.0, 100.0], hard_cores=cores, core_pg_connect=connect),
             "glue": dict(outline_um=[50.0, 50.0])}
    parts = {f"p{i}": dict(type="hd") for i in range(n_parts)}
    parts["g0"] = dict(type="glue")
    return SimpleNamespace(types=types, parts=parts, die={})


def _run(P, strict):
    R = check.Report()
    s = check.check_core_pg(P, R, strict=strict)
    return R, s


def test_clean_type_no_finding():
    with tempfile.TemporaryDirectory() as d:
        for strict in (False, True):
            R, s = _run(_P(d), strict)
            assert [i for i in R.items if i["check"] == "core_pg"] == []
            assert s["types_with_macros"] == 1 and s["types_missing"] == [] and s["insts_no_pg"] == 0


def test_mutant_missing_core_pg_connect_warn_then_error():
    with tempfile.TemporaryDirectory() as d:
        R, s = _run(_P(d, connect=False), strict=False)
        assert R.errors() == [] and any(i["level"] == "WARN" and "core_pg_connect" in i["msg"] for i in R.items)
        assert s["types_missing"] == ["hd"] and s["macro_insts_missing"] == 2
        R, s = _run(_P(d, connect=False), strict=True)
        assert len(R.errors()) == 1 and "without core_pg_connect" in R.errors()[0]["msg"]


def test_mutant_lef_without_pg_geometry():
    """no VSS geometry, M7-only PG pins, and VDD/VSS on different layers are each a finding even with the opt-in set"""
    for kw in (dict(vss=None), dict(vdd="M7", vss="M7"), dict(vdd="M5", vss="M4")):
        with tempfile.TemporaryDirectory() as d:
            R, s = _run(_P(d, lef_kw=kw), strict=True)
            assert len(R.errors()) == 1, kw
            assert s["insts_no_pg"] == 2 and len(s["lefs_no_pg"]) == 1
            R, s = _run(_P(d, lef_kw=kw), strict=False)
            assert R.errors() == [] and len([i for i in R.items if i["check"] == "core_pg"]) == 1


def test_unresolved_lef_is_warn_only():
    with tempfile.TemporaryDirectory() as d:
        P = _P(d)
        P.types["hd"]["hard_cores"][0]["lef"] = str(Path(d) / "missing.lef")
        R, s = _run(P, strict=True)
        assert R.errors() == [] and s["lefs_unresolved"] and "unchecked" in R.items[0]["msg"]


def test_type_without_macros_not_flagged():
    with tempfile.TemporaryDirectory() as d:
        P = _P(d, connect=False)
        P.types["hd"]["hard_cores"][0].pop("lef")       # a declared core without a view places no macro
        R, s = _run(P, strict=True)
        assert R.items == [] and s["types_with_macros"] == 0 and s["types_cores_without_lef"] == ["hd"]
