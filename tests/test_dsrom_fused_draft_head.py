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
