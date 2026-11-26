"""C-LEGACY-VIEW-EOL (S81-COL-EOL 11-26): COL kits staging a porous M4/M5 view with pin line-end OBS stubs are refused by kit_preflight; porous_views never applies them."""
import gzip
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_preflight as KP
import porous_views as PV

LEF_CLEAN = """MACRO m
  SIZE 10 BY 10 ;
  PIN a
    USE SIGNAL ;
    PORT
      LAYER M5 ;
        RECT 1.0 1.0 1.2 1.048 ;
    END
  END a
  OBS
    LAYER M5 ;
      RECT 3.0 3.0 4.0 3.1 ;
  END
END m
"""
# own-wire OBS stub: the pin ends at x=1.2, the OBS continues to 1.231 (< 0.048 past the pin end) on the pin track
LEF_STUB = LEF_CLEAN.replace("RECT 3.0 3.0 4.0 3.1 ;", "RECT 1.0 1.0 1.231 1.048 ;")


def _kit(tmp, design, lefs):
    (tmp / "macros").mkdir()
    (tmp / "config.mk").write_text(f"export DESIGN_NAME = {design}\n")
    for n, t in lefs.items():
        (tmp / "macros" / n).write_text(t)
    return tmp


def test_counter_separates_clean_and_stub():
    assert KP.lef_m5_eol_pins(LEF_CLEAN) == 0
    assert KP.lef_m5_eol_pins(LEF_STUB) == 1


def test_col_kit_with_known_porous_sha_is_refused(tmp_path):
    row = PV.rows()["dsfd_qbank_N.lef"]
    raw = gzip.decompress((PV.DATA / row["file"]).read_bytes())
    assert hashlib.sha256(raw).hexdigest()[:8] in KP.EOL_STALL_SHA8
    kit = _kit(tmp_path, "col_h9_r2__t1__clx", {})
    (kit / "macros" / "dsfd_qbank_N.lef").write_bytes(raw)
    err = KP.col_view_eol(kit)
    assert err and "C-LEGACY-VIEW-EOL" in err[0] and "6e387979" in err[0]


def test_col_kit_with_clean_views_passes_and_stub_count_fails(tmp_path):
    kit = _kit(tmp_path, "col_h10_r2__t1__cl1", {"a.lef": LEF_CLEAN})
    assert KP.col_view_eol(kit) == []
    kit2 = _kit(tmp_path / "k2" if (tmp_path / "k2").mkdir() is None else tmp_path, "col_h9_r1__t1", {f"s{i}.lef": LEF_STUB for i in range(20)})
    assert any("20 M5 signal pins" in e for e in KP.col_view_eol(kit2))


def test_non_col_kit_is_not_judged(tmp_path):
    kit = _kit(tmp_path, "ot_s81sl_leaf__t5", {f"s{i}.lef": LEF_STUB for i in range(40)})
    assert KP.col_view_eol(kit) == []


def test_every_listed_stall_sha_is_a_porous_row_and_select_skips_it(tmp_path, monkeypatch):
    rows = {r["sha256"][:8]: n for n, r in PV.rows().items()}
    for sha8, mod in PV.EOL_STALL_SHA8.items():
        assert rows.get(sha8, "").startswith(mod), (sha8, mod)
    assert PV.EOL_STALL_SHA8 == KP.EOL_STALL_SHA8
    name = "dsfd_qbank_N.lef"
    row = PV.rows()[name]
    plan = tmp_path / name
    plan.write_text("base")
    monkeypatch.setitem(row, "base_sha256", hashlib.sha256(b"base").hexdigest())
    monkeypatch.setenv(PV.ENV, "all")
    monkeypatch.delenv(PV.ALLOW_EOL_ENV, raising=False)
    PV.SKIPPED.clear()
    logs = []
    assert PV.select(str(plan), lambda p: p, log=logs.append) == str(plan)
    assert PV.SKIPPED[name]["reason"].startswith("C-LEGACY-VIEW-EOL")
