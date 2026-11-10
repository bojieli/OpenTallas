"""bind_view_check: clean view, PG stripe offset (another run / plan stub) and pin-access stub cases; exit 0 always."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_view_check as B


def lef(name="core", size=(40.0, 20.0), pin_rects=None, pg_x=(10.0, 20.0), pitch_gap=0.192, header="VERSION 5.8 ;"):
    pin_rects = pin_rects or {"a": [(0.0, 5.0, 0.084, 5.024)], "b": [(39.916, 7.0, 40.0, 7.024)]}
    out = [header, "MACRO %s" % name, "  CLASS BLOCK ;", "  SIZE %s BY %s ;" % size]
    for n, rs in pin_rects.items():
        out += ["  PIN %s" % n, "    DIRECTION %s ;" % ("INPUT" if n == "a" else "OUTPUT"), "    USE SIGNAL ;",
                "    PORT", "      LAYER M4 ;"] + ["        RECT %.3f %.3f %.3f %.3f ;" % r for r in rs] + \
               ["    END", "  END %s" % n]
    for net, use, shift in (("VSS", "GROUND", 0.0), ("VDD", "POWER", pitch_gap)):
        out += ["  PIN %s" % net, "    DIRECTION INOUT ;", "    USE %s ;" % use, "    PORT", "      LAYER M5 ;"]
        out += ["        RECT %.3f 1.000 %.3f %.3f ;" % (x + shift - 0.06, x + shift + 0.06, size[1] - 1) for x in pg_x]
        out += ["    END", "  END %s" % net]
    out += ["  OBS", "    LAYER M4 ;", "      RECT 0 0 %s %s ;" % size, "  END", "END %s" % name, "END LIBRARY"]
    return "\n".join(out) + "\n"


def kit_and_exports(tmp, kit_text, exp_text, name="core", abstract=None):
    kit = tmp / "kit"
    (kit / "macros").mkdir(parents=True)
    (kit / "macros" / (name + ".lef")).write_text(kit_text)
    (kit / "macros" / "ot_sram_x.lef").write_text("# OpenTallas memory compiler (tools/mem_compiler), ASAP7 abstract view\n"
                                                  + lef(name="ot_sram_x"))
    exp = tmp / "exp" / name
    exp.mkdir(parents=True)
    (exp / "detail.lef").write_text(exp_text)
    (exp / "export.json").write_text(json.dumps({"odb_sha256": "e" * 64, "routed_db": "/r/run/base/6_final.odb"}))
    cache = {"signed_records": [{"top": name, "name": "kl_" + name, "routed_db": "/r/run/base/6_final.odb",
                                 "store_id": "s" * 64, "versioned": True, "flow_tag": "f", "generated": "2026-11-01"}],
             "plans": {"p.json": {"designs": {name: {"pins_lef": "views/%s/%s.lef" % (name, name)}}}}}
    return str(kit), str(tmp / "exp"), cache


def test_clean(tmp_path):
    kit, exp, cache = kit_and_exports(tmp_path, lef(), lef(header="VERSION 5.8 ;\nBUSBITCHARS \"[]\" ;"))
    rep = B.run(kit, cache, export_dir=exp)
    assert [r["core"] for r in rep["rows"]] == ["core"]  # generated SRAM skipped
    assert rep["rows"][0]["classes"] == ["CLEAN"]
    assert rep["rows"][0]["export_is_counted_db"] is True
    assert rep["mismatches"] == []


def test_pg_offset_other_run(tmp_path, monkeypatch):
    kit, exp, cache = kit_and_exports(tmp_path, lef(pg_x=(2.46, 7.86, 13.26)), lef(pg_x=(6.384, 10.704, 15.024)))
    monkeypatch.setattr(B, "view_provenance", lambda repo, rev, p: {"odb_sha256": "a" * 64, "odb_host": "/old/run"})
    rep = B.run(kit, cache, export_dir=exp, git_repo="x")
    row = rep["rows"][0]
    assert row["classes"] == ["PG_OFFSET"]
    assert row["details"]["pg"]["VSS M5/V"]["shared"] == 0
    assert "another routed DB" in row["stale"]
    assert rep["mismatches"] == ["core"]


def test_pg_offset_plan_stub(tmp_path):
    # kit carries the standard stub recipe (4.32 inset + 2.064 offset, pitch 4.32); the real DB is shifted
    rec = B.stub_recipe_stripes(40.0, 20.0)["VSS"]
    kit, exp, cache = kit_and_exports(tmp_path, lef(pg_x=rec), lef(pg_x=[x - 2.16 for x in rec]))
    row = B.run(kit, cache, export_dir=exp)["rows"][0]
    assert row["classes"] == ["PG_OFFSET"]
    assert row["details"]["kit_pg_is_stub_recipe"] is True
    assert "stub" in row["stale"]


def test_pin_stub_only(tmp_path):
    stub = {"a": [(0.0, 5.0, 0.084, 5.024), (0.084, 5.0, 1.3, 5.024)], "b": [(39.916, 7.0, 40.0, 7.024)]}
    kit, exp, cache = kit_and_exports(tmp_path, lef(pin_rects=stub), lef())
    row = B.run(kit, cache, export_dir=exp)["rows"][0]
    assert row["classes"] == ["PIN_STUB"] and row["details"]["pin_stub"] == ["a"]
    assert row["stale"] is None


def test_pin_shape_and_outline(tmp_path):
    moved = {"a": [(0.0, 9.0, 0.084, 9.024)], "b": [(39.916, 7.0, 40.0, 7.024)]}
    kit, exp, cache = kit_and_exports(tmp_path, lef(pin_rects=moved, size=(40.0, 21.0)), lef())
    row = B.run(kit, cache, export_dir=exp)["rows"][0]
    assert "PIN_SHAPE" in row["classes"] and "OUTLINE" in row["classes"]


def test_no_export_and_exit_zero(tmp_path, capsys):
    kit, exp, cache = kit_and_exports(tmp_path, lef(), lef())
    (Path(exp) / "core" / "detail.lef").unlink()
    cp = tmp_path / "cache.json"
    cp.write_text(json.dumps(cache))
    out = tmp_path / "r.json"
    assert B.main(["--kit", kit, "--cache", str(cp), "--export-dir", exp, "--out", str(out)]) == 0
    rep = json.loads(out.read_text())
    assert rep["rows"][0]["classes"] == ["NO_EXPORT"] and rep["mismatches"] == []
    assert B.main(["--kit", str(tmp_path / "missing"), "--cache", str(cp)]) == 0  # error is reported, not raised
