"""GENBUG (FABLE-PD-HEAD-1115 s3, HEAD hd_spn DRT-0255): the face-pin spreader kept M7 pins off the PG band at 4.32 +- 0.48 mod 8.64
(PART_PG_BANDS, type-frame phase) but a kit whose pdn.tcl puts the M7 pair at the core-edge offset has its straps at 0 mod 8.64.
die.pg.pin_band_origins_um [0, 4.32] makes the spreader (pin_positions, usable_tracks, check) avoid both phases; absent = unchanged."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S  # noqa: E402

M7 = {"name": "M7", "dir": "V", "pitch_um": 0.064, "offset_um": 0.032}
PORT = dict(id="p", layers=["M7"], window_um=[100.0, 140.0], width=200, epoch=False, order="lsb_low")


def _both(L):
    return dict(L, pg_origins=(0.0, 4.32))


def _bad(c, origins):
    return any(S.pg_blocked("M7", c - o) for o in origins)


def test_default_pin_table_unchanged_and_both_phase_pins_clear_of_both_bands():
    port = dict(PORT)
    base = S.pin_positions(port, {"M7": M7})
    assert base == S.pin_positions(port, {"M7": dict(M7)})                   # no key: byte-identical to the old rule
    assert any(_bad(c, (0.0,)) is False and _bad(c, (4.32,)) for _, _, c in base)   # old pins DO sit in the 0-phase band
    new = S.pin_positions(port, {"M7": _both(M7)})
    assert len(new) == len(base) and all(not _bad(c, (0.0, 4.32)) for _, _, c in new)
    assert any(c != d for (_, _, c), (_, _, d) in zip(new, base))


def test_usable_tracks_shrinks_with_both_origins():
    a = S.usable_tracks(M7, "M7", 100.0, 140.0)
    b = S.usable_tracks(_both(M7), "M7", 100.0, 140.0)
    assert 0 < b < a
    assert S.pg_blocked_any(M7, "M7", 8.64 * 12) is False and S.pg_blocked_any(_both(M7), "M7", 8.64 * 12) is True


def test_plan_attaches_origins_to_banded_layers_only_when_asked():
    from test_g2 import PAIR
    raw = copy.deepcopy(PAIR)
    P0 = S.Plan(copy.deepcopy(raw))
    assert "pg_origins" not in P0.layers["M7"]
    raw["die"].setdefault("pg", {})["pin_band_origins_um"] = [0.0, 4.32]
    P1 = S.Plan(raw)
    assert P1.layers["M7"]["pg_origins"] == (0.0, 4.32) and "pg_origins" not in S.ASAP7_LAYERS[5] and "pg_origins" not in P1.layers["M4"]
