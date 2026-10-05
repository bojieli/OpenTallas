"""L1 fused DSpark draft head: default off, successor-only sources, as-built encodings untouched."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_fused_draft_head as F  # noqa: E402


def test_select_default_off():
    srcs = [ROOT / "rtl/hdc/v41/ot_hdc_v41_matvec.sv", ROOT / "rtl/hdc/v41/ot_hdc_core_v41.sv", ROOT / "x.sv"]
    off = F.select(srcs)
    assert off["sources"] == srcs and off["defines"] == [] and not off["enabled"]
    on = F.select(srcs, enable=True)
    assert on["sources"][:2] == [F.SUCCESSOR / "ot_hdc_v41_matvec.sv", F.SUCCESSOR / "ot_hdc_core_v41.sv"]
    assert on["sources"][2] == srcs[2] and on["defines"] == [F.DEFINE]


def test_successor_files_exist():
    for n in F.NAMES:
        assert (F.SUCCESSOR / n).is_file()
    assert F.TB_FH.is_file()


def test_fused_sources_carry_the_closed_adder():
    srcs, defs, _ = F.sources(True)
    names = [p.name for p in srcs]
    for n in ("ot_hdc_fp32_add_lat.sv", "ot_hdc_prefix.sv", "ot_hdc_fastfp.sv"):
        assert n in names
    assert not any("OT_FH_ALAT" in d for d in defs)       # successor default (7, closed)
    _, defs0, _ = F.sources(True, fh_alat=0)
    assert "+define+OT_FH_ALAT=0" in defs0
    off, defs_off, _ = F.sources(False)
    assert "ot_hdc_fp32_add_lat.sv" not in [p.name for p in off] and not any("FUSED" in d for d in defs_off)
