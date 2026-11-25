"""FP-CONVERGE-S81: MONLEG-REACH runs in every PRE: --skip MONLEG is ignored and said so."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_gate_pre as PGP  # noqa: E402


def test_monleg_not_skippable_source():
    src = Path(PGP.__file__).read_text()
    i = src.index("_pt.mark(\"MONLEG\")")
    blk = src[i:i + 700]
    assert "--skip ignored" in blk and "findings += check_monleg(plan)" in blk
    assert "if \"MONLEG\" not in skip" not in blk
