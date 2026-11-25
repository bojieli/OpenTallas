"""FP-CONVERGE-S81 11-25: int(W / 4.32) truncated 1563.84 / 4.32 = 361.99999999999994 to 361, so the Raster lost its E-face column and every
E-face point of a grown leaf read as blocked (t50gr).  The grid size must be epsilon-safe."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hub_repack as HR  # noqa: E402

G = 4.32


def test_raster_counts_exact_multiples():
    for k in (361, 362, 393, 363, 100, 17):
        W = k * G
        R = HR.Raster(W, 20 * G, [])
        assert R.nx == k + 1 and R.ny == 21
    for W, n in ((1563.84, 362), (1697.76, 393), (1568.16, 363)):
        assert HR.Raster(W, 100.0, []).nx == n + 1


def test_e_face_column_is_free():
    R = HR.Raster(1563.84, 200.0, [])
    assert R.free(1563.84, 100.0)


def test_mutant_old_formula_fails_1563_84():
    assert int(1563.84 / G) + 1 == 362          # the old formula: one column short of the 363 the fixed grid has
    assert int(1563.84 / G + 1e-9) + 1 == 363
